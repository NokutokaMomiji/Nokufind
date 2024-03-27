"""
Nokufind
~~~~~~~~

A library that allows you to find posts from multiple Boorus and sources.
It also allows you to create custom wrappers around other finders and API modules.
"""

__title__ = "nokufind"
__author__ = "Nokutoka Momiji"
__license__ = "MIT"
__copyright__ = "Copyright (C) 2024 Nokutoka Momiji"
__version__ = "1.0.4"

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from nokufind.Post import Post
from nokufind.Comment import Comment
from nokufind.Note import Note
from nokufind.Finder import Finder
from nokufind.Subfinder import builtin_finders
from nokufind.Utils import Utils