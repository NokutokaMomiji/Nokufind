from datetime import datetime, timedelta

from pixivpy3 import AppPixivAPI
from pixivpy3.utils import JsonDict
from timeloop import Timeloop

from nokufind import Post, Comment, Note
from nokufind.Subfinder import ISubfinder, SubfinderConfiguration
from nokufind.Utils import PIXIV_REFERER, get, make_request, assert_conversion
from nokufind.Utils.PixivAuth import login, refresh

PIXIV_AUTH_MESSAGE = """
"""

timeloop = Timeloop()

class PixivFinder(ISubfinder):
    @staticmethod
    def to_post(post_data: JsonDict) -> Post:
        pages = None

        if (post_data["page_count"] > 1):
            pages = [page["image_urls"]["original"] for page in post_data["meta_pages"]]
        else:
            pages = [post_data["meta_single_page"]["original_image_url"]]

        return Post(
            post_id = post_data["id"],
            tags = [tag["name"] for tag in post_data["tags"]],
            sources = [],
            images = pages,
            authors = [post_data["user"]["name"]],
            source = "pixiv",
            preview = post_data["image_urls"]["large"],
            md5 = None,
            rating = None,
            parent_id = None,
            dimensions = [(post_data["width"], post_data["height"])] * len(pages),
            poster = post_data["user"]["name"],
            poster_id = post_data["user"]["id"],
            name = None
        )
    
    @staticmethod
    def to_comment(comment_data) -> Comment:
        return Comment(
            comment_id = comment_data["id"],
            post_id = comment_data["post_id"],
            creator_id = comment_data["user"]["id"],
            creator = comment_data["user"]["name"],
            body = comment_data["comment"],
            source = "pixiv",
            created_at = datetime.strptime(comment_data["date"], "%Y-%m-%dT%H:%M:%S%z")
        )
    
    @staticmethod
    def to_note(note_data) -> Note:
        raise RuntimeError("Pixiv has no notes.")

    def __init__(self, refresh_key: str | None = None) -> None:
        self.__client = AppPixivAPI()

        if (not refresh_key):
            refresh_key = login()
            timeloop.start()

        self.__client.auth(refresh_token = refresh_key)

        self.__config = SubfinderConfiguration()
        self.__config._set_property("api_key", refresh_key)

    def search_posts(self, tags: str | list[str], *, limit: int = 100, page: int | None = None) -> list[Post]:
        self._check_client()

        if (type(tags) == list):
            tags = " ".join(tags)

        return self._get_all_posts(tags, limit, page)
    
    def get_post(self, post_id: int) -> Post | None:
        self._check_client()

        raw_post = self.__client.illust_detail(post_id)

        return PixivFinder.to_post(raw_post) if not "error" in raw_post else None
    
    def search_comments(self, *, post_id=None, limit=None, page=None) -> list[Comment]:
        comments = []
        
        if (post_id == None):
            offset = (page - 1) * 30 if page != None else 0
            while len(comments) < limit:
                posts = self.__client.illust_ranking(offset=offset)
                for post in posts.illusts:
                    raw_comment = self.__client.illust_comments(post["id"])
                    if len(raw_comment["comments"]) == 0:
                        continue

                    for comment in raw_comment["comments"]:
                        comment["post_id"] = post["id"]
                        comments.append(PixivFinder.to_comment(comment))
                offset += 30

            return comments[:limit]

        raw_comments = self.__client.illust_comments(post_id)
        if "error" in raw_comments:
            return None
        
        for comment in raw_comments["comments"]:
            comment["post_id"] = post_id

        return [PixivFinder.to_comment(comment) for comment in raw_comments]

    def get_comment(self, comment_id: int) -> Comment | None:
        self._check_client()

        return None
    
    def get_notes(self, post_id: int) -> list[Note]:
        return []
    
    def post_get_parent(self, post: Post) -> Post | None:
        return None
    
    def post_get_children(self, post: Post) -> list[Post]:
        return []
    
    # Non-standard functions
    def get_recommended_posts(self, limit: int = 100, page: int | None = None):
        self._check_client()
        
        posts = []
        limit = assert_conversion(limit, int, "limit")
        current_page = page if page != None else 0
        previous_size = 30
        oversized = False

        while previous_size == 30:
            raw_posts = self.__client.illust_recommended(offset = 30 * current_page).illusts
            previous_size = len(raw_posts)

            posts += [PixivFinder.to_post(post) for post in raw_posts]

            if (len(posts) > limit):
                oversized = True
                break
        
        if (oversized):
            return posts[:limit]
        
        return posts
    
    def get_recommended_user_posts(self, limit: int = 100, page: int | None = None):
        self._check_client()
        
        posts = []
        limit = assert_conversion(limit, int, "limit")
        current_page = page if page != None else 0
        previous_size = 30
        oversized = False

        while previous_size == 30:
            raw_posts = self.__client.user_recommended(offset = 30 * current_page).user_previews
            previous_size = len(raw_posts)

            posts += [PixivFinder.to_post(post) for post in raw_posts["illusts"]]

            if (len(posts) > limit):
                oversized = True
                break
        
        if (oversized):
            return posts[:limit]
        
        return posts

    def get_trending_tags(self):
        raise NotImplementedError()
        self.__client.trending_tags_illust()
    

    def on_config_change(self, key: str, value, is_cookie: bool, is_header: bool):
        if (key == "api_key" and value):
            self.__client.auth(refresh_token = value)

    def _get_all_posts(self, tags: str, limit: int, page: int | None = None) -> list[Post]:
        limit = assert_conversion(limit, int, "limit")
        current_page = page if page != None else 0
        previous_length = 30
        posts = []
        overflowed = False

        while (previous_length == 30):
            raw_posts = self.__client.search_illust(tags, offset = 30 * current_page).illusts
            previous_length = len(raw_posts)

            posts += [PixivFinder.to_post(post) for post in raw_posts]

            if (len(posts) > limit):
                overflowed = True
                break

            current_page += 1

        if (overflowed):
            return posts[:limit]
        
        return posts

    def _has_auth(self):
        return (self.__client.access_token != None)
    
    @timeloop.job(interval = timedelta(seconds=3500))
    def _refresh_auth(self):
        self.__client.auth(refresh_token = refresh(self.__config.get_config("api_key")))
    
    def _check_client(self):
        if (not isinstance(self.__client, AppPixivAPI)):
            raise RuntimeError(f"Client must be of type AppPixivAPI, not {type(self.__client)}.")

        if (not self._has_auth()):
            self.__config.set_config("api_key", login())


    @property
    def configuration(self):
        return self.__config