"""
    Rule34API.py

    Nokutoka Momiji

    Contains a custom Rule34API class for the Rule34Finder.

    This custom class extends the functionality of the rule34Py library, due to the sheer amount of missing 
    functionality in the original library. 

    This class allows you to fetch and parse more data from the Rule34 API, such as artists' names, notes, and comments.

    This script also includes utility functions for making requests and parsing some Rule34 XML data.

    This is mostly meant for internal use and probably requires a lot more work.
"""


import requests
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from rule34Py import rule34Py
from rule34Py import Post as r34Post
from rule34Py.post_comment import PostComment as r34Comment
from rule34Py.api_urls import API_URLS, __base_url__
from rule34Py.__vars__ import __headers__, __version__

from nokufind.Utils import USER_AGENT

POST_URL = "https://rule34.xxx/index.php?page=post&s=view&id="
NOTE_URL = "https://rule34.xxx/index.php?page=history&type=page_notes&id="
COMMENTS_URL = "https://api.rule34.xxx/index.php?page=dapi&s=comment&q=index&pid="

def _make_request(post_id: int, url: str = POST_URL):
    return requests.get(f"{url}{post_id}", headers = {"User-Agent": USER_AGENT}, cookies = {"resize-original": "1"})

class Rule34Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_artist_tag = False
        self.artist_tag_count = 0
        self.in_note_box = False
        self.in_note_body = False
        self.skipped_first_row = False
        self.in_note_table_row = False
        self.table_data_count = 0
        self.artists = []
        self.note_data = []
        self.note_table_data = []
        self.current_note_table = {}
        self.parse_note_table = False

    def handle_starttag(self, tag, attrs):
        if tag == "li" and ("class", "tag-type-artist tag") in attrs:
            self.in_artist_tag = True
        elif tag == "div" and ("class", "note-box") in attrs:
            self.in_note_box = True

            note_box_attrs = dict(attrs)
            
            self.current_note_data = {
                "width": round(float(note_box_attrs.get("style", "").split("width:")[1].split("px")[0].strip())),
                "height": round(float(note_box_attrs.get("style", "").split("height:")[1].split("px")[0].strip())),
                "x": round(float(note_box_attrs.get("style", "").split("top:")[1].split("px")[0].strip())),
                "y": round(float(note_box_attrs.get("style", "").split("left:")[1].split("px")[0].strip()))
            }
        elif tag == "div" and ("class", "note-body") in attrs:
            self.in_note_body = True
        elif tag == "tr":
            self.in_note_table_row = True

    def handle_endtag(self, tag):
        if tag == "li" and self.in_artist_tag:
            self.in_artist_tag = False
        elif tag == "div" and self.in_note_box:
            self.in_note_box = False
            self.note_data.append(self.current_note_data)
        elif tag == "div" and self.in_note_body:
            self.in_note_body = False
        elif tag == "tr":
            self.in_note_table_row = False
            if (self.skipped_first_row):
                self.note_table_data.append(self.current_note_table)
                self.current_note_table = {}
            self.skipped_first_row = True
            

    def handle_data(self, data):
        if self.in_artist_tag:
            # Skip weird empty string data.
            if not data.strip():
                return
            
            self.artist_tag_count += 1
            
            # Since there is no easy way to discern valid tag data from other stuff,
            # I just keep a counter that grabs each second element out of the three (?, tag, tag_count)
            if (self.artist_tag_count == 2):
                self.artists.append(data.strip())
                return
            
            # We reset after the third element since that is the last one in a single tag.
            if (self.artist_tag_count == 3):
                self.artist_tag_count = 0
        elif self.in_note_body:
            self.current_note_data["body"] = data.strip()
        elif self.in_note_table_row and self.skipped_first_row and self.parse_note_table:
            if not data.strip():
                return
            self.table_data_count += 1

            if (self.table_data_count == 2):
                self.current_note_table["id"] = int(data.strip())
                return
            elif (self.table_data_count == 3):
                self.current_note_table["body"] = data.strip()
                return
            elif(self.table_data_count == 5):
                self.current_note_table["created_at"] = data.strip()
                return
            
            if (self.table_data_count == 6):
                self.table_data_count = 0
            

    def get_artists(self):
        return [artist.replace(" ", "_") for artist in self.artists]
    
    def get_artists_names(self):
        return self.artists.copy()

    def get_note_data(self):
        return self.note_data.copy()
    
    def get_note_table_data(self):
        return self.note_table_data.copy()
    
    def clear_data(self):
        self.artists.clear()
        self.note_data.clear()
        self.note_table_data.clear()
        self.skipped_first_row = False
        self.parse_note_table = False

def _parse_comment_data(xml_string):
    root = ET.fromstring(xml_string)
    
    result = {
        root.tag: []
    }

    for comment_elem in root.findall('comment'):
        comment_dict = {
            'created_at': comment_elem.get('created_at'),
            'post_id': comment_elem.get('post_id'),
            'body': comment_elem.get('body'),
            'creator': comment_elem.get('creator'),
            'id': comment_elem.get('id'),
            'creator_id': comment_elem.get('creator_id')
        }
        result[root.tag].append(comment_dict)

    return result

class Rule34API(rule34Py):
    """
        Custom Rule34API class that derives from rule34Py's rule34Py class.
        
        Mainly created for adding extra data to the Post object as well as getting some data that
        cannot be obtained using the original rule34Py class, such as Notes.
    """

    # Trust me when I say that the data missing from rule34Py really infuriates me.
    # Like... the data is already there in the Rule 34 API's response data.
    # Why not... grab it? Guess we'll never know.

    def __init__(self):
        super().__init__()
        self.__parser = Rule34Parser()

    def search(self, tags: list, page_id: int = None, limit: int = 1000, deleted: bool = False, ignore_max_limit: bool = False):
        # Check if "limit" is in between 1 and 1000
        if not ignore_max_limit and limit > 1000 or limit <= 0:
            raise Exception("invalid value for \"limit\"\n  value must be between 1 and 1000\n  see for more info:\n  https://github.com/b3yc0d3/rule34Py/blob/master/DOC/usage.md#search")
            return

        params = [
            ["TAGS", "+".join(tags)],
            ["LIMIT", str(limit)],
        ]
        url = API_URLS.SEARCH.value
        # Add "page_id"
        if page_id != None:
            url += f"&pid={{PAGE_ID}}"
            params.append(["PAGE_ID", str(page_id)])

        
        if deleted:
            raise Exception("To include deleted images is not Implemented yet!")
            #url += "&deleted=show"

        formatted_url = self._parseUrlParams(url, params)
        response = requests.get(formatted_url, headers=__headers__)
        
        res_status = response.status_code
        res_len = len(response.content)
        ret_posts = []

        # checking if status code is not 200
        # (it's useless currently, becouse rule34.xxx returns always 200 OK regardless of an error)
        # and checking if content lenths is 0 or smaller
        # (curetly the only way to check for a error response)
        if res_status != 200 or res_len <= 0:
            return ret_posts

        for post in response.json():
            r34_post = r34Post.from_json(post)
            r34_post.content = post["file_url"]
            r34_post.parent_id = post["parent_id"] if post["parent_id"] else None
            r34_post.source = post["source"]
            ret_posts.append(r34_post)

        return ret_posts
    
    def get_comments(self, post_id: int) -> list:
        params = [
            ["POST_ID", str(post_id)]
        ]
        formatted_url = self._parseUrlParams(API_URLS.COMMENTS, params) # Replacing placeholders
        response = requests.get(formatted_url, headers=__headers__)

        res_status = response.status_code
        res_len = len(response.content)
        ret_comments = []

        if res_status != 200 or res_len <= 0:
            return ret_comments

        res_xml_base = _parse_comment_data(response.content.decode("utf-8"))
        res_xml = res_xml_base["comments"]

        # loop through all comments
        for comment in res_xml:
            r34_comment = r34Comment(comment["id"], comment["creator_id"], comment["body"], comment["post_id"], comment["created_at"])
            r34_comment.creator = comment["creator"]
            ret_comments.append(r34_comment)


        return ret_comments
    
    def search_comments(self, page_id: int = 1):
        request = _make_request(page_id, COMMENTS_URL)

        if (request.status_code >= 400):
            return []
        
        comments = _parse_comment_data(request.text)["comments"]
        ret_comments = []

        for comment in comments:
            r34_comment = r34Comment(comment["id"], comment["creator_id"], comment["body"], comment["post_id"], comment["created_at"])
            r34_comment.creator = comment["creator"]
            ret_comments.append(r34_comment)

        return ret_comments
    
    def get_artists(self, post_id: int) -> list[str]:
        request = _make_request(post_id)

        if (request >= 400):
            return []
        
        self.__parser.clear_data()
        self.__parser.feed(request.text)

        return self.__parser.get_artists()
    
    def get_notes(self, post_id: int) -> list[dict]:
        request = _make_request(post_id)

        if (request.status_code >= 400):
            return []
        
        self.__parser.clear_data()
        self.__parser.feed(request.text)

        note_data = self.__parser.get_note_data()
        
        for note in note_data:
            note["post_id"] = post_id
            note["id"] = None
            note["created_at"] = None

        num_of_notes = len(note_data)

        table_request = _make_request(post_id, url = NOTE_URL)
        
        if (table_request.status_code >= 400):
            return note_data
        
        self.__parser.clear_data()
        self.__parser.parse_note_table = True
        self.__parser.feed(table_request.text)

        for index, table_data in enumerate(self.__parser.get_note_table_data()):
            if (index >= num_of_notes):
                return note_data

            note = note_data[index]
            note["id"] = table_data["id"]
            note["created_at"] = table_data["created_at"]

        return note_data