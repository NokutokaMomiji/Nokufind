import requests
from typing import cast
from datetime import datetime

from enma import Enma, DefaultAvailableSources, CloudFlareConfig, NHentai, Manga
from enma.domain.entities.manga import Chapter

from nokufind import Post, Comment, Note
from nokufind.Subfinder import ISubfinder, SubfinderConfiguration
from nokufind.Utils import assert_conversion, get, log, USER_AGENT
from nokufind.Post import Rating

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
POST_URL = "https://nhentai.net/g"
API_URL = "https://nhentai.net/api/gallery/%s/comments"
AVATARS_URL = "https://i5.nhentai.net/"
RANDOM_URL = "https://nhentai.net/random/"

class NHentaiFinder(ISubfinder):
    @staticmethod
    def to_post(post_data: Manga) -> Post:
        first_page = post_data.chapters[0].pages[0]
        return Post(
            post_id = int(post_data.id),
            tags = [genre.name for genre in post_data.genres],
            sources = [f"https://nhentai.net/g/{post_data.id}/"],
            images = [page.uri for page in post_data.chapters[0].pages],
            authors = [author.name for author in post_data.authors],
            source = "nhentai",
            preview = post_data.thumbnail.uri,
            md5 = None,
            rating = Rating.EXPLICIT,
            parent_id = None,
            dimensions = [(page.width, page.height) for page in post_data.chapters[0].pages],
            poster = "",
            poster_id = None,
            name = post_data.title.english
        )
    
    @staticmethod
    def to_comment(comment_data: dict) -> Comment:
        return Comment(
            comment_id = comment_data["id"],
            post_id = comment_data["gallery_id"],
            creator_id = comment_data["poster"]["id"],
            creator = comment_data["poster"]["username"],
            creator_avatar = AVATARS_URL + comment_data["poster"]["avatar_url"],
            body = comment_data["body"],
            source = "nhentai",
            created_at = datetime.fromtimestamp(comment_data["post_date"]),
        )
    
    @staticmethod
    def to_note(note_data) -> Note:
        raise RuntimeError("NHentai has no notes.")

    def __init__(self, cf_clearance: str = "") -> None:
        self.__client = Enma[DefaultAvailableSources]()
        self.__client.source_manager.set_source("nhentai")

        self.__cf_config = CloudFlareConfig(USER_AGENT, cf_clearance)
        self.__source = cast(NHentai, self.__client.source_manager.source)
        self.__source.set_config(self.__cf_config)

        self.__config = SubfinderConfiguration(self.on_client_change)
        self.__config.set_header("Referer", "https://nhentai.net")
        self.__config.set_header("User-Agent", USER_AGENT)
        self.__config.set_cookie("cf_clearance", cf_clearance)

        self.__name = f"nokufind.Subfinder.{self.__class__.__name__}"

        if (len(cf_clearance) == 0):
            log(f"> [{self.__name}]: This Finder requires a valid cf_clearance cookie.")
            log(f"> [{self.__name}]: Please set the cookie via \"configuration.set_cookie(\"cf_clearance\", [cookie value here])\"")

    def search_posts(self, tags: str | list[str], *, limit: int = 100, page: int | None = None) -> list[Post]:
        self._check_client()

        if type(tags) == list:
            tags = " ".join(tags)

        limit = abs(assert_conversion(limit, int, "limit"))
        current_page = 1 if page == None else page
        posts = []
        EXPECTED_SIZE = 25
        previous_size = EXPECTED_SIZE
        oversized = False

        while (previous_size == EXPECTED_SIZE):
            raw_results = self.__client.search(tags, current_page).results
            previous_size = len(raw_results)

            posts += [self.get_post(post.id) for post in raw_results]

            if (len(posts) >= limit):
                oversized = True
                break

            current_page += 1

        if (oversized):
            return posts[:limit]
        
        return posts

    def get_post(self, post_id: int) -> Post | None:
        self._check_client()

        post_id = str(post_id)

        manga = self.__client.get(post_id)

        return NHentaiFinder.to_post(manga)._set_headers(self.configuration.headers)._set_cookies(self.configuration.cookies) if manga != None else None

    def search_comments(self, *, post_id: int | None = None, limit: int | None = None, page: int | None = None) -> list[Comment]:
        if not post_id:
            request = self._make_request(RANDOM_URL)
            
            if not request:
                return []

            post_id = request.url.split("/")[-2]

        comment_url = (API_URL %(post_id))
        comment_request = self._make_request(comment_url)

        if not comment_request:
            return []
        
        try:
            comment_data = comment_request.json()
        except requests.exceptions.JSONDecodeError as e:
            log(f"> [{self.__name}]: Invalid response data: {e}")
        except Exception as e:
            log(f"> [{self.__name}]: Unexpected exception: {e}")

        return [NHentaiFinder.to_comment(comment) for comment in comment_data]

    def get_comment(self, comment_id: int, post_id: int | None = None) -> Comment | None:
        if not post_id:
            return None

        comments = self.search_comments(post_id = post_id)

        for comment in comments:
            if comment.comment_id == comment_id:
                return comment

        return None
    
    def get_notes(self, post_id: int) -> list[Note]:
        return []

    def post_get_parent(self, post: Post) -> Post | None:
        return None
    
    def post_get_children(self, post: Post) -> list[Post]:
        return []

    def on_client_change(self, key: str, value, is_cookie, is_header):
        if (is_cookie and key == "cf_clearance"):
            self.__cf_config.cf_clearance = value
            self.__source.set_config(self.__cf_config)

    def _check_client(self):
        if (not isinstance(self.__client, Enma)):
            raise RuntimeError(f"Client must be an Enma instance, not {type(self.__client)}.")
        
        if (len(self.__cf_config.cf_clearance) == ""):
            log(f"> [{self.__name}]: This Finder requires a valid cf_clearance cookie.")
            log(f"> [{self.__name}]: Please set the cookie via \"configuration.set_cookie(\"cf_clearance\", [cookie value here])\"")

    def _make_request(self, url) -> requests.Response | None:
        request = requests.get(url, headers = self.configuration.headers, cookies = self.configuration.cookies)
        
        if request.status_code >= 400:
            log(f"> [{self.__name}]: [{request.status_code}]: {request.text.encode()}")
            return None
        
        return request

    @property
    def configuration(self):
        return self.__config
        
