import os
from setuptools import setup, find_packages

PACKAGE = "apitoolbox"
VERSION = "0.9.1"

URL = "https://github.com/zuarbase/" + PACKAGE
DOWNLOAD_URL= URL + "/archive/v" + VERSION + ".tar.gz"

DESCRIPTION = "Full-stack async framework for Python."

with open("README.md", "r") as filp:
    LONG_DESCRIPTION = filp.read()


setup(
    name=PACKAGE,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Matthew Laue",
    author_email="matt@zuar.com",
    url=URL,
    download_url=DOWNLOAD_URL,
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    install_requires=[
        "email-validator",
        "fastapi >= 0.52.0, < 0.53.0",
        "pydantic >= 1.4, < 1.5",
        "passlib",
        "python-dateutil",
        "python-multipart",
        "pyjwt",
        "sqlalchemy",
        "sqlalchemy-filters",
        "tzlocal",
        "itsdangerous",
    ],
    extras_require={
        "dev": [
            "coverage",
            "pylint",
            "pytest",
            "pytest-cov",
            "pytest-env",
            "pytest-mock",
            "requests",
            "flake8",
            "flake8-quotes",
        ],
        "prod": [
            "uvicorn",
            "gunicorn",
        ]
    }
)
