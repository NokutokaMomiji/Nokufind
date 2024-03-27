from enma import Enma, DefaultAvailableSources, SearchResult, Manga
from enma.domain.entities.manga import Chapter

from nokufind import Post, Comment, Note
from nokufind.Subfinder import ISubfinder, SubfinderConfiguration
from nokufind.Utils import assert_conversion, get, log

class ManganatoFinder(ISubfinder):
    @staticmethod
    def to_post(post_data: Manga | Chapter) -> Post:
        if (type(post_data) == Manga):
            return Post(
                post_id = post_data.id,
                tags = [genre.name for genre in post_data.genres],
                sources = [chapter.link.link for chapter in post_data.chapters],
                images = [post_data.cover.uri],
                authors = [author.name for author in post_data.authors],
                source = "manganato",
                preview = post_data.thumbnail.uri,
                md5 = None,
                rating = None,
                parent_id = None,
                dimensions = (post_data.cover.width, post_data.cover.height),
                poster = "",
                poster_id = None,
                name = post_data.title.english
            )
        
        return Post(
            post_id = post_data.id,
            tags = post_data.tags,
            sources = post_data.sources,
            images = [image.uri for image in post_data.pages],
            authors = post_data.authors,
            source = "manganato",
            preview = post_data.pages[0].uri,
            md5 = None,
            rating = None,
            parent_id = f"manga-{post_data.pages[0].uri.split('/')[-3]}",
            dimensions = [(page.height, page.width) for page in post_data.pages],
            poster = "",
            poster_id = None,
            name = None
        )
    
    @staticmethod
    def to_comment(comment_data) -> Comment:
        raise RuntimeError("Manganato has no comments.")
    
    @staticmethod
    def to_note(note_data) -> Note:
        raise RuntimeError("Manganato has no notes.")
    
    def __init__(self) -> None:
        source = "manganato"

        self.__client = Enma[DefaultAvailableSources]()
        self.__client.source_manager.set_source(source)

        self.__config = SubfinderConfiguration()
        self.__config._set_property("source", source)
        self.__config.set_header("Referer", "https://chapmanganato.com/")

        self.__name  = f"nokufind.Subfinder.{self.__class__.__name__}"

    def _get_all_posts(self, tags: str, limit: int = 100, page: int | None = 1):
        current_page = page if type(page) == int else 1
        limit = assert_conversion(limit, int, "limit")
        previous_size = 20
        posts = []
        oversized = True

        while (previous_size == 20):
            try:
                raw_posts = self.__client.search(tags, current_page).results
            except Exception as e:
                log(f"> [{self.__name}]: {e}")
                return posts
            
            previous_size = len(raw_posts)

            posts += raw_posts

            if (len(posts) >= limit):
                oversized = True
                break

            current_page += 1

        if (oversized):
            posts = posts[:limit]

        return posts

    def search_posts(self, tags: str | list[str], *, limit: int = 100, page: int | None = None) -> list[Post]:
        if (type(tags) == list):
            tags = " ".join(tags)

        raw_posts =  self._get_all_posts(tags, limit, page)
        posts = []
        
        for raw_post in raw_posts:
            try:
                post = self.get_post(raw_post.id)
            except:
                post = None

            if (post == None):
                continue
            posts.append(post)

        return posts

    def get_post(self, post_id: str) -> Post | None:
        log(f"> [{self.__name}]: Fetching post \"{post_id}\".")

        try:
            post = self.__client.get(post_id, with_symbolic_links = True)
        except:
            post = None

        return ManganatoFinder.to_post(post)._set_headers(self.configuration.headers) if post != None else None

    def search_comments(self, *, post_id: int | None = None, limit: int | None = None, page: int | None = None) -> list[Comment]:
        return []
    
    def get_comment(self, comment_id: int, post_id: int | None = None) -> Comment | None:
        return None
    
    def get_notes(self, post_id: int) -> list[Note]:
        return []
    
    def post_get_parent(self, post: Post) -> Post | None:
        if (type(post) != Post):
            raise TypeError(f"Post must be a Post object, not {type(post)}.")
        
        try:
            raw_post = self.__client.get(post.parent_id, with_symbolic_links = True)
        except:
            return None
        return ManganatoFinder.to_post(raw_post)._set_headers(self.configuration.headers) if raw_post != None else None
    
    def post_get_children(self, post: Post) -> list[Post]:
        if (type(post) != Post):
            raise TypeError(f"Post must be a Post object, not {type(post)}.")
        
        try:
            manga = self.__client.get(post.post_id)
        except:
            manga = None

        if (manga == None):
            return []
        
        for index, chapter in enumerate(manga.chapters):
            chapter.tags = manga.genres
            chapter.sources = post.sources[index]
            chapter.authors = post.authors
        
        return [ManganatoFinder.to_post(chapter)._set_headers(self.configuration.headers) for chapter in manga.chapters]

    def _headers(self):
        return self.configuration.headers

    @property
    def configuration(self):
        return self.__config