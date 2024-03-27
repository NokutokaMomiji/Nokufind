import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from calendar import timegm
from itertools import combinations
from html.parser import HTMLParser

from pygelbooru import Gelbooru
from pygelbooru.gelbooru import GelbooruImage, GelbooruComment

from nokufind import Post, Comment, Note
from nokufind.Subfinder import ISubfinder, SubfinderConfiguration
from nokufind.Utils import log, assert_conversion, make_request, parse_tags, get

def _parse_notes_data(data):
    # Parse the XML-like data
    root = ET.fromstring(data)

    # Initialize a list to store formatted notes
    formatted_notes = []

    # Loop through each 'note' element
    for note_elem in root.findall('note'):
        note_data = {
            'id': note_elem.get('id'),
            'created_at': note_elem.get('created_at'),
            'updated_at': note_elem.get('updated_at'),
            'body': note_elem.get('body'),
            'position': {'x': note_elem.get('x'), 'y': note_elem.get('y')},
            'dimensions': {'width': note_elem.get('width'), 'height': note_elem.get('height')},
            'creator_id': note_elem.get('creator_id'),
        }

        formatted_notes.append(note_data)

    return formatted_notes

def _post_is_valid(post: GelbooruImage) -> bool:
    return post != None

def _filter_invalid_posts(posts: list[GelbooruImage]) -> list[dict]:
    return [post for post in posts if _post_is_valid(post)]

class GelbooruParser(HTMLParser):
    def __init__(self, *, convert_charrefs: bool = True) -> None:
        super().__init__(convert_charrefs=convert_charrefs)

        self.in_comment_body = False
        self.in_link = False
        self.in_comment_thumb = False
        self.comment_data = []
        self.last_comment = {}
        self.gelbooru = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div" and ("class", "commentBody ") in attrs:
            print(f"{attrs}")
            self.in_comment_body = True
            return
        elif tag == "div" and ("class", "commentThumbnail") in attrs:
            self.in_comment_thumb = True

        if tag == "a" and self.in_comment_body and not self.last_comment.get("@creator_id", None):
            print(f"{attrs}")
            self.last_comment["@creator_id"] = int(attrs[0][1].split("=")[-1])
            self.in_link = True
        elif tag == "a" and self.in_comment_thumb and not self.last_comment.get("@post_id", None):
            self.last_comment["@post_id"] = int(attrs[0][1].split("=")[-1])

    def handle_data(self, data: str) -> None:
        if self.in_comment_body and self.in_link:
            self.last_comment["@creator"] = data.replace("<b>", "")
            return
        
        if self.in_comment_body:
            content = data.split("\n")
            if " commented at " in content[0]:
                content = content[0].split(" commented at ")[-1].split(" » ")
                self.last_comment["@created_at"] = content[0][:-3]
                self.last_comment["@id"] = content[1][1:]
            elif self.last_comment.get("@id") and not self.last_comment.get("@body", None) and content[0] != '':
                self.last_comment["@body"] = "\n".join(content)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.in_link:
            self.in_link = False

        if tag == "div" and self.in_comment_body:
            self.in_comment_body = False
            self.comment_data.append(GelbooruComment(self.last_comment, gelbooru = self.gelbooru))
            self.last_comment = {}
        elif tag == "div" and self.in_comment_thumb:
            self.in_comment_thumb = False

    def get_comments(self, html: str, gelbooru: Gelbooru):
        self.gelbooru = gelbooru
        self.comment_data = []
        self.last_comment = {}
        self.feed(html)
        return self.comment_data

class GelbooruFinder(ISubfinder):
    @staticmethod
    def to_post(post_data: GelbooruImage) -> Post:

        if post_data.source == None:
            post_data.source = ""

        if (not hasattr(post_data, "_payload")):
            print(post_data.__dict__)

        post_data.parent_id = int(post_data._payload["parent_id"])

        return Post(
            post_id = post_data.id,
            tags = post_data.tags,
            sources = post_data.source.split(" "),
            images = [post_data.file_url],
            authors = [""],
            source = "gelbooru",
            preview = post_data._payload["preview_url"],
            md5 = [post_data._payload["md5"]],
            rating = post_data.rating,
            parent_id = post_data.parent_id if post_data.parent_id != 0 else None,
            dimensions = [(post_data.width, post_data.height)],
            poster = post_data._payload["owner"],
            poster_id = int(post_data._payload["creator_id"]),
            name = None
        )
    
    @staticmethod
    def to_comment(comment_data: GelbooruComment) -> Comment:
        return Comment(
            comment_id = comment_data.id,
            post_id = comment_data.post_id,
            creator_id = comment_data.creator_id,
            creator = comment_data.creator,
            body = comment_data.body,
            source = "gelbooru",
            created_at = comment_data.created_at
        )
    
    @staticmethod
    def to_note(note_data: dict) -> Note:
        return Note(
            note_id = note_data["id"],
            created_at = datetime.strptime(note_data["created_at"], "%a %b %d %H:%M:%S %z %Y"),
            x = int(note_data["position"]["x"]),
            y = int(note_data["position"]["y"]),
            width = int(note_data["dimensions"]["width"]),
            height = int(note_data["dimensions"]["height"]),
            body = note_data["body"],
            source = "gelbooru",
            post_id = note_data["post_id"]
        )

    def __init__(self, api_key = None, user_id = None) -> None:
        self.__client = Gelbooru(api_key, user_id)
        self.__config = SubfinderConfiguration()
        self.__config._set_property("api_key", None)
        self.__config._set_property("user_id", None)

        self.__name = f"nokufind.Subfinder.{self.__class__.__name__}"
        log(f"> [{self.__name}]: Initialized a new {self.__class__.__name__} instance.")

    def search_posts(self, tags: str | list[str], *, limit: int = 100, page: int | None = None) -> list[Post]:
        self._check_client()

        if (type(tags) == str):
            tags = tags.split(" ")

        posts = self._get_all_posts(tags = tags, limit = limit, page = page)

        return posts
    
    async def search_posts_async(self, tags: str | list[str], *, limit: int = 100, page: int | None = None) -> list[Post]:
        self._check_client()

        if (type(tags) == str):
            tags = tags.split(" ")

        posts = await self._get_all_posts_async(tags = tags, limit = limit, page = page)

        return posts

    def get_post(self, post_id: int) -> Post | None:
        self._check_client()

        post_id = assert_conversion(post_id, int, "post_id")

        post = asyncio.run(self.__client.get_post(post_id))

        return GelbooruFinder.to_post(post) if post else None
    
    def search_comments(self, *, post_id: int | None = None, limit: int | None = None, page: int | None = None) -> list[Comment]:
        self._check_client()

        if post_id != None:
            post_id = assert_conversion(post_id, int, "post_id")
            
            try:
                raw_comments = asyncio.run(self.__client.get_comments(post_id))
                return [GelbooruFinder.to_comment(comment) for comment in raw_comments]
            except Exception as e:
                log(f"> [{self.__name}]: Getting comments from post failed. This is probably due to Gelbooru having disabled their comment API due to abuse.\n{e}")
                return []
        
    def get_comment(self, comment_id: int, post_id: int | None = None) -> Comment | None:
        self._check_client()

        comment_id = assert_conversion(comment_id, int, "comment_id")

        return None

    def get_notes(self, post_id: int) -> list[Note]:
        self._check_client()

        post_id = assert_conversion(post_id, int, "post_id")

        request = make_request(f"https://gelbooru.com/index.php?page=dapi&s=note&q=index&post_id={post_id}&json=1")

        if (request.status_code >= 400):
            log(f"> [{self.__name}]: Failed to get notes for post {post_id} ({request.status_code}).\n{request.text}")
            return []
        
        raw_notes = _parse_notes_data(request.text)

        for raw_note in raw_notes:
            raw_note["post_id"] = post_id

        return [GelbooruFinder.to_note(note) for note in raw_notes]
    
    def post_get_parent(self, post: Post) -> Post | None:
        self._check_client()
        
        if (type(post) != Post):
            raise TypeError(f"\"post\" must be of type Post, not {type(post)}.")
        
        if (not post.parent_id):
            return None
        
        parent_post = self.get_post(post.parent_id)

        return post._set_parent(parent_post)
    
    def post_get_children(self, post: Post) -> list[Post]:
        self._check_client()

        if (type(post) != Post):
            raise TypeError(f"\"post\" must be of type Post, not {type(post)}.")
        
        children_posts = self.search_posts(f"parent:{post.post_id}")

        for index, child_post in enumerate(children_posts):
            if child_post.post_id == post.post_id:
                children_posts.pop(index)
                break

        return post._set_children(children_posts)
    
    def _get_all_posts(self, tags: str, limit: int = 100, page: int | None = None) -> list[Post]:
        current_posts = []
        current_size = 100
        current_page = page if type(page) == int else 1
        
        while (current_size == 100):
            raw_posts = asyncio.run(self.__client.search_posts(tags = tags, limit = 100, page = current_page))
            current_size = len(raw_posts)

            if (type(raw_posts) == list):
                raw_posts = _filter_invalid_posts(raw_posts)
                posts = [GelbooruFinder.to_post(post) for post in raw_posts]
            elif _post_is_valid(raw_posts):
                posts = [GelbooruFinder.to_post(raw_posts)]
                
            current_posts += posts

            if len(current_posts) >= limit:
                break

            current_page += 1

        current_posts = list(sorted(current_posts, key = lambda x: x.post_id))

        if len(current_posts) > limit:
            return current_posts[:limit]
        
        return current_posts
    
    async def _get_all_posts_async(self, tags: str, limit: int = 100, page: int | None = None) -> list[Post]:
        current_posts = []
        current_size = 100
        current_page = page if type(page) == int else 1
        
        while (current_size == 100):
            raw_posts = await self.__client.search_posts(tags = tags, limit = 100, page = current_page)
            current_size = len(raw_posts)

            if (type(raw_posts) == list):
                raw_posts = _filter_invalid_posts(raw_posts)
                posts = [GelbooruFinder.to_post(post) for post in raw_posts]
            elif _post_is_valid(raw_posts):
                posts = [GelbooruFinder.to_post(raw_posts)]
                
            current_posts += posts

            if len(current_posts) >= limit:
                break

            current_page += 1

        current_posts = list(sorted(current_posts, key = lambda x: x.post_id))

        if len(current_posts) > limit:
            return current_posts[:limit]
        
        return current_posts

    def _check_client(self):
        if (not isinstance(self.__client, Gelbooru)):
            raise RuntimeError(f"Client should be of type Gelbooru, not {type(self.__client)}")

    @property
    def configuration(self):
        return self.__config