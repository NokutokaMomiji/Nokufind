import json
from datetime import datetime
from calendar import timegm
from reprlib import Repr

import markdownify

class Comment():
    """A wrapper around comment data from multiple sources."""

    def __init__(self, *, comment_id: int, post_id: int, creator_id: int, creator: str, body: str, source: str, created_at: datetime):
        """Creates a new Comment object.

        If you are using any of the built-in Finders, you can use the to_post() static methods to automatically generate a Comment object
        from the data object itself.

        Args:
            comment_id (``int``): The ID of the comment.
            post_id (``int``): The ID of the post where the comment is located.
            creator_id (``int``): The ID of the creator of the comment.
            creator (``str``): The name of the creator of the comment.
            body (``str``): The content of the comment.
            source (``str``): A string representing the source from where the comment data came from. (Ex: "danbooru", "konachan", etc...)
            created_at (``datetime``): A datetime object containing the date information. This will be transformed into a UTC timestamp.
        """
        self.__comment_data = {}

        self.__comment_data["comment_id"] = comment_id
        self.__comment_data["post_id"] = post_id
        self.__comment_data["creator_id"] = creator_id
        self.__comment_data["creator"] = creator
        self.__comment_data["body"] = body
        self.__comment_data["source"] = source
        self.__comment_data["created_at"] = timegm(created_at.utctimetuple())

    def __repr__(self):
        rep = Repr()
        content = ", ".join([f"{key}={rep.repr(value)}" for key, value in self.__comment_data.items()])
        return f"<Comment({content})>"

    def __str__(self):
        return json.dumps(self.__comment_data)
    
    def __getitem__(self, key):
        return self.__comment_data[key]
    
    def __iter__(self):
        return self.__comment_data.copy().__iter__()
    
    def body_to_markdown(self):
        return markdownify.MarkdownConverter().convert(self.body)

    @property
    def comment_id(self) -> int:
        """The ID of the comment.

        Returns:
            int: The ID of the comment.
        """
        return self.__comment_data["comment_id"]
    
    @property
    def post_id(self) -> int:
        """The ID of the post where the comment is located.

        Returns:
            int: The ID of the post.
        """
        return self.__comment_data["post_id"]
    
    @property
    def creator_id(self) -> int:
        """The ID of the user who made the comment.

        Returns:
            int: The user ID.
        """
        return self.__comment_data["creator_id"]
    
    @property
    def creator(self) -> str:
        """The name of the user who made the comment.

        Returns:
            str: The username.
        """
        return self.__comment_data["creator"]
    
    @property
    def body(self) -> str:
        """The text content of the comment.

        Use ``body_to_markdown`` to get the body in Markdown format.

        Returns:
            str: The text of the comment.
        """
        return self.__comment_data["body"]
    
    @property
    def source(self) -> str:
        """A string representing the source where the comment came from. (Ex: "danbooru", "pixiv", etc...)"""
        return self.__comment_data["source"]
    
    @property
    def created_at(self) -> int:
        """The timestamp of when the comment was created."""
        return self.__comment_data["created_at"]