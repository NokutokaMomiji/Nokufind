from setuptools import find_packages, setup

setup(
    name = "nokufind",
    packages = find_packages(),
    version = "1.0.0",
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
    test_suite = "tests"
)