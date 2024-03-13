"""
    Post.py

    Nokutoka Momiji


    Contains a Post class representing a wrapper around post data from multiple sources. 
    
    The Post class wraps information such as post ID, tags, sources, images, authors, source, preview, 
    MD5 hashes, rating, parent ID, dimensions, poster, and poster ID. 
    
    It also provides methods for downloading and fetching image data.

    This script relies on built-in Python modules such as os, hashlib, json, threading, and concurrent.futures, 
    as well as external libraries, such as tqdm for progress bars.

"""


from __future__ import annotations

import os
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import requests
from enum import Enum
from reprlib import Repr

from tqdm import tqdm

from nokufind.Utils import make_request, log, expand

class Rating(int, Enum):
        GENERAL = 1
        SENSITIVE = 2
        QUESTIONABLE = 3
        EXPLICIT = 4
        UNKNOWN = 5

def _generate_md5(self, images: list[str]):
    log("> [nokufind.Post]: Generating md5 hashes.")
    if (type(images) != list or len(images) == 0):
        return []
    
    hashes = []

    for image in images:
        image_request = make_request(image)
        if (image_request.status_code > 400):
            hashes.append("")
            continue

        hashes.append(str(hashlib.md5(image_request.content).hexdigest()))

    self._Post__post_data["md5"] = hashes

class Post():
    """A wrapper around post data from multiple sources."""

    # Class variables.
    __rating_general = ["s", "safe", "general", "g"]
    __rating_sensitive = ["sensitive", "s"]
    __rating_questionable = ["questionable", "q"]
    __rating_explicit = ["e", "explicit"]

    # Max number of threads to be used when fetching the data.
    __max_threads = 10

    @staticmethod
    def set_max_threads(self, num_of_threads: int):
        """Sets the maximum number of threads to use when fetching data.

        Args:
            num_of_threads (int): The number of max threads.
        """
        Post.__max_threads = num_of_threads if num_of_threads > 0 else Post.__max_threads

    @staticmethod
    def _get_rating(rating_string: str) -> Rating:
        """[INTERNAL] Returns the corresponding Rating enum value.

        Args
        ~~~~
            rating_string (``str``): The rating string from the post data.

        Returns
        ~~~~~~~
            ``Rating``: The corresponding Rating enum value.
        """

        if (rating_string == None):
            return Rating.UNKNOWN

        rating_string = rating_string.lower()

        if (rating_string in Post.__rating_general):
            return Rating.GENERAL
        
        if (rating_string in Post.__rating_sensitive):
            return Rating.SENSITIVE
        
        if rating_string in Post.__rating_questionable:
            return Rating.QUESTIONABLE
        
        if rating_string in Post.__rating_explicit:
            return Rating.EXPLICIT
        
        return Rating.UNKNOWN
    
    def __init__(self, *, post_id: int, tags: list[str], sources: list[str], images: list[str], authors: list[str], source: str, preview: str, md5: list[str] | None, rating: str | None, parent_id: int | None, dimensions: list[tuple[int, int]], poster: str, poster_id: int, name: str):
        """
        Creates a new Post object. 

        If you are using any of the built-in Finders, you can use the to_post() static methods to automatically generate a Post object
        from the data object itself.

        Args:
            post_id (``int``): The ID of the post.
            tags (``list[str]``): A list containing all of the tags of the post.
            sources (``list[str]``): A list containing the sources of the images.
            images (``list[str]``): A list containing the URLs to the content (content can be anything, really).
            authors (``list[str]``): A list containing the authors of the work.
            source (``str``): A string representing the source from where the post data came from. (Ex: "danbooru", "konachan", etc...)
            preview (``str``): The URL of the image to be used as a preview.
            md5 (``str``): The md5 hash of the image. If None or empty, a list of md5 hashes will be automatically generated from the images.
            rating (``str | None``): The content rating. (Ex: "explicit", "general", etc...)
            parent_id (``int | None``): The ID of the Post's parent. If the Post has no parent, this should be None.
            dimensions (``list[tuple[int, int]]``): A list containing tuples containing the width and height of the images.
            poster (``str``): The username of the poster of the image.
            poster_id (``int``): The ID of the poster of the image.
            name (``str``): The title of the post, if it has any. If set to None, an automatic title will be generated.
        """

        # All post data is stored in a dictionary for easy conversion to a JSON file.
        self.__post_data = {}
        self.__post_data["post_id"] = post_id
        self.__post_data["tags"] = tags
        self.__post_data["sources"] = sources
        self.__post_data["images"] = images
        self.__post_data["authors"] = authors
        self.__post_data["source"] = source
        self.__post_data["preview"] = preview
        self.__post_data["md5"] = md5
        self.__post_data["rating"] = Post._get_rating(rating) if type(rating) != Rating else rating
        self.__post_data["parent_id"] = parent_id
        self.__post_data["poster"] = poster
        self.__post_data["poster_id"] = poster_id
        self.__post_data["filenames"] = [url.split("/")[-1] for url in self.__post_data["images"]]
        self.__post_data["name"] = f"Post #{post_id}" if not name else name
        self.__post_data["dimensions"] = dimensions

        # Some extra information that derives from the aforementioned post data and that should not be included in the exported JSON.
        self.__image = images[0]
        self.__is_video = self.__post_data["images"][0].endswith(".mp4")
        self.__is_zip = self.__post_data["images"][0].endswith(".zip")
        self.__parent = None
        self.__children = []
        self.__headers = {}
        self.__cookies = {}
        self.__data = []
        self.__fetched_data = False

        # If there is no md5 data, we generate it ourselves.
        if (type(self.__post_data["md5"]) != list or len(self.__post_data["md5"]) == 0 or self.__post_data["md5"][0] == None):
            threading.Thread(target=lambda: _generate_md5(self, self.__post_data["images"])).start()

    def __repr__(self):
        rep = Repr()
        param_string = ", ".join([f"{name}={rep.repr(value)}" for name, value in self.__post_data.items()])
        return f"<Post({param_string})>"
    
    def __str__(self):
        return json.dumps(self.__post_data)
    
    def __iter__(self):
        return self.__post_data.copy().__iter__()
    
    def __getitem__(self, key):
        return self.__post_data[key]
    
    def get_image_data(self, *, index: int = 0) -> bytes | None:
        """Requests and returns the data for the image at the given index.

        Args:
            index (``int``, optional): The number of the image to download, starting at 0. Defaults to 0.

        Returns:
            ``bytes | None``: Returns the data of the image, or None if the request failed.
        """
        image_url = self.images[index]
        image_request = make_request(image_url)

        if (image_request.status_code >= 400):
            log(f"> [nokufind.Post]: [{image_request.status_code}]: {image_request.text}")
            return None
        
        return image_request.content

    def download_item(self, path: str, *, index: int = 0) -> str:
        """Downloads and stores the image at the given index.

        Args:
            path (``str``): Directory where to store the downloaded image.
            index (``int``, optional): The number of the image, starting at 0. Defaults to 0.

        Returns:
            ``str``: The path to the downloaded file.
        """
        image_url = self.images[index]
        image_request = make_request(image_url, stream = True, headers = self.__headers, cookies = self.__cookies)

        if (image_request.status_code >= 400):
            log(f"[{image_request.status_code}]: {image_request.text}")
            return ""
        
        os.makedirs(path, exist_ok = True)

        content_size = int(image_request.headers.get("content-length", 1))
        progress = tqdm(total = content_size, unit = "iB", unit_scale = True)

        file_name = os.path.join(path, image_url.split("/")[-1])
        
        try:
            with open(file_name, "wb") as file:
                for data in image_request.iter_content(2048):
                    progress.update(len(data))
                    file.write(data)

            progress.close()
            return file_name
        except Exception as e:
            log(e)
            return ""

    def download_all(self, path: str) -> list[str]:
        """Downloads all of the images of the post.

        Args:
            path (``str``): Path to directory where to store all the files.

        Returns:
            ``list[str]``: List containing the paths to all of the downloaded files.
        """
        return [self.download_item(path, index = i) for i in range(len(self.images))]
    
    def fetch_data(self, only_image: bool = False) -> None:
        """Fetches the data of all of the post's images.

        Args:
            only_image (``bool``, optional): Whether to only download the main image. Defaults to False.
        """
        if (self.fetched_data and len(self.data) == len(self.images)):
            return
        
        session = requests.Session()

        if only_image:
            self.__data = [None]
            self._request_data(self.image, session, 0)
            self.fetched_data = True
            return

        self.__data = [None] * len(self.images)

        url_chunks = [self.images[i:i + Post.__max_threads] for i in range(0, len(self.images), Post.__max_threads)]

        with ThreadPoolExecutor(Post.__max_threads) as executor:
            last_index = 0
            for chunk in url_chunks:
                executor.map(self._request_data, chunk, [session] * len(chunk), list(range(last_index, len(chunk))))
                last_index = len(chunk)

    
    def _request_data(self, image_url: str, session: requests.Session, index: int) -> bool:
        """(Internal) Function used for fetching the data.
        ATTENTION! Do not use this function. Use ``fetch_data`` instead.

        Args:
            image_url (``str``): The URL of the image to fetch.
            session (``requests.Session``): A Session object used to make the request.
            index (``int``): The index where to store the downloaded data.

        Returns:
            ``bool``: Whether the image data was successfully fetched and stored or not.
        """
        response = session.get(image_url, headers = self.__headers, cookies = self.__cookies)

        if (response.status_code >= 400):
            log(f"> [nokufind.Post]: [{response.status_code}]: {response.text}")
            return False
        
        self.data[index] = response.content
        return True

    def _set_parent(self, parent_post: Post) -> Post:
        """(Internal) Used by ``post_get_parent`` to store the parent post.

        Args:
            parent_post (Post): The parent of the current post.

        Returns:
            ``Post``: Returns the parent post object.
        """
        self.__parent = parent_post
        return parent_post

    def _set_children(self, children_posts: list[Post]) -> list[Post]:
        """(Internal) Used by ``post_get_children`` to store the post's children.

        Args:
            children_posts (``list[Post]``): A list containing this post's children.

        Returns:
            ``list[Post]``: Returns the list of children posts.
        """
        self.__children = children_posts.copy()
        return children_posts
    
    def _set_cookies(self, cookies: dict) -> Post:
        """(Internal) Used to set the request cookies for downloading / fetching-related methods.

        Args:
            cookies (``dict``): The cookies to be used for the post's subsequent requests.

        Returns:
            ``Post``: Returns itself.
        """
        if (type(cookies) != dict):
            return self
        
        self.__cookies = cookies
        return self

    def _set_headers(self, headers: dict) -> Post:
        """(Internal) Used to set the request headers for downloading / fetching-related methods.

        Args:
            headers (``dict``): The headers to be used for the post's subsequent requests.

        Returns:
            ``Post``: Returns itself.
        """
        if (type(headers) != dict):
            return self
        
        self.__headers = headers
        return self

    @property
    def post_dict(self) -> dict:
        """Returns a copy of the post data dictionary for external use.

        Returns:
            dict: A dictionary containing all of the stored post data.
        """
        return self.__post_data.copy()

    @property
    def post_id(self) -> int:
        """The post ID.

        Returns:
            ``int``: The post's ID.
        """
        return self.__post_data["post_id"]
    
    @property
    def tags(self) -> list[str]:
        """The list of tags used for the image.

        Returns:
            ``list[str]``: A list containing the tags as strings.
        """
        return self.__post_data["tags"]

    @property
    def tag_string(self) -> str:
        """A string containing all of the tags.

        Returns:
            ``str``: Returns all of the tags in a single string (spaced with spaces).
        """
        return " ".join(self.__post_data["tags"])

    @property
    def sources(self) -> list[str]:
        """The sources of the images.
        In most cases, this is not the booru post URL, but the actual source from where the images came from.

        The data may or may not be actual valid URLs, since most boorus don't actually check that the images have valid sources.

        Returns:
            ``list[str]``: List containing all of the sources.
        """
        return self.__post_data["sources"]
    
    @property
    def images(self) -> list[str]:
        """Returns all of the images from the post.

        Returns:
            ``list[str]``: List containing the URLs of all of the images of the post.
        """
        return self.__post_data["images"]
    
    @property
    def image(self) -> str:
        """The first image of the post.

        Returns:
            str: The URL of the first image of the post.
        """
        return self.__image

    @property
    def authors(self) -> list[str]:
        """Returns the authors of the work.
        Usually the artists related to the work.

        Returns:
            ``list[str]``: List containing the authors of the work.
        """
        return self.__post_data["authors"]
    
    @property
    def source(self) -> str:
        """A string that identifies where the image came from. May be useful for using with the finder or for some external purposes.

        Returns:
            ``str``: A string that identifies where the image came from. (Ex: "danbooru", "pixiv", etc...)
        """
        return self.__post_data["source"]
    
    @property
    def preview(self) -> str:
        """Returns the post's preview image. 
        It is usually a downscaled version of the main image. Helpful for list previous of content.

        Returns:
            ``str``: URL to the preview image.
        """
        return self.__post_data["preview"]
    
    @property
    def md5(self) -> list[str]:
        """The md5 hashes of the images.
        Can be used for sorting and removing duplicate images, as well as used for finding the images in some boorus.

        Returns:
            list[str]: List containing the md5 hashes of the images.
        """
        return self.__post_data["md5"]
    
    @property
    def rating(self) -> Rating:
        """The rating of the image. (Ex: "general", "questionable", "explicit", etc...)

        Returns:
            ``Rating``: A Rating enum value representing the image's rating. 
        """
        return self.__post_data["rating"]
    
    @property
    def parent_id(self) -> int | None:
        """Returns the post's parent ID, if it has one.

        Returns:
            int | None: The ID of the post's parent, or None if the post does not have a parent.
        """
        return self.__post_data["parent_id"]
    
    @property
    def parent(self) -> Post | None:
        """Returns the post's parent, if it has one and has been searched for using ``post_get_parent``.

        Returns:
            ``Post | None``: A Post object containing the post's parent data.
        """
        return self.__parent
    
    @property
    def children(self) -> list[Post]:
        """Returns the post's children, if it has any and have been searched for using ``post_get_children``.

        Returns:
            ``list[Post]``: A list containing the post's children as Post objects.
        """
        return self.__children
    
    @property
    def filenames(self) -> list[str]:
        """The filenames of every image as stored online. Usually the md5 hash but can vary.

        Returns:
            ``list[str]``: List containing the filenames of every image.
        """
        return self.__post_data["filenames"]
    
    @property
    def name(self) -> str:
        """The name of the post, for the sources that support it.

        Returns:
            ``str``: The name of the post, or an auto-generated one.
        """
        return self.__post_data["name"]
    
    @property
    def dimensions(self) -> list[tuple[int, int]]:
        """The dimensions of all of the post's images.

        Returns:
            ``list[tuple[int, int]]``: A list containing tuples with the images' width and height as integers.
        """        
        return self.__post_data["dimensions"]
    
    @property
    def poster(self) -> str:
        """The name of the user who posted the images.

        Returns:
            ``str``: A string containing the poster's username.
        """
        return self.__post_data["poster"]
    
    @property
    def poster_id(self) -> int:
        """The ID of the user who posted the images.

        Returns:
            ``int``: The ID for the user who posted the images, as stored in the original source.
        """
        return self.__post_data["poster_id"]
    
    @property
    def is_video(self) -> bool:
        """Returns whether the post content is an MP4 video or not.

        Returns:
            ``bool``: ``True`` if the post content is an MP4 video.
        """
        return self.__is_video
    
    @property
    def is_zip(self) -> bool:
        """Returns whether the post content is a ZIP file.

        Returns:
            ``bool``: ```True`` if the post content is a ZIP file.
        """
        return self.__is_zip
    
    @property
    def data(self) -> list[bytes]:
        """Returns a list containing the raw fetched data of all the images.

        This list is empty by default. To fill it, use the ``fetch_data`` method.

        Returns:
            ``list[bytes]``: List containing raw content data as bytes.
        """
        return self.__data
    
    @property
    def fetched_data(self) -> bool:
        """Whether the data has been fetched or not.

        Returns:
            ``bool``: ``True`` if the data has been successfully fetched.
        """
        return self.__fetched_data