from typing import List, Optional

import pytest
from aiohttp import web
from multidict import CIMultiDict

from aiohttp_deps import Depends, Header
from tests.conftest import ClientGenerator


@pytest.mark.anyio
async def test_header_dependency(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(my_header: str = Depends(Header())) -> web.Response:
        return web.json_response({"header": my_header})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/", headers={"my_header": "123"})
    assert resp.status == 200
    assert (await resp.json())["header"] == "123"


@pytest.mark.anyio
async def test_empty_headers(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(my_header: str = Depends(Header())) -> None:
        """Nothing."""

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 400


@pytest.mark.anyio
async def test_nullable_headers(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(my_header: Optional[str] = Depends(Header())) -> web.Response:
        return web.json_response({"header": my_header})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert (await resp.json())["header"] is None

    resp = await client.get("/", headers={"my_header": "meme"})
    assert resp.status == 200
    assert (await resp.json())["header"] == "meme"


@pytest.mark.anyio
async def test_parse_types(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(my_header: int = Depends(Header())) -> web.Response:
        return web.json_response({"header": my_header})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)

    resp = await client.get("/", headers={"my_header": "42"})
    assert resp.status == 200
    assert (await resp.json())["header"] == 42


@pytest.mark.anyio
async def test_default_value(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(my_header: int = Depends(Header(42))) -> web.Response:
        return web.json_response({"header": my_header})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)

    resp = await client.get("/")
    assert resp.status == 200
    assert (await resp.json())["header"] == 42


@pytest.mark.anyio
async def test_multiple(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(
        my_header: List[int] = Depends(Header(multiple=True)),
    ) -> web.Response:
        return web.json_response({"header": my_header})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)

    headers = CIMultiDict()
    headers.extend({"my_header": "123"})
    headers.extend({"my_header": "321"})

    resp = await client.get("/", headers=headers)
    assert resp.status == 200
    assert (await resp.json())["header"] == [123, 321]


@pytest.mark.anyio
async def test_untyped(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(my_header=Depends(Header())) -> web.Response:  # noqa: ANN001
        return web.json_response({"header": my_header})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)

    resp = await client.get("/", headers={"my_header": "123"})
    assert resp.status == 200
    assert (await resp.json())["header"] == "123"
