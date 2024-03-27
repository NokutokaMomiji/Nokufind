import requests
from datetime import datetime
from calendar import timegm
from html.parser import HTMLParser
from time import sleep

from pybooru import Moebooru, PybooruHTTPError
from nokufind import Comment, Note, Post

from nokufind.Subfinder import ISubfinder, SubfinderConfiguration
from nokufind.Utils import log, make_request, assert_conversion 


class KonaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.comment_ids = []
        self.in_popular_list = False
        self.popular_posts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div" and ("class", "comment avatar-container") in attrs:
            comment_id = int(attrs[1][1][1:])
            self.comment_ids.append(comment_id)

        if tag == "ul" and ("id", "post-list-posts") in attrs:
            self.in_popular_list = True

        if tag == "li" and self.in_popular_list:
            try:
                possible_id = attrs[1][1]
                if not possible_id.startswith("p"):
                    return
                self.popular_posts.append(int(possible_id[1:]))
            except Exception as e:
                print(e)
    def handle_endtag(self, tag: str) -> None:
        if tag == "ul" and self.in_popular_list:
            self.in_popular_list = False

    def find_comments(self, html):
        self.comment_ids = []
        self.feed(html)
        return self.comment_ids
    
    def find_popular_posts(self, html):
        self.popular_posts = []
        self.feed(html)
        return self.popular_posts
        

class KonachanFinder(ISubfinder):
    @staticmethod
    def to_post(post_data) -> Post:
        return Post(
            post_id = post_data["id"],
            tags = post_data["tags"].split(" "),
            sources = post_data["source"].split(" "),
            images = [post_data["file_url"]],
            authors = [""],
            source = "konachan",
            preview = post_data["preview_url"],
            md5 = [post_data["md5"]],
            rating = post_data["rating"],
            parent_id = post_data["parent_id"],
            dimensions = [(post_data["width"], post_data["height"])],
            poster = post_data["author"],
            poster_id = post_data["creator_id"],
            name = None
        )
    
    @staticmethod
    def to_comment(comment_data) -> Comment:
        return Comment(
            comment_id = comment_data["id"],
            post_id = comment_data["post_id"],
            creator_id = comment_data["creator_id"],
            creator = comment_data["creator"],
            body = comment_data["body"],
            source = "konachan",
            created_at = datetime.strptime(comment_data["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
        )

    @staticmethod
    def to_note(note_data) -> Note:
        return Note(
            note_id = note_data["id"],
            created_at = datetime.strptime(note_data["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"),
            x = note_data["x"],
            y = note_data["y"],
            width = note_data["width"],
            height = note_data["height"],
            body = note_data["body"],
            source = "konachan",
            post_id = note_data["body"]
        )
    
    def __init__(self, username = "", password = "", hash_string = ""):
        self.__client_name = "konachan"

        self.__client = Moebooru(self.__client_name, username = username, password = password, hash_string = hash_string)
        self.__parser = KonaParser()
        
        self.__config = SubfinderConfiguration()
        self.__config._set_property("username", username)
        self.__config._set_property("password", password)
        self.__config._set_property("hash_string", hash_string)

        self.__retries = 0
        self.__MAX_RETRIES = 10

        self.__name = f"nokufind.Subfinder.{self.__class__.__name__}"
        log(f"> [{self.__name}]: Initialized a new {self.__class__.__name__} instance.")

    def search_posts(self, tags: str | list[str], *, limit: int = 100, page: int | None = None) -> list[Post]:
        self._check_client()
        
        tags = " ".join(tags) if (type(tags) == list) else tags
        page = page if page else 1
        raw_posts = self._get_all_posts(tags, limit, page)

        return [KonachanFinder.to_post(post) for post in raw_posts]
    
    def get_post(self, post_id: int) -> Post | None:
        self._check_client()

        post_id = assert_conversion(post_id, int, "post_id")

        try:
            post = self.search_posts(f"id:{post_id}")
        except PybooruHTTPError as e:
            log(f"> [{self.__name}]: Pybooru raised an HTTP Error. Retrying.\n{e}")
            sleep(2)
            
            if (self.__retries >= self.__MAX_RETRIES):
                log(f"> [{self.__name}]: Exceded max retries.")
                self.__retries = 0
                return None
            
            self.__retries += 1
            return self.get_post(post_id)
        except Exception as e:
            log(f"> [{self.__name}]: Failed to get post id {post_id}.\nException: {e}")

        return post[0] if post else None
    
    def search_comments(self, *, post_id: int | None = None, limit: int | None = None, page: int | None = None) -> list[Comment]:
        self._check_client()

        limit = 100 if limit == None else limit
        page = 1 if page == None else page

        return self._get_comments(post_id, limit, page)

    def get_comment(self, comment_id: int, post_id: int | None = None) -> Comment | None:
        self._check_client()

        comment_id = assert_conversion(comment_id, int, "comment_id")
        try:
            raw_comment = self.__client.comment_show(comment_id)
            return KonachanFinder.to_comment(raw_comment)
        except Exception as e:
            log(f"> [{self.__name}]: Failed to get comment id {comment_id}.\n{e}")
            return None
    
    def get_notes(self, post_id: int) -> list[Note]:
        self._check_client()

        post_id = assert_conversion(post_id, int, "post_id")

        try:
            raw_notes = self.__client.note_list(post_id = post_id)
            return [KonachanFinder.to_note(note) for note in raw_notes]
        except Exception as e:
            log(f"> [{self.__name}]: Failed to get notes from post {post_id}.\nException: {e}")
            return []
        
    def post_get_parent(self, post: Post) -> Post | None:
        self._check_client()

        if (type(post) != Post):
            raise TypeError(f"\"post\" should be of type Post, not {post}.")
        
        if (not post.parent_id):
            return None

        parent_post = self.get_post(post.parent_id)

        return post._set_parent(parent_post)
    
    def post_get_children(self, post: Post) -> list[Post]:
        self._check_client()

        if (type(post) != Post):
            raise TypeError(f"\"post\" should be of type Post, not {type(post)}")
        
        children_posts = self.search_posts(f"parent:{post.post_id}")

        for index, child_post in enumerate(children_posts):
            if (child_post.post_id == post.post_id):
                children_posts.pop(index)
                break

        return post._set_children(children_posts)

    # Non-standard methods.
    def get_popular_posts(self, *, date: datetime | None = None, is_month = False) -> list[Post]:
        """
        Returns a list containing the most popular posts.

        By default, the function returns the most popular posts in the last 24 hours.
        However, if you set a ``date``, it will return the most popular posts of the week of the date.

        Alternatively, you can set ``is_month`` to ``True`` to get the popular posts of the month.

        Args:
            date (datetime, optional): The date for the week to check. If ``is_month`` is set to True, it will return the posts of the month instead. Defaults to None.
            is_month (bool, optional): Whether the function should return the posts of the month or the week. Defaults to False.

        Returns:
            list[Post]: A list of the most popular posts of the given timeframe (Default: last 24 hours).
        """
        self._check_client()

        url = f"{self.__client.site_url}/post/popular_recent"

        if (type(date) == datetime):
            url = f"{self.__client.site_url}/post/"
            if is_month:
                url += f"popular_by_month?month={date.month}&year={date.year}"
            else:
                url += f"popular_by_week?day={date.day - date.weekday()}&month={date.month}&year={date.year}"

        request = self._request(url)

        if (request.status_code >= 400):
            log(f"> [{self.__name}]: Url \"{url}\" returned error status code {request.status_code}\n{request.text}")
            return []
        
        post_ids = self.__parser.find_popular_posts(request.text)
        raw_posts = [self.get_post(post) for post in post_ids]

        posts = []

        for post in raw_posts:
            if (not post):
                continue
            posts.append(post)
            
        return posts

    def on_config_change(self, key: str, value, is_cookie: bool, is_header: bool):
        if key in ["username", "password", "hash_string"]:
            username = self.__config.get_config("username")
            password = self.__config.get_config("password")
            hash_string = self.__config.get_config("hash_string")
            self.__client = Moebooru(self.__client_name, username, password, hash_string)

    def _get_all_posts(self, tags: str, limit: int, page: int | None) -> list[dict]:
        all_posts = []
        current_page = page if page != None else 0
        previous_size = 100
        oversized = False


        while (previous_size == 100):
            try:
                raw_posts = self.__client.post_list(tags = tags, limit = 100, page = page)
            except KeyError:
                break
            except PybooruHTTPError as e:
                log(f"> [{self.__name}]: PybooruHTTPError: {e}")
                if "410" in e._msg:
                    break
                else:
                    sleep(1)

                    if (self.__retries >= self.__MAX_RETRIES):
                        log(f"> [{self.__name}]: Max retries exceeded. Returning found posts.")
                        self.__retries = 0
                        break
                    
                    self.__retries += 1
                    continue
                
            previous_size = len(raw_posts)

            all_posts += raw_posts

            if len(all_posts) >= limit:
                oversized = True
                break

            current_page += 1

        if oversized:
            return all_posts[:limit]
        
        return all_posts

    def _get_comments_of_post(self, post_id: int):
        log("In _get_comments_of_post")
        post_id = assert_conversion(post_id, int, "post_id")
        url = f"{self.__client.site_url}/post/show/{post_id}"

        request = requests.get(url)

        if (request.status_code >= 400):
            log(f"> [{self.__name}]: Url \"{url}\" returned error status code {request.status_code}.")
            return []
        
        comment_ids = self.__parser.find_comments(request.text)

        if not comment_ids:
            return []
        
        raw_comments = [self.get_comment(comment) for comment in comment_ids]

        comments = []
        for comment in raw_comments:
            if not comment:
                continue
            comments.append(comment)

        return comments


    def _get_comments(self, post_id: int | None, limit: int = 100, page: int = 1):
        if post_id != None:
            return self._get_comments_of_post(post_id)
        
        url = f"{self.__client.site_url}/comment"

        current_page = page
        all_comments = []
        oversized = False

        while True:
            request_url = url + f"?page={current_page}"
            request = requests.get(request_url)

            if (request.status_code >= 400):
                log(f"> [{self.__name}]: Url \"{request_url}\" returned status code {request.status_code}.")
                break

            comment_ids = self.__parser.find_comments(request.text)
            all_comments += comment_ids

            if (len(all_comments) >= limit):
                oversized = True
                break
        
        all_raw_comments = list(set(all_comments))
        all_comments.clear()
        for comment in all_raw_comments:
            if comment == None:
                continue
            all_comments.append(self.get_comment(comment))

        if oversized:
            return all_comments[:limit]
        
        return all_comments

    def _request(self, url, post = False):
        return make_request(url, post = post, headers = self.configuration.headers, cookies = self.configuration.cookies)

    def _check_client(self):
        if (not isinstance(self.__client, Moebooru)):
            raise RuntimeError(f"Client must be of type Moebooru, not {type(self.__client)}.")
        
    @property
    def configuration(self) -> SubfinderConfiguration:
        return self.__config