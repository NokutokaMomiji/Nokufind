from datetime import datetime
from itertools import combinations
from time import sleep

from pybooru import Danbooru
from pybooru.exceptions import PybooruHTTPError

from nokufind import Post, Comment, Note
from nokufind.Subfinder import ISubfinder, SubfinderConfiguration
from nokufind.Utils import attempt_conversion, log, get, parse_tags

def _post_is_valid(post: dict) -> bool:
    return (post.get("md5") != None and post.get("file_url") != None)

def _comment_is_valid(comment: dict) -> bool:
    return not comment.get("is_deleted")

def _filter_invalid_posts(posts: list[dict]) -> list[dict]:
    return [post for post in posts if _post_is_valid(post)]

def _filter_invalid_comments(comments: list[dict]) -> list[dict]:
    return [comment for comment in comments if _comment_is_valid(comment)]

class DanbooruFinder(ISubfinder):
    # Static methods.
    @staticmethod
    def to_post(post_data: dict) -> Post:
        """Creates a Post object from Danbooru data.

        Args
        ~~~~
            post_data (``dict``): A dictionary containing all of the Danbooru post data.

        Returns
        ~~~~~~~
            ``Post``: A Post object containing the extracted data.
        """

        if "author" not in post_data.keys():
            post_data["author"] = f"User {post_data['uploader_id']}"

        return Post(
            post_id = post_data["id"],
            tags = post_data["tag_string"].split(" "),
            sources = post_data["source"].split(" "),
            images = [post_data["file_url"]],
            authors = post_data["tag_string_artist"].split(" "),
            source = "danbooru",
            preview = post_data["preview_file_url"],
            md5 = [post_data["md5"]],
            rating = post_data["rating"],
            parent_id = post_data["parent_id"],
            dimensions = [(post_data["image_width"], post_data["image_height"])],
            poster = post_data["author"],
            poster_id = post_data["uploader_id"],
            name = None
        )
    
    @staticmethod
    def to_comment(comment_data) -> Comment:
        return Comment(
            comment_id = comment_data["id"],
            post_id = comment_data["post_id"],
            creator_id = comment_data["creator_id"],
            creator = "",
            body = comment_data["body"],
            source = "danbooru",
            created_at = datetime.strptime(comment_data["created_at"], "%Y-%m-%dT%H:%M:%S.%f%z")
        )

    @staticmethod
    def to_note(note_data: dict) -> Note:
        """Creates a Note object from Danbooru note data.

        Args:
            note_data (``dict``): A dictionary containing the Danbooru note data.

        Returns:
            ``Note``: A Note object containing the extracted data.
        """

        return Note(
            note_id = note_data["id"],
            created_at = datetime.strptime(note_data["created_at"], "%Y-%m-%dT%H:%M:%S.%f%z"),
            x = note_data["x"],
            y = note_data["y"],
            width = note_data["width"],
            height = note_data["height"],
            body = note_data["body"],
            source = "danbooru",
            post_id = note_data["post_id"]
        )
    
    def __init__(self, api_key = ""):
        self.__client = Danbooru("danbooru", api_key = api_key)

        self.__config = SubfinderConfiguration(self.on_config_change)
        self.__config._set_property("api_key", api_key)

        self.__page = 1
        self.__comments_page = 1

        self.__name = f"nokufind.Subfinder.{self.__class__.__name__}"

    def _get_all_posts(self, tags: str, limit: int = 100, page: int | None = None) -> list[Post]:
        current_posts = []
        current_size = 100
        current_page = page if type(page) == int else 1
        
        while (current_size == 100):
            try:
                raw_posts = self.__client.post_list(tags = tags, limit = 100, page = current_page)
            except KeyError:
                break
            except PybooruHTTPError as e:
                log(f"> [{self.__name}]: PybooruHTTPError: {e}")
                if "410" in e._msg:
                    break
                else:
                    sleep(0.1)
                    continue

            current_size = len(raw_posts)

            raw_posts = _filter_invalid_posts(raw_posts)
            posts = [DanbooruFinder.to_post(post) for post in raw_posts]

            current_posts += posts

            if len(current_posts) >= limit:
                break

            current_page += 1

        current_posts.sort(key=lambda x: x.post_id)

        if len(current_posts) > limit:
            return current_posts[:limit]
        
        return current_posts

    def _get_multiple_tags(self, tags: str | list[str], limit: int = 100, page: int | None = None) -> list[Post]:
        parsed_tags = parse_tags(tags)
        
        num_of_tags = len(parsed_tags)
        
        if num_of_tags <= 2:
            tag_string = " ".join(parsed_tags)
            return self._get_all_posts(tag_string, limit = limit, page = page)
        
        total_posts: list[Post] = []
        filtered_posts: list[Post] = []

        for index, tag in enumerate(parsed_tags):
            if tag == "or":
                s1 = []
                s2 = []
                prev_tags: str = get(parsed_tags, index - 1, None)
                next_tags: str = get(parsed_tags, index + 1, None)

                if prev_tags:
                    s1 = self._get_multiple_tags(prev_tags.strip("()"), limit = limit, page = page)
                if next_tags:
                    s2 = self._get_multiple_tags(next_tags.strip("()"), limit = limit, page = page)
                return s1 + s2
            elif "or" in tag:
                return self._get_multiple_tags(next_tags.strip("()"), limit = limit, page = page)
        
        if (num_of_tags % 2 == 0):
            total_combinations = [" ".join(total_posts[i:i + 2]) for i in range(num_of_tags, step = 2)]
        else:
            total_combinations = list(combinations(parsed_tags, 2))

        for combination in total_combinations:
            tag_string = " ".join(combination)
            log(f"> [{self.__name}]: \"{tag_string}\".")

            current_posts = self._get_all_posts(tag_string, limit, page)

            if (not len(current_posts)):
                log(f"> [{self.__name}]: No posts found.")
                return []
            
            total_posts += current_posts

        for post in total_posts:
            add_to_list = True
            for tag in parsed_tags:
                if tag not in post.tags and not tag.startswith("rating:"):
                    add_to_list = False
                    break
            
            if add_to_list:
                filtered_posts.append(post)

        if (len(filtered_posts) > limit):
            return filtered_posts[:limit]
        
        return filtered_posts

    def search_posts(self, tags: str | list[str], *, limit: int = 100, page: int | None = None) -> list[Post]:
        self._check_client()

        # Danbooru takes in tags as a string, so we need to join them together.
        if (type(tags) == list):
            tags = " ".join()

        if page == None:
            page = self.__page
        else:
            self.__page = page

        return self._get_multiple_tags(tags = tags, limit = limit, page = page)
    
    def get_post(self, post_id: int) -> Post | None:
        self._check_client()

        # Post ID must be an int, so we convert it or raise an error if the conversion fails.
        post_id = attempt_conversion(post_id, int)

        if (type(post_id) != int):
            raise TypeError(f"post_id should be an int, not {type(post_id)}")

        # Danbooru flat out raises a PybooruHTTPError when it doesn't find a post, so we deal with that.
        try:
            raw_post = self.__client.post_show(post_id)
            
            # Normally, I would do this using a ternary operator, but the to_post function fails if data is not valid.
            if (not _post_is_valid(raw_post)):
                return None
            
            return DanbooruFinder.to_post(raw_post)
        except PybooruHTTPError as e:
            log(f"> [{self.__name}]: Danbooru raised an HTTP error.\n{e}")
            return None
        
    def search_comments(self, *, post_id = None, limit = None, page = None):
        raw_comments = self.__client.comment_list("comment", post_id = post_id, limit = limit, page = page)
        raw_comments = _filter_invalid_comments(raw_comments)

        return [DanbooruFinder.to_comment(comment) for comment in raw_comments if comment != None]
    
    def get_comment(self, comment_id: int, post_id: int | None = None) -> Comment | None:
        self._check_client()

        comment_id = attempt_conversion(comment_id, int)

        if (type(comment_id) != int):
            raise TypeError(f"comment_id should be an int, not {type(comment_id)}.")

        try:
            raw_comment = self.__client.comment_show(comment_id)

            return DanbooruFinder.to_comment(raw_comment)
        except PybooruHTTPError as e:
            log(f"> [{self.__name}]: Danbooru raised an HTTP error.\n{e}")
            return None

    def get_notes(self, post: int | Post) -> list[Note]:
        self._check_client()

        post_id = post.post_id if type(post) == Post else post
        post_id = attempt_conversion(post_id, int)

        if (type(post) != int):
            raise TypeError(f"post_id should be an int or a Post object, not {type(post_id)}")
        
        raw_notes = self.__client.note_list(post_id = post_id)

        return [DanbooruFinder.to_note(note) for note in raw_notes if note != None]
    
    def post_get_parent(self, post: Post) -> Post | None:
        if (not isinstance(post, Post)):
            raise TypeError(f"post should be a Post object, not {type(post)}")
        
        if (not post.parent_id):
            return None

        return post._set_parent(self.get_post(post.parent_id))

    def post_get_children(self, post: Post) -> list[Post]:
        if (not isinstance(post, Post)):
            raise TypeError(f"post should be a Post object, not {type(post)}")
        
        children_posts = self.search_posts(f"parent:{post.post_id}")

        for index, child_post in enumerate(children_posts):
            if child_post.post_id == post.post_id:
                children_posts.pop(index)
                break

        return post._set_children(children_posts)

    def next_page(self):
        self.__page += 1

    def on_config_change(self, key: str, value, is_cookie: bool, is_header: bool):
        if (key == "api_key"):
            self.__client = Danbooru("danbooru", api_key = value)

    def _check_client(self):
        if (not isinstance(self.__client, Danbooru)):
            raise RuntimeError(f"Client must be of type Danbooru, not {type(self.__client)}.")
        
    @property
    def configuration(self):
        return self.__config