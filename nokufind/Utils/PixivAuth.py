"""
    PixivAuth.py

    Nokutoka Momiji

    This script derives from ZipFile's Pixiv OAuth script (https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362)
"""

import requests
import platform
import io
import time
import json
import re
import os
from base64 import urlsafe_b64encode
from hashlib import sha256
from secrets import token_urlsafe
from urllib.parse import urlencode
from zipfile import ZipFile

from appdirs import user_data_dir
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from nokufind.Utils import log

CHROMEDRIVER_URL = "https://chromedriver.storage.googleapis.com/91.0.4472.101/"
CHROMEDRIVER_FILES = {
    "Windows": "chromedriver_win32.zip",
    "Linux": "chromedriver_linux64.zip",
    "Darwin": "chromedriver_mac64.zip",
    "DarwinM1": "chromedriver_mac64_m1.zip"
}

# Latest app version can be found using GET /v1/application-info/android
USER_AGENT = "PixivIOSApp/7.13.3 (iOS 14.6; iPhone13,2)"
REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
AUTH_TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"
CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
REQUESTS_KWARGS = {
    # 'proxies': {
    #     'https': 'http://127.0.0.1:1087',
    # },
    # 'verify': False
}

def install_chromedriver() -> bool:
    current_platform = platform.system()
    
    if (current_platform == "Darwin"):
        current_platform += "M1" if platform.processor() == "arm" else ""
    
    full_url = f"{CHROMEDRIVER_URL}{CHROMEDRIVER_FILES[current_platform]}"

    request = requests.get(full_url)

    if (request.status_code >= 400):
        return False
    
    save_dir = user_data_dir("chromedriver")

    with ZipFile(io.BytesIO(request.content), "r") as zip_file:
        zip_file.extractall(save_dir)

    return True
    
def s256(data) -> bytes:
    """S256 transformation method."""

    return urlsafe_b64encode(sha256(data).digest()).rstrip(b"=").decode("ascii")


def oauth_pkce(transform) -> tuple[str, ...]:
    """Proof Key for Code Exchange by OAuth Public Clients (RFC7636)."""

    code_verifier = token_urlsafe(32)
    code_challenge = transform(code_verifier.encode("ascii"))

    return code_verifier, code_challenge


def print_auth_token_response(response):
    data = response.json()

    try:
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
    except KeyError:
        log("error:")
        log(data)

    log(f"access_token: {access_token}")
    log(f"refresh_token: {refresh_token}")
    log(f"expires_in: {data.get('expires_in', 0)}")
    return refresh_token


def login():
    path = user_data_dir("chromedriver")
    
    if (not os.path.isdir(path)):
        log("> Chromedriver not found. Installing...")
        install_chromedriver()

    caps = DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"performance": "ALL"}  # enable performance logs
    
    options = webdriver.ChromeOptions()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    service = webdriver.ChromeService()
    driver = webdriver.Chrome(options = options, service = service)

    code_verifier, code_challenge = oauth_pkce(s256)
    login_params = {
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "client": "pixiv-android",
    }

    log(f"> Gen code_verifier: {code_verifier}")

    driver.get(f"{LOGIN_URL}?{urlencode(login_params)}")

    while True:
        # wait for login
        if driver.current_url[:40] == "https://accounts.pixiv.net/post-redirect":
            break
        time.sleep(1)

    # filter code url from performance logs
    code = None
    for row in driver.get_log('performance'):
        data = json.loads(row.get("message", {}))
        message = data.get("message", {})
        if message.get("method") == "Network.requestWillBeSent":
            url = message.get("params", {}).get("documentURL")
            if url[:8] == "pixiv://":
                code = re.search(r'code=([^&]*)', url).groups()[0]
                break

    driver.close()

    log(f"> Get code: {code}")

    response = requests.post(
        AUTH_TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "include_policy": "true",
            "redirect_uri": REDIRECT_URI,
        },
        headers={
            "user-agent": USER_AGENT,
            "app-os-version": "14.6",
            "app-os": "ios",
        },
        **REQUESTS_KWARGS
    )

    return print_auth_token_response(response)


def refresh(refresh_token):
    response = requests.post(
        AUTH_TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "include_policy": "true",
            "refresh_token": refresh_token,
        },
        headers={
            "user-agent": USER_AGENT,
            "app-os-version": "14.6",
            "app-os": "ios",
        },
        **REQUESTS_KWARGS
    )

    return print_auth_token_response(response)