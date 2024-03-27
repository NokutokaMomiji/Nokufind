"""
    Finder.py

    Nokutoka Momiji

    Contains the Finder class that acts as a wrapper around multiple booru / image searching APIs. 
    It allows you to get posts, comments, notes, etc... from various sources. 
    
    The Finder class provides methods for adding and removing subfinders, searching for posts, comments, and notes, 
    downloading images, and more.

    This script utilizes asyncio and threading to handle asynchronous operations and parallel downloading of images. 
    It also makes use of third-party libraries such as httpx and aiometer for HTTP requests and asynchronous processing.
"""

# System Modules
import os
import io
import asyncio
import functools
import threading
from concurrent.futures import ThreadPoolExecutor, wait, thread
from random import shuffle

import httpx
import aiometer

from nokufind import Post, Comment, Note
from nokufind.Subfinder import (ISubfinder,
                                SubfinderConfiguration, 
                                DanbooruFinder, 
                                Rule34Finder,
                                KonachanFinder,
                                YandereFinder,
                                GelbooruFinder,
                                PixivFinder)

from nokufind.Utils import log, split

_list_lock = threading.Lock()

class Finder():
    """
    A wrapper around multiple booru / image searching APIs that allows you to get posts, comments, notes, etc.
    """

    __max_threads = 10

    def __init__(self):
        self.__clients: dict[str, ISubfinder] = {}
        self.__config: SubfinderConfiguration = SubfinderConfiguration()
        self.__config._set_property("aliases", {})
        self.__name = f"nokufind.Finder"
        self.__inner_executor = None
        self.__temp_posts = None

    def add_subfinder(self, name: str, subfinder: ISubfinder) -> None:
        """Adds a subfinder to the list of clients to use in subsequent functions.

        Args:
            name (``str``): The name that will be used to identify the subfinder.
            subfinder (``ISubfinder``): The subfinder to be stored and used.

        Raises:
            ``TypeError``: Raised if the provided subfinder doesn't inherit from ``ISubfinder``.
        """
        if (not isinstance(subfinder, ISubfinder)):
            raise TypeError("Subfinder must inherit from ISubfinder.")
        
        self.__clients[name] = subfinder
        self.__config.get_config("aliases")[name] = {}

    def remove_subfinder(self, name: str) -> None:
        """Removes a subfinder.

        Args:
            name (str): The name of the subfinder to remove.
        """
        self.__clients.pop(name)

    def get_subfinder(self, name: str) -> ISubfinder | None:
        """Returns a subfinder with the given name, if it has one.

        Args:
            name (``str``): The name of the subfinder to look for.

        Returns:
            ``ISubfinder`` | None: The subfinder instance, or None if none was found.
        """
        return self.__clients.get(name, None)
    
    def has_subfinder(self, name: str) -> bool:
        """Checks whether the finder contains a subfinder with the given name.

        Args:
            name (``str``): The subfinder to look for.

        Returns:
            ``bool``: Returns ``True`` if it contains a subfinder with the given name.
        """
        return (name in self.__clients.keys())
    
    def add_default(self, *, danbooru_key = ""):
        """Adds a few built-in subfinders.

        Args:
            danbooru_key (``str``, optional): Key for the Danbooru API. Defaults to "".
        """
        self.add_subfinder("danbooru", DanbooruFinder(danbooru_key))
        self.add_subfinder("rule34", Rule34Finder())
        self.add_subfinder("konachan", KonachanFinder())
        self.add_subfinder("yande.re", YandereFinder())
        self.add_subfinder("gelbooru", GelbooruFinder())

    def set_tag_alias(self, tag: str, alias: str, client: str):
        """Sets an alias for a tag, for a given client.

        This is useful when multiple sources have different tag names for the same thing.

        For example:
            rating:safe -> rating:s

        Args:
            tag (str): The tag that will be aliased.
            alias (str): The alias for the tag.
            client (str): The client that the alias will be applied for.
        """
        self._check_subfinder_exists(client)

        aliases = self.configuration.get_config("aliases")

        if (client not in aliases.keys()):
            aliases[client] = {}

        aliases[client][tag] = alias

    def search_posts(self, tags: str | list[str] = "", *, limit: int = 100, page: int | None = None, client: str | None = None) -> list[Post]:
        """Searches for posts with the given tags.

        Args:
            tags (``str | list[str]``, optional): The tags to match for. Defaults to "".
            limit (``int``, optional): The maximum number of posts to look for per client. Defaults to 100.
            page (``int | None``, optional): The page number. Defaults to None.
            client (``str | None``, optional): The name of the client to use. If None, all clients are used. Defaults to None.

        Returns:
            list[Post]: List containing all the found posts.
        """
        aliases = self.configuration.get_config("aliases")

        if type(client) == str:
            self._check_subfinder_exists(client)
            client_aliases: dict[str, str] = aliases[client]
            result_tags = tags
        
            for tag, alias in client_aliases.items():
                result_tags = result_tags.replace(tag, alias)

            return self.__clients[client].search_posts(tags = result_tags, limit = limit, page = page)
        
        all_posts: list[Post] = []

        for name, subfinder in self.__clients.items():
            result_tags = tags
            client_aliases = aliases[name]

            for tag, alias in client_aliases.items():
                result_tags = result_tags.replace(tag, alias)

            posts = subfinder.search_posts(tags = result_tags, limit = limit, page = page)
            if len(posts) == 0:
                log(f"> [{self.__name}]: Subfinder {name} returned 0 posts.")
            all_posts += posts

        return all_posts
    
    def get_post(self, post_id: int, *, client: str | None = None) -> Post | None:
        """Gets a post with the given ID.

        Args:
            post_id (``int``): ID of the post to look for.
            client (``str | None``, optional): The name of the client to use. If ``None``, all clients will be used. Defaults to None.

        Returns:
            ``Post | None``: Post object containing all the data, or None if no post was found.
        """
        if type(client) == str:
            self._check_subfinder_exists(client)
            return self.__clients[client].get_post(post_id)
        
        for subfinder in self.__clients.values():
            post = subfinder.get_post(post_id = post_id)

            if post != None:
                return post
            
        return None
    
    def search_comments(self, *, client: str | None = None, post_id: int | None = None, limit: int = 100, page: int | None = None) -> list[Comment]:
        """Searches for comments.

        Args:
            client (``str | None``, optional): The subfinder to use. If None, all subfinders will be used. Defaults to None.
            post_id (``int | None``, optional): The ID of the post to get the comments from. Defaults to None.
            limit (``int``, optional): The maximum number of comments to return per client. Defaults to 100.
            page (``int | None``, optional): The page number. Defaults to None.

        Returns:
            list[Comment]: List containing all the found comments.
        """
        if type(client) == str:
            self._check_subfinder_exists(client)
            return self.__clients[client].search_comments(post_id = post_id, limit = limit, page = page)
        
        all_comments = []

        for subfinder in self.__clients.values():
            comments = subfinder.search_comments(post_id = post_id, limit = limit, page = page)
            all_comments += comments

        return all_comments

    def get_comment(self, comment_id: int, post_id: int | None = None, *, client: str | None = None) -> Comment | None:
        """Returns a comment with the given ID.

        Args:
            comment_id (``int``): The ID of the comment to look for.
            client (``str | None``, optional): The subfinder to use. If None, all subfinders will be used. Defaults to None.

        Returns:
            ``Comment | None``: A Comment object containing the data, or None if no comment was found.
        """
        if type(client) == str:
            self._check_subfinder_exists(client)
            return self.__clients[client].get_comment(comment_id, post_id)
        
        for subfinder in self.__clients.values():
            comment = subfinder.get_comment(comment_id, post_id)
            
            if comment != None:
                return comment
            
        return None
    
    def get_notes(self, post_id: int, *, client: str | None = None) -> list[Note]:
        """Gets the notes of a post.

        Args:
            post_id (``int``): The ID of the post to get the notes from.
            client (``str | None``, optional): The subfinder to use. If None, all subfinders will be used. Defaults to None.

        Returns:
            ``list[Note]``: A list containing the notes.
        """
        if type(client) == str:
            self._check_subfinder_exists(client)
            return self.__clients[client].get_notes(post_id)
        
        all_notes = []
        for subfinder in self.__clients.values():
            notes = subfinder.get_notes(post_id)
            all_notes += notes

        return all_notes

    def post_get_parent(self, post: Post, *, client: str | None = None) -> Post:
        """Gets the parent post of a post.

        Args:
            post (``Post``): The post to find the parent of.
            client (``str | None``, optional): The subfinder to use. If None, all subfinders will be used. Defaults to None.

        Returns:
            ``Post``: The parent post of the post.
        """
        if type(client) == str:
            self._check_subfinder_exists(client)
            return self.__clients[client].post_get_parent(post)
        
        for subfinder in self.__clients.values():
            parent_post = subfinder.post_get_parent(post)

            if parent_post != None:
                return parent_post
            
        return None

    def post_get_children(self, post: Post, *, client: str | None = None) -> list[Post]:
        """Gets the children posts of the a post.

        Args:
            post (``Post``): The post to find the children of.
            client (``str | None``, optional): The subfinder to use. If None, all subfinders are used. Defaults to None.

        Returns:
            list[Post]: _description_
        """
        if type(client) == str:
            self._check_subfinder_exists(client)
            return self.__clients[client].post_get_children(post)
        
        all_children = []

        for subfinder in self.__clients.values():
            children_post = subfinder.post_get_children(post)
            all_children += children_post

        return all_children
    
    async def search_posts_async(self, tags: str | list[str] = "", *, limit: int = 100, page: int | None = None, client: str | None = None) -> list[Post]:
        if type(client) == str:
            return self.search_posts(tags, limit = limit, page = page, client = client)
        
        aliases = self.configuration.get_config("aliases")
        all_posts: list[Post] = []

        async def _search(client: tuple[str, ISubfinder]):
            client_name = client[0]
            client_subfinder = client[1]

            client_aliases = aliases[client_name]

            result_tags = tags

            for tag, alias in client_aliases.items():
                result_tags = result_tags.replace(tag, alias)

            if (hasattr(client_subfinder, "search_posts_async")):
                return await client_subfinder.search_posts_async(result_tags, limit = limit, page = page)

            return client_subfinder.search_posts(result_tags, limit = limit, page = page)

        async with aiometer.amap(_search, self.__clients.items()) as results:
            async for result in results:
                all_posts += result

        return all_posts

    def download_fast(self, post_list: list[Post], directory: str) -> list[str]:
        """Downloads all of the images in a list of posts to the provided directory.

        Args:
            post_list (``list[Post]``): A list containing all of the posts to download.
            directory (``str``): A path to a directory. If the path doesn't exist, it will be created.

        Raises:
            ``TypeError``: Raised if post_list is not a list.

        Returns:
            ``list[str]``: List containing the paths to all of the downloaded files.
        """
        return asyncio.run(self.download_fast_async(post_list, directory))

    async def download_fast_async(self, post_list: list[Post], directory: str) -> list[str]:
        """Downloads all of the images in a list of posts to the provided directory.

        Args:
            post_list (``list[Post]``): A list containing all of the posts to download.
            directory (``str``): A path to a directory. If the path doesn't exist, it will be created.

        Raises:
            ``TypeError``: Raised if post_list is not a list.

        Returns:
            ``list[str]``: List containing the paths to all of the downloaded files.
        """
        if (type(post_list) != list):
            raise TypeError("Value should be a list of Post objects. Try using search_posts().")
        
        os.makedirs(directory, exist_ok = True)

        # In an attempt to minimize the amount of constant requests to a single source
        # we create a shuffled version of the list. If there are posts of multiple sources,
        # this could theoretically lower the amount of requests to a single source at a time.
        temp_post_list = post_list.copy()
        shuffle(temp_post_list)

        client = httpx.AsyncClient()
        request_function = functools.partial(self._download_and_safe, client, directory)
        end_paths = []

        async with aiometer.amap(request_function, post_list, max_at_once = 10, max_per_second = 10) as results:
            async for result in results:
                end_paths += result

        return end_paths
    
    def fetch_data(self, posts: list[Post], only_main_image: bool = False, *, should_block: bool = True) -> None:
        """Fetches the data from all the posts in the list.

        Args:
            posts (``list[Post]``): A list containing all the posts to fetch the data for.
            only_main_image (``bool``, optional): Whether only the data of the main image should be fetched. Defaults to False.
            should_block (``bool``, optional): Whether the main thread should be blocked until all data has been fetched. Defaults to True.
        """
        self.cancel_fetch()

        if (len(posts) == 0):
            log(f"> {self.__name}: WARNING! Post list was empty. Exiting.")
            return

        log(f"> {self.__name}: Main thread {'WILL' if should_block else 'WILL NOT'} be blocked.")

        self.__temp_posts = posts.copy()
        #post_chunks = [posts[i:i + Finder.__max_threads] for i in range(0, len(posts), Finder.__max_threads)]

        #with ThreadPoolExecutor(Finder.__max_threads) as executor:
        executor = ThreadPoolExecutor(Finder.__max_threads)

        self.__inner_executor = executor
        
        futures = []
        for index, post in enumerate(posts):
            future = executor.submit(self._fetch_data_post, post, only_main_image, should_block)
            futures.append(future)

        if should_block:
            wait(futures)

    def cancel_fetch(self):
        if (not self.__inner_executor or not self.__temp_posts):
            return
        
        self.__inner_executor.shutdown(False, cancel_futures = True)
        self.__inner_executor = None

        if (not self.__temp_posts):
            return
        
        for post in self.__temp_posts:
            post.cancel_fetch()

        del self.__temp_posts
        self.__temp_posts = None


    def filter_by_md5(self, posts: list[Post], generate_md5: bool = False):
        hash_list = []

        def check(post):
            if generate_md5 and len(post.md5) == 0:
                post.generate_md5()
            
            if type(post.md5) != list:
                log(f"> {self.__name}: WARNING! Post has invalid md5 property. {post}")
                return True

            for md5_hash in post.md5:
                if md5_hash in hash_list:
                    return False
                hash_list.append(md5_hash)

            return True
        
        return list(filter(check, posts))

    def _fetch_data_post(self, post: Post, only_main_image: bool, should_block: bool):
        """(Internal) Function that calls a post's fetch_data method. Used together with the ThreadPoolExecutor.
        
        ATTENTION! You should not use this function, use `fetch_data` instead.

        Args:
            post (``Post``): The post to fetch the data for.
            only_main_image (``bool``): Whether only the data of the main image should be fetched. Defaults to False.
            should_block (``bool``): Whether the main thread should be blocked until all data has been fetched. Defaults to True.
        """
        post.fetch_data(only_main_image, should_block = should_block)

    async def _download_and_safe(self, client: httpx.AsyncClient, directory: str, post: Post) -> list[str]:
        """(Internal) Function for doing the actual downloading. It creates threads for each image in a post.
        
        ATTENTION! You should not use this function, use ``download_fast`` or ``download_fast_async`` instead.

        Args:
            client (``httpx.AsyncClient``): An Asynchronous Client to use for making the requests.
            directory (``str``): The directory where the images will be stored in.
            post (``Post``): The Post object with the images to download.

        Returns:
            ``list[str]``: List containing the paths of the downloaded images.
        """
        def store_response(list_ref: list, directory: str, filename: str, response: httpx.Response):
            """(Internal) Handles the request for an image, writes the content to a file, and stores the path to the file
            in the given list, using a lock to make sure that it is the only one writing to it.

            Args:
                list_ref (list): The list where to store the path to the downloaded file.
                directory (str): The directory where to store the file.
                filename (str): The filename of the file.
                response (httpx.Response): The response object from the request.
            """
            if response.status_code >= 400:
                log(f"> [{self.__name}]: Request returned {response.status_code} for \"{response.url}\".")
                return
            
            file_path = os.path.join(directory, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)

            with _list_lock:
                list_ref.append(file_path)

        end_paths: list[str] = []
        threads: list[threading.Thread] = []
        
        # For each image request, we create a thread to handle storing the file.
        for index, image in enumerate(post.images):
            response = await client.get(image, timeout = None, headers = post._Post__headers, cookies = post._Post__cookies)
            thread = threading.Thread(target = lambda: store_response(end_paths, directory, post.filenames[index], response))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        return end_paths
            
    def on_config_change(self, key: str, value, is_cookie: bool, is_header: bool):
        """(Internal) Callback function for when the configuration settings are modified.

        Args:
            key (str): The key that was changed.
            value (Any): The value to which the key was changed to.
            is_cookie (bool): Whether the key was a request cookie.
            is_header (bool): Whether the key was a request header.
        """
        for client in self.__clients.values():
            client_method = client.configuration.set_cookie if is_cookie else client.configuration.set_header
            client_method = client.configuration.set_header if is_header else client_method

            client_method(key, value)

    def _check_subfinder_exists(self, client: str):
        """(Internal) Simply checks if the subfinder is stored in the clients list.

        Args:
            client (str): The name of the subfinder.

        Raises:
            ``ValueError``: Raised if there is no Subfinder with the given client name.
        """
        if not client in self.__clients.keys():
            raise ValueError(f"Finder contains no Subfinder named \"{client}\".")
        
    @property
    def finders(self) -> list[ISubfinder]:
        """Returns the list of subfinders.

        Returns:
            ``list[ISubfinder]``: A list containing the subfinders stored within this finder instance.
        """
        return self.__clients
    
    @property
    def configuration(self) -> SubfinderConfiguration:
        """Returns the configuration object for the finder, which can be used to set configuration for all subfinders, as well
        as request headers and cookies.

        All modifications to this configuration object will apply to all subfinders. If you wish to modify the configuration for a
        specific subfinder, you can use the ``get_subfinder`` method to access the subfinder's configuration object directly.

        Returns:
            ``SubfinderConfiguration:`` A configuration object used by the finder. 
        """
        return self.__config