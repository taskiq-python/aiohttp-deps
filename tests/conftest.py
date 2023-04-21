from typing import Awaitable, Callable, Union

import pytest
from aiohttp import web
from aiohttp.test_utils import BaseTestServer, TestClient

from aiohttp_deps import init

ClientGenerator = Callable[
    [Union[BaseTestServer, web.Application]],
    Awaitable[TestClient],
]


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """
    Anyio backend.

    Backend for anyio pytest plugin.
    :return: backend name.
    """
    return "asyncio"


@pytest.fixture
def my_app() -> web.Application:
    app = web.Application()
    app.on_startup.append(init)
    return app
