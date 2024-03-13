"""
    Note.py

    Nokutoka Momiji

    Contains the Note class which represents a note associated with a post. 
    The Note class wraps information such as the note's ID, creation timestamp, coordinates, dimensions, 
    body content, source, and post ID. 
    
    It provides methods for converting the note's body to Markdown format and accessing its properties.

    This script relies on built-in Python modules such as json, datetime, and calendar for handling datetimes.
    It also utilizes the markdownify library for converting HTML-like note bodies to Markdown format.
    
"""

import json
from datetime import datetime
from calendar import timegm
from reprlib import Repr

import markdownify

class Note():
    def __init__(self, *, note_id: int, created_at: datetime, x: int, y: int, width: int, height: int, body: str, source: str, post_id: int):
        """Creates a note object from the given data.

        Args:
            note_id (int): The ID of the note.
            created_at (datetime): A datetime object containing the date and time when the note was created.
            x (int): The X coordinate of the note.
            y (int): The Y coordinate of the note.
            width (int): The width of the note.
            height (int): The height of the note.
            body (str): The text of the note. May include html tags or markdown content.
            source (str): A string identifying where the note came from. (Ex: "danbooru", "gelbooru", etc...)
            post_id (int): The ID of the post where the note is from.
        """
        self.__note_data = {}

        self.__note_data["note_id"] = note_id
        self.__note_data["created_at"] = timegm(created_at.utctimetuple())
        self.__note_data["x"] = x
        self.__note_data["y"] = y
        self.__note_data["width"] = width
        self.__note_data["height"] = height
        self.__note_data["body"] = body
        self.__note_data["source"] = source
        self.__note_data["post_id"] = post_id

    def __repr__(self) -> str:
        rep = Repr()
        pairs = ", ".join([f"{key} = {rep.repr(value)}" for key, value in self.__note_data.items()]).encode("unicode_escape")
        return f"<Note({pairs})>"

    def __str__(self) -> str:
        return json.dumps(self.__note_data)
    
    def __getitem__(self, key):
        return self.__note_data[key]
    
    def __iter__(self):
        return self.__note_data.copy().__iter__()
    
    def body_to_markdown(self) -> str:
        """Returns the contents of the note as Markdown.

        Returns:
            ``str``: String containing the text of the note in Markdown format.
        """
        return markdownify.MarkdownConverter().convert(self.body)

    @property
    def note_id(self) -> int:
        """The ID of the note."""
        return self.__note_data["note_id"]
    
    @property
    def created_at(self) -> int:
        """The timestamp when the note was created."""
        return self.__note_data["created_at"]
    
    @property
    def x(self) -> int:
        """The note's X coordinate relative to the image."""
        return self.__note_data["x"]
    
    @property
    def y(self) -> int:
        """The note's Y coordinate relative to the image."""
        return self.__note_data["y"]
    
    @property
    def width(self) -> int:
        """The width of the box containing the note."""
        return self.__note_data["width"]
    
    @property
    def height(self) -> int:
        """The height of the box containing the note."""
        return self.__note_data["height"]
    
    @property
    def body(self) -> int:
        """The text content of the note. 
        
        May contain HTML tags. Use ``body_to_markdown`` to get the body in Markdown format.
        
        """
        return self.__note_data["body"]
    
    @property
    def source(self) -> str:
        """A string representing where the note came from. (Ex: "danbooru", "gelbooru", etc...)"""
        return self.__note_data["source"]
    
    @property
    def post_id(self) -> int:
        """The ID of the post where the note is located."""
        return self.__note_data["post_id"]