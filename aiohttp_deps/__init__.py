"""Project was generated using taskiq."""

from taskiq_dependencies import Depends

from aiohttp_deps.initializer import init
from aiohttp_deps.keys import DEPENDENCY_OVERRIDES_KEY, VALUES_OVERRIDES_KEY
from aiohttp_deps.router import Router
from aiohttp_deps.swagger import extra_openapi, openapi_response, setup_swagger
from aiohttp_deps.utils import ExtraOpenAPI, Form, Header, Json, Path, Query
from aiohttp_deps.view import View

__all__ = [
    "DEPENDENCY_OVERRIDES_KEY",
    "VALUES_OVERRIDES_KEY",
    "Depends",
    "ExtraOpenAPI",
    "Form",
    "Header",
    "Json",
    "Path",
    "Query",
    "Router",
    "View",
    "extra_openapi",
    "init",
    "openapi_response",
    "setup_swagger",
]
