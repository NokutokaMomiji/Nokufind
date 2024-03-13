from datetime import datetime

from rule34Py import Post as r34Post
from rule34Py.post_comment import PostComment as r34Comment

from nokufind import Post, Comment, Note
from nokufind.Subfinder import ISubfinder, SubfinderConfiguration
from nokufind.Utils import Rule34API, assert_conversion, parse_tags

class Rule34Finder(ISubfinder):
    @staticmethod
    def to_post(post_data: r34Post) -> Post:
        """Creates a Post object from rule34 post data.

        Args
        ~~~~
            post_data (``rule34Py.post.Post``): A rule34 Post object (from rule34Py) containing all of the post data.

        Returns
        ~~~~~~~
            ``Post``: A Post object containing the extracted data.
        """

        # The Finder uses a custom Rule34API object which means posts contain some extra data
        # not found originally in rule34Py's Post object, so I check for that if the user attempts
        # to use a post from rule34Py.
        if (not hasattr(post_data, "source")):
            post_data.source = ""

        if (not hasattr(post_data, "content")):
            post_data.content = post_data.video if post_data.content_type == "video" else post_data.image

        if (not hasattr(post_data, "parent_id")):
            post_data.parent_id = None

        return Post(
            post_id = post_data.id,
            tags = post_data.tags,
            sources = [post_data.source.split(" ")], #post_data.source.split(" "),
            images = [post_data.content],
            authors = [""],
            source = "rule34",
            preview = post_data.sample,
            md5 = [post_data.hash],
            rating = post_data.rating,
            parent_id = post_data.parent_id,
            dimensions = [(post_data.size[0], post_data.size[1])],
            poster = post_data.owner,
            poster_id = -1,
            name = None
        )
    
    @staticmethod
    def to_comment(comment_data: r34Comment) -> Comment:
        """Creates a Comment object from rule34 comment data.

        Args:
            comment_data (``rule34Py.post_comment.PostComment``): A PostComment object (from rule34Py) containing all of the comment data.

        Returns:
            ``Comment``: A Comment object containing the extracted data.
        """
        
        if (not hasattr(comment_data, "creator")):
            comment_data.creator = "Unknown"
        
        return Comment(
            comment_id = comment_data.id,
            post_id = comment_data.post_id,
            creator_id = comment_data.author_id,
            creator = comment_data.creator,
            body = comment_data.body,
            source = "rule34",
            created_at = datetime.strptime(comment_data.creation, "%Y-%m-%d %H:%M")
        )
    
    @staticmethod
    def to_note(note_data: dict) -> Note:
        return Note(
            note_id = note_data["id"],
            created_at = datetime.strptime(note_data["created_at"], "%Y-%m-%d %H:%M:%S"),
            x = note_data["x"],
            y = note_data["y"],
            width = note_data["width"],
            height = note_data["height"],
            body = note_data["body"],
            source = "rule34",
            post_id = note_data["post_id"]
        )

    def __init__(self):
        self.__client = Rule34API()
        self.__config = SubfinderConfiguration()

    def _get_all_posts(self, tags: list[str], limit: int, page: int | None) -> list[r34Post]:
        all_posts = []
        current_page = page if page != None else 0
        previous_size = 1000
        oversized = False

        while (previous_size == 1000):
            raw_posts = self.__client.search(tags, current_page)
            previous_size = len(raw_posts)

            all_posts += raw_posts

            if len(all_posts) >= limit:
                oversized = True
                break

            current_page += 1

        if oversized:
            return all_posts[:limit]
        
        return all_posts
    
    def _get_all_comments(self, page: int | None, limit: int) -> list[r34Comment]:
        all_comments = []
        current_page = page if page != None else 1
        previous_size = 100
        oversized = False

        while (previous_size == 100):
            raw_comments = self.__client.search_comments(current_page)
            previous_size = len(raw_comments)

            all_comments += raw_comments

            if len(all_comments) >= limit:
                oversized = True
                break

            current_page += 1

        if oversized:
            return all_comments[:limit]
        
        return all_comments

    def search_posts(self, tags: str | list[str], *, limit: int = 100, page: int | None = None) -> list[Post]:
        self._check_client()
        
        tags = parse_tags(tags) if type(tags) != list else tags

        raw_posts = self._get_all_posts(tags, limit, page)

        return [Rule34Finder.to_post(post) for post in raw_posts]
    
    def get_post(self, post_id: int) -> Post | None:
        self._check_client()

        # Post ID must be an int, so we convert it or raise an error if the conversion fails.
        post_id = assert_conversion(post_id, int, "post_id")
        
        raw_post = self.__client.get_post(post_id)

        return Rule34Finder.to_post(raw_post) if type(raw_post) == r34Post else None
    
    def search_comments(self, *, post_id=None, limit=None, page=None) -> list[Comment]:
        self._check_client()
        
        raw_comments = None

        if post_id == None:
            raw_comments = self._get_all_comments(page, limit)
            return [Rule34Finder.to_comment(comment) for comment in raw_comments]
        
        post_id = assert_conversion(post_id, int, "post_id")

        raw_comments = self.__client.get_comments(post_id)
        return [Rule34Finder.to_comment(post) for post in raw_comments]
    
    def get_comment(self, comment_id: int) -> Comment | None:
        self._check_client()

        comment_id = assert_conversion(comment_id, int, "comment_id")

        return None
    
    def get_notes(self, post_id: int) -> list[Note]:
        self._check_client()

        post_id = assert_conversion(post_id, int, "post_id")

        raw_notes = self.__client.get_notes(post_id)

        return [Rule34Finder.to_note(note) for note in raw_notes]
    
    def post_get_parent(self, post: Post) -> Post | None:
        if (not post.parent_id):
            return None
        
        parent_post = self.get_post(post.parent_id)

        return post._set_parent(parent_post)
    
    def post_get_children(self, post: Post) -> list[Post]:
        children_posts = self.search_posts(f"parent:{post.post_id}")

        if (not children_posts):
            return []
        
        for index, child_post in enumerate(children_posts):
            if child_post.post_id == post.post_id:
                children_posts.pop(index)
                break

        return post._set_children(children_posts)


    def _check_client(self):
        if (not isinstance(self.__client, Rule34API)):
            raise RuntimeError(f"Client must be of type Rule34API, not {type(self.__client)}")

    @property
    def configuration(self):
        return self.__config