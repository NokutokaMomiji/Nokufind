from setuptools import find_packages, setup

with open("README.md", "r", encoding = "utf-8") as file:
    long_description = file.read()

with open("LICENSE", "r", encoding = "utf-8") as file:
    license_text = file.read()

setup(
    name = "nokufind",
    packages = find_packages(),
    version = "1.0.2",
    description = "A library that allows you to find posts from multiple Boorus and sources.",
    author = "Nokutoka Momiji (@NokutokaMomiji)",
    install_requires = [
        "enma==2.3.0",
        "markdownify==0.11.6",
        "pixivpy3==3.7.4",
        "Pybooru==4.2.2",
        "pygelbooru==0.5.0",
        "rule34Py==1.4.11",
        "tqdm==4.66.2",
        "appdirs==1.4.4",
        "selenium==4.18.1",
        "httpx==0.27.0",
        "aiometer==0.5.0",
        "timeloop==1.0.2",
        "Requests==2.31.0"
    ],
    setup_requires = ["pytest-runner"],
    tests_require = ["pytest==4.4.1"],
    test_suite = "tests",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/NokutokaMomiji/Nokufind",
    license = license_text
)