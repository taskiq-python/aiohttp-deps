"""Project was generated using taskiq."""
from taskiq_dependencies import Depends

from aiohttp_deps.initializer import init
from aiohttp_deps.router import Router
from aiohttp_deps.swagger import extra_openapi, setup_swagger
from aiohttp_deps.utils import Form, Header, Json, Path, Query
from aiohttp_deps.view import View

__all__ = [
    "init",
    "setup_swagger",
    "extra_openapi",
    "Header",
    "Depends",
    "Router",
    "View",
    "Json",
    "Query",
    "Form",
    "Path",
]
