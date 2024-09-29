import asyncio
from typing import AsyncGenerator, Awaitable, Callable, Optional, Union

import pytest
from aiohttp import web
from aiohttp.test_utils import BaseTestServer, TestClient, TestServer

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


@pytest.fixture
async def aiohttp_client() -> (
    AsyncGenerator[Callable[[web.Application], Awaitable[TestClient]], None]
):
    """
    Create a test client.

    This function creates a TestServer
    and a test client for the application.

    :param app: current application.
    :yield: ready to use client.
    """
    client: Optional[TestClient] = None

    async def inner(app: web.Application) -> TestClient:
        nonlocal client
        loop = asyncio.get_running_loop()
        server = TestServer(app)
        client = TestClient(server, loop=loop)
        await client.start_server()
        return client

    yield inner

    if client is not None:
        await client.close()
