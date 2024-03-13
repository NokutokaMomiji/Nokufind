<h1 align="center">
Nokufind
</h1>

<center>

[![GitHub forks](https://img.shields.io/github/forks/NokutokaMomiji/Nokufind)](https://github.com/NokutokaMomiji/Nokufind)
[![GitHub stars](https://img.shields.io/github/stars/NokutokaMomiji/Nokufind)](https://github.com/NokutokaMomiji/Nokufind)
[![GitHub issues](https://img.shields.io/github/issues/NokutokaMomiji/Nokufind)](https://github.com/NokutokaMomiji/Nokufind/issues)

</center>

Nokufind is a Python library that allows you to find posts from multiple Boorus and sources. It also allows you to create custom wrappers around other finders and API modules.

## Requirements
- [Python 3.9+](https://www.python.org/downloads/)
- ChromeDriver (For Pixiv)

## Installation
```python
pip install --upgrade nokufind
```

## Usage

### 1. General usage.
Using Nokufind is as easy as creating a Finder instance and adding Subfinders.

Nokufind comes with a few default Subfinders that can be easily included via the ``add_default()`` method.

```python
import nokufind

# Create a finder.
finder = nokufind.Finder()

# Nokufind comes with some default finders included.
finder.add_default()

# Search posts with tag "rating:safe"
posts = finder.search_posts("rating:safe")

# Show the data.
print(posts[0])
```

### 2. Add more Subfinders.
You can also manually add more Subfinders, as well as indicate specific Subfinders to use.

```python
import nokufind

# All subfinders are located in the nokufind.Subfinder module.
from nokufind.Subfinder import ManganatoFinder

# Create a finder.
finder = nokufind.Finder()

# Add default finder.
finder.add_default()

# Create an instance of a finder.
manganato = ManganatoFinder()

# Add subfinder to finder.
finder.add_subfinder("manganato", manganato)

# You can specify a specific Subfinder to use, if you wish.
manga = finder.search_posts("isekai", client = "manganato")
```

### 3. Using individual Subfinders.
As shown previously, you can use the ``client`` parameter to indicate a specific Subfinder to use.

However, you can also use individual Subfinders, which contain exactly the same base methods as a Finder instance.

```python
# Using the built-in Danbooru Subfinder.
from nokufind.Subfinder import DanbooruFinder

# Create an instance just like with a regular Finder.
danbooru = DanbooruFinder()

# Voila! You can use the same methods in the exact same way.
posts = danbooru.search_posts("hololive", limit = 10, page = 5)

print(posts[0])
```

### 4. Mix and Match
There are multiple methods to acquire multiple data, including posts, comments and, in some cases, notes.

```python
import nokufind

finder = nokufind.Finder()
finder.add_default()

# Using the default Danbooru Subfinder.
post = finder.get_post(7327433, client = "danbooru")

# <Post(post_id=7327433, tags=['2girls', 'blue_eyes', 'blue_pupils', 'bow', 'collared_shirt', 'comic', ...], sources=['https://twit...9275051991268'], images=['https://cdn....4cb6761eb.jpg'], authors=['hana_kon_(17aaammm)'], source='danbooru', preview='https://cdn....4cb6761eb.jpg', md5=['431d91351248...44e34cb6761eb'], rating=<Rating.GENERAL: 1>, parent_id=None, poster='User 739901', poster_id=739901, filenames=['431d91351248...4cb6761eb.jpg'], name='Post #7327433', dimensions=[(1356, 1777)])>

# Get post comments.
comments = finder.search_comments(client = "danbooru", post_id = post.post_id)

# [<Comment(comment_id=2396793, post_id=7327433, creator_id=753402, creator='', body="Is it just m...t's adorable.", source='danbooru', created_at=1710359682)>]

# Get notes
notes = finder.get_notes(post.post_id, client = "danbooru")

# [<Note(b"note_id = 3694423, created_at = 1710361069, x = 190, y = 1482, width = 30, height = 53, body = 'Umm...', source = 'danbooru', post_id = 7327433")>, <Note(b"note_id = 3694422, created_at = 1710361055, x = 10, y = 974, width = 307, height = 477, body = 'Is incredibly cute...', source = 'danbooru', post_id = 7327433")>, <Note(b"note_id = 3694421, created_at = 1710361038, x = 849, y = 997, width = 108, height = 223, body = 'Huh...? This girl...', source = 'danbooru', post_id = 7327433")>, <Note(b"note_id = 3694420, created_at = 1710361027, x = 57, y = 252, width = 105, height = 182, body = 'Grabbing you... like that...', source = 'danbooru', post_id = 7327433")>, <Note(b'note_id = 3694419, created_at = 1710361017, x = 1195, y = 274, width = 80, height = 235, body = "I-I\'m so sorry!", source = \'danbooru\', post_id = 7327433')>]
```

## Data objects
Nokufind's objective is to allow the simple retrieval of data from multiple Boorus and sources. In order to do that, Finders and Subfinders return data using three custom objects: ``Post``, ``Comment`` and ``Note``

### 1. Post
The ``Post`` object allows you to directly interface in a unified manner with the post data acquired from multiple Subfinders.

The Post object contains multiple properties, most notably: post ID, tags, sources, images, etc...

| Property       | Type           | Description                                                                                                                                                                                  |
|----------------|----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| post_dict      | `dict`         | Returns a copy of the post data dictionary for external use.                                                                                                                                 |
| post_id        | `int`          | The post ID.                                                                                                                                                                                 |
| tags           | `list[str]`    | The list of tags used for the image.                                                                                                                                                         |
| tag_string     | `str`          | A string containing all of the tags (spaced with spaces).                                                                                                                                    |
| sources        | `list[str]`    | The sources of the images, not necessarily valid URLs.                                                                                                                                       |
| images         | `list[str]`    | List containing the URLs of all of the images of the post.                                                                                                                                   |
| image          | `str`          | The URL of the first image of the post.                                                                                                                                                      |
| authors        | `list[str]`    | List containing the authors of the work, usually the artists.                                                                                                                                |
| source         | `str`          | Identifies where the image came from (e.g., "danbooru", "pixiv").                                                                                                                            |
| preview        | `str`          | URL to the post's preview image, a downscaled version of the main image.                                                                                                                     |
| md5            | `list[str]`    | List containing the md5 hashes of the images.                                                                                                                                                |
| rating         | `Rating`       | A Rating enum value representing the image's rating.                                                                                                                                         |
| parent_id      | `int` \| `None`| The ID of the post's parent, or None if it does not have one.                                                                                                                                |
| parent         | `Post` \| `None`| A Post object containing the post's parent data, if any.                                                                                                                                      |
| children       | `list[Post]`   | A list containing the post's children as Post objects, if any.                                                                                                                               |
| filenames      | `list[str]`    | List containing the filenames of every image.                                                                                                                                                |
| name           | `str`          | The name of the post, or an auto-generated one for sources that support it.                                                                                                                  |
| dimensions     | `list[tuple[int, int]]` | A list containing tuples with the images' width and height.                                                                                                              |
| poster         | `str`          | The username of the user who posted the images.                                                                                                                                              |
| poster_id      | `int`          | The ID for the user who posted the images, as stored in the original source.                                                                                                                 |
| is_video       | `bool`         | `True` if the post content is an MP4 video.                                                                                                                                                  |
| is_zip         | `bool`         | `True` if the post content is a ZIP file.                                                                                                                                                    |
| data           | `list[bytes]`  | List containing raw content data as bytes. This list is empty by default and can be filled using the `fetch_data` method.                                                                    |
| fetched_data   | `bool`         | `True` if the data has been successfully fetched.                                                                                                                                            |

### 2. Comment
Most Boorus allow for users to add comments to posts. Nokufind allows you to fetch this data in a unified manner via the Comment object.

The Comment object provides a way to interface with comment data from multiple sources.

| Property   | Type  | Description                                                              |
|------------|-------|--------------------------------------------------------------------------|
| comment_id | `int` | The ID of the comment.                                                   |
| post_id    | `int` | The ID of the post where the comment is located.                         |
| creator_id | `int` | The ID of the user who made the comment.                                 |
| creator    | `str` | The name of the user who made the comment.                               |
| body       | `str` | The text content of the comment.                                         |
| source     | `str` | A string representing the source where the comment came from.            |
| created_at | `int` | The timestamp of when the comment was created.                           |

### 3. Note
Certain Boorus have the ability to apply notes on top of images. Nokufind allows you to get note data via the Note object.

| Property   | Type  | Description                                                              |
|------------|-------|--------------------------------------------------------------------------|
| note_id    | `int` | The ID of the note.                                                      |
| created_at | `int` | The timestamp when the note was created.                                 |
| x          | `int` | The note's X coordinate relative to the image.                           |
| y          | `int` | The note's Y coordinate relative to the image.                           |
| width      | `int` | The width of the box containing the note.                                |
| height     | `int` | The height of the box containing the note.                               |
| body       | `int` | The text content of the note. May contain HTML tags.                     |
| source     | `str` | A string representing where the note came from.                          |
| post_id    | `int` | The ID of the post where the note is located.                            |

## Default Subfinders
Nokufind comes with a few Subfinders included:
1. Danbooru
1. Rule34
1. Konachan
1. Yande.re
1. Gelbooru
1. Pixiv
1. Manganato
1. NHentai

The method ``add_default()`` adds the first 5 to a finder instance. All Subfinders can be found in the ``nokufind.Subfinder`` module.

> **Note**: Some Subfinders have custom methods for extra functionality. However, all Subfinders have the same standard methods that can be used with the default Finder object. 

## Expanding with custom Subfinders
Nokufind is designed to be easily expandable with custom sources.

All you need to do is create a class that inherits from ``ISubfinder``, which is found in the Subfinder module. **All Subfinders must inherit from ISubfinder**.

```python
# Importing the ISubfinder interface.
from nokufind import Comment, Post
from nokufind.Subfinder import ISubfinder, SubfinderConfiguration

# Create a custom Subfinder that inherits from the interface
class MyCustomFinder(ISubfinder):
    # You can do some custom initialization stuff.
    def __init__(self) -> None:
        self.configuration = SubfinderConfiguration()
        ...

    # These are required methods. They must be included.
    def search_posts(self, tags: str | list[str], *, limit: int = 100, page: int | None = None) -> list[Post]:
        ...

    def search_comments(self, *, post_id: int = None, limit: int | None = None, page: int | None = None) -> list[Comment]:
        ...

# Create an instance of your custom subfinder.
my_finder = MyCustomFinder()

# Use methods as normal.
posts = my_finder.search_posts("some_tag")

comments = my_finder.search_comments(post_id = posts[0].post_id)
```

## Downloading and Fetching Post Data.
Certain sources do not easily allow for one to gain access to their content outside of their website. For example, sites such as Pixiv or Manganato have a string same-origin policy and block any connections to raw images from any sources that do not have the expected Referer. Other sites may require a User-Agent to interact with the page, or a special cookie, etc...

Nokufind provides simple tools to be able to both download and fetch post data easily.

```python
import nokufind
import random

finder = nokufind.Finder()
finder.add_default()

posts = finder.search_posts("goddess_of_victory:_nikke", limit = 10)

post = random.choice(posts)

# You can download all of the images of a post...
post.download_all("path/to/folder")

# Or you can download a specific image
post.download_item("path/to/folder", index = 0)

# Or you can use the Finder to download all the images of all the posts.
finder.download_fast(posts, "path/to/folder")

# There is also an async version.
# finder.download_fast_async(posts, "path/to/folder")

# You can also fetch the data without downloading it to disk.
post.fetch_data()

# And you can check whether the data was fetched.
if post.fetched_data:
    ...

```