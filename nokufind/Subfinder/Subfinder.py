"""
    ISubfinder.py

    Nokutoka Momiji

    Contains the ISubfinder interface to be used for creating Subfinders, as well as the SubfinderConfiguration class
    for configuring Subfinder properties.

    This ensures that all Subfinders must provide the same methods, returning data in the exact same manner, bringing uniformity.
"""

from abc import ABC, abstractmethod
from typing import Callable, Any

from nokufind import Post, Comment, Note
from nokufind.Utils import PIXIV_REFERER

class SubfinderConfiguration():
    """A class for configuring Subfinder properties"""

    def __init__(self, callback: Callable[[str, Any, bool, bool], None] = None):
        """Initializes the configuration object.

        Args:
            callback (``Callable[[str, Any, bool, bool], None]``, optional): Callback function to execute when a change to the settings is made. Defaults to None.
        """
        self.__config = {}
        self.__config["cookies"] = {
            "cf_clearance": ""
        }
        self.__config["headers"] = {
            "User-Agent": "",
            "Referer": PIXIV_REFERER
        }
        self.__config["api_key"] = None
        self.__callback = callback

    def set_cookie(self, key: str, value: str | bytes) -> None:
        """Sets a request cookie.

        Args:
            key (str): The name of the cookie
            value (str | bytes): The value of the cookie
        """
        self._check_valid_value_type(key)
        self._check_valid_value_type(value)

        self.__config["cookies"][key] = value
        
        if (callable(self.__callback)):
            self.__callback(key, value, True, False)

    def get_cookie(self, key: str) -> str | bytes:
        """Returns a request cookie

        Args:
            key (str): The name of the cookie.

        Returns:
            ``str | bytes``: The value of the cookie. 
        """
        self._check_valid_value_type(key)
        
        return self.__config["cookies"][key]
    
    def set_header(self, key: str, value: str | bytes):
        """Sets a request header key.

        Args:
            key (``str``): The name of the header key.
            value (``str | bytes``): The value of the header key.
        """
        self._check_valid_value_type(key)
        self._check_valid_value_type(value)

        self.__config["headers"][key] = value
        
        if (callable(self.__callback)):
            self.__callback(key, value, False, True)

    def get_header(self, key: str) -> str | bytes:
        """Returns a request header value

        Args:
            key (``str``): The key of the request header value.

        Returns:
            ``str | bytes``: The request header key value.
        """
        self._check_valid_value_type(key)

        return self.__config["headers"][key]
    
    def set_config(self, key: str, value):
        """Sets the value for a setting.

        Args:
            key (``str``): The name of the setting.
            value (``Any``): The value for the setting.

        Raises:
            ``ValueError``: Raised if the key is a header key or a cookie.
        """
        if (key in ["cookies", "headers"] or key not in self.__config):
            raise ValueError(f"Invalid key \"{key}\".")
        
        self.__config[key] = value

        if (callable(self.__callback)):
            self.__callback(key, value, False, False)

    def get_config(self, key: str, default_value = None):
        """Returns the value of a setting. 
        
        If the setting is not found, it returns the default value.

        Args:
            key (``str``): The name of the setting.
            default_value (``Any``, optional): The default value to return if the setting is not found. Defaults to None.

        Returns:
            ``Any``: The value of the setting, or the default value if the setting does not exist.
        """
        if (key == "cookies"):
            return self.cookies
        
        if (key == "headers"):
            return self.headers
        
        return self.__config.get(key, default_value)
    
    def _set_property(self, key: str, default_value):
        """(Internal) This function is only meant for Subfinders to use for adding the settings they require for functioning.

        ATTENTION! Do not use this function, use ``set_header``, ``set_cookie`` or ``set_config`` instead.

        Args:
            key (``str``): The name of the setting.
            default_value (``Any``): The default value for the setting.

        Raises:
            ``ValueError``: Raised if an attempt is made to configure header values or cookies.
        """
        if (key in ["cookies", "headers"]):
            raise ValueError("Do not use _set_property for configuring headers or cookies, use the respective functions.")
        
        self.__config[key] = default_value

    def _check_valid_value_type(self, value):
        """(Internal) Used to check that the value's type is valid for request header / cookie use.

        Args:
            value (Any): Value to check. 

        Raises:
            ``TypeError``: Raised if the value is not of type ``str`` or ``bytes``
        """
        if (type(value) not in [str, bytes]):
            raise TypeError(f"Value should be of type str or bytes, received {type(value)}.")
    
    def __getitem__(self, key: str):
        return self.get_config(key)

    @property
    def headers(self) -> dict[str | bytes]:
        """Returns the headers as configured.

        Returns:
            ``dict[str | bytes]``: A dictionary containing the request headers as configured.
        """
        return self.__config["headers"].copy()
    
    @property
    def cookies(self) -> dict[str | bytes]:
        """Returns the cookies as configured.

        Returns:
            ``dict[str | bytes]``: A dictionary containing the request cookies as configured.
        """
        return self.__config["cookies"].copy()

    @property
    def cf_clearance(self) -> str:
        """Used for returning the "cf_clearance" cookie value."""
        return self.__config["cookies"]["cf_clearance"]
    
    @property
    def user_agent(self) -> str:
        """Returns the request "User-Agent" header value."""
        return self.__config["headers"]["User-Agent"]
    
    @property
    def referer(self) -> str:
        """Returns the request "Referer" header value"""
        return self.__config["headers"]["Referer"]
    
    @property
    def api_key(self) -> str:
        """Returns an API key, if set."""
        return self.__config["api_key"]

class ISubfinder(ABC):
    # Static methods.

    """
        All Finders must implement functions to transform the data acquired from the API
        into a general Post, Comment or Note object.
    """

    @staticmethod
    @abstractmethod
    def to_post(post_data) -> Post:
        """(Internal) Creates a Post object from the given data.

        Args:
            post_data (``Any``): An object containing all of the data from the post, acquired from the API.

        Returns:
            ``Post``: A Post object containing the extracted data.
        """
        ...

    @staticmethod
    @abstractmethod
    def to_comment(comment_data) -> Comment:
        """(Internal) Creates a Comment object from the given data.

        Args:
            comment_data (``Any``): An object containing all of the data from the comment, acquired from the API.

        Returns:
            ``Comment``: A Comment object containing the extracted data.
        """
        ... 

    @staticmethod
    @abstractmethod
    def to_note(note_data) -> Note:
        """(Internal) Creates a Note object from the given data.

        Args:
            note_data (``Any``): An object containing all of the data from the note, acquired from the API.

        Returns:
            ``Note``: A Note object containing the extracted data.
        """
        ...

    @abstractmethod
    def search_posts(self, tags: str | list[str], *, limit: int = 100, page: int | None = None) -> list[Post]:
        """Searches for posts that match the given tags.

        Args:
            tags (``str | list[str]``): A string or list of tags to match against.
            limit (``int``, optional): The maximum number of posts to get. Defaults to 100.
            page (``int | None``, optional): The page number. Defaults to None.

        Returns:
            ``list[Post]``: A list containing all the found posts.
        """
        ...

    @abstractmethod
    def get_post(self, post_id: int) -> Post | None:
        """Searches for a post with the given ID.

        Args:
            post_id (``int``): The ID of the post to look for.

        Returns:
            ``Post | None``: The post, or None if a post with the ID was not found.
        """
        ...

    @abstractmethod
    def search_comments(self, *, post_id: int = None, limit: int | None = None, page: int | None = None) -> list[Comment]:
        """Searches for comments.

        Args:
            post_id (``int``, optional): The ID of the post to get the comments from. Defaults to None.
            limit (``int | None``, optional): The maximum number of comments to get. Defaults to None.
            page (``int | None``, optional): The page number. Defaults to None.

        Returns:
            ``list[Comment]``: A list containing the found comments.
        """
        ...

    @abstractmethod
    def get_comment(self, comment_id: int, post_id: int | None = None) -> Comment | None:
        """Searches for a comment with the given ID.

        Args:
            comment_id (``int``): The ID of the comment to look for.

        Returns:
            ``Comment | None``: The comment, or None if a matching comment was not found.
        """
        ...

    @abstractmethod
    def get_notes(self, post_id: int) -> list[Note]:
        """Searches for the notes in a given post.

        Args:
            post_id (``int``): The ID of the post to get the notes from.

        Returns:
            ``list[Note]``: A list containing the found notes.
        """
        ...

    @abstractmethod
    def post_get_parent(self, post: Post) -> Post | None:
        """Searches for the parent post of a post.

        Args:
            post (``Post``): The post.

        Returns:
            ``Post | None``: The parent post, or None if the post has no parent.
        """
        ...

    @abstractmethod
    def post_get_children(self, post: Post) -> list[Post]:
        """Searches for the children posts of a post.

        Args:
            post (``Post``): The post.

        Returns:
            ``list[Post]``: A list containing the children of the post.
        """
        ...

    @property
    @abstractmethod
    def configuration(self) -> SubfinderConfiguration:
        """The Subfinder configuration object.

        This can be used to set any settings related to the current Subfinder.

        Returns:
            SubfinderConfiguration: The Subfinder configuration object.
        """
        ...