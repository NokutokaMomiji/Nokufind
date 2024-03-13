import requests
import xml.etree.ElementTree as ET
from math import ceil

_cookies = {
    "cf_clearance": "4PtNZd5PGSDKDBXhASc1z_mC.tKc.ggMrvxhx2s3GdE-1709327262-1.0.1.1-azAPC335pQo4d9v.0TqPligg5htX.RtlAn36lYJx1Vc9IHvYDWrWjSBCaxciXtfGeawADZZ9MDQG2c7iXT27vA"
}

_headers = {
    "Referer": "https://app-api.pixiv.net/"
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0"
PIXIV_REFERER = "https://app-api.pixiv.net/"

should_log = False

def make_request(url: str, params = None, *, post: bool = False, cookies = _cookies, headers = _headers, stream: bool = False):
    request_function = requests.get if not post else requests.post
    return request_function(url, params = params, headers = headers, cookies = cookies, stream = stream)

def parse_xml(xml_string: str):
    # Parse the XML string
    root = ET.fromstring(xml_string)

    # Convert XML to a Python dictionary
    def parse_element(element):
        result = {}
        for child in element:
            if child:
                child_data = parse_element(child)
                if child.tag in result:
                    if type(result[child.tag]) is list:
                        result[child.tag].append(child_data)
                    else:
                        result[child.tag] = [result[child.tag], child_data]
                else:
                    result[child.tag] = child_data
            else:
                result[child.tag] = child.text
        return result

    return parse_element(root)

def attempt_conversion(item, new_type):
    try:
        return new_type(item)
    except:
        return item
    
def assert_conversion(item, new_type, item_name: str = ""):
    item = attempt_conversion(item, new_type)
    item_name = "Element" if len(item_name) == 0 else item_name

    if (type(item) != new_type):
        raise TypeError(f"{item_name} must be {new_type}, not {type(item)}.")

    return item
    
def log(content):
    if not should_log:
        return
    print(content)

def get(list_ref: list, index: int, default_value = None):
    if (index >= len(list_ref)):
        return default_value
    
    return list_ref[index]

def parse_tags(tags):
    current_text = ""
    tag_list = []
    num_of_parenthesis = 0
    
    tags = tags if type(tags) == str else " ".join(tags)

    for index, char in enumerate(tags):
        if char == " " and num_of_parenthesis == 0:
            tag_list.append(current_text)
            current_text = ""
            continue

        num_of_parenthesis += 1 if char == '(' else (-1 if char == ')' else 0)

        if num_of_parenthesis < 0:
            raise SyntaxError(f"Unmatched closing parenthesis found in tags.\n    {tags}\n    {'~' * index}^")

        current_text += char
    
    tag_list.append(current_text)

    return tag_list

def expand(list_ref, new_size, value = None):
    current_len = len(list_ref)

    if (new_size <= current_len):
        return
    
    difference = new_size - current_len

    for _ in range(difference):
        list_ref.append(value)

def split(list_ref, num_of_splits):
    split_lists = []
    max_num_of_items = ceil(len(list_ref) / num_of_splits)

    current_list = []
    current_list_count = 0

    for item in list_ref:
        current_list.append(item)
        current_list_count += 1

        if current_list_count >= max_num_of_items:
            split_lists.append(current_list)
            current_list = []
            current_list_count = 0

    return split_lists

