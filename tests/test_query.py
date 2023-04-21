from typing import Optional

import pytest
from aiohttp import web
from multidict import CIMultiDict

from aiohttp_deps import Depends, Query
from tests.conftest import ClientGenerator


@pytest.mark.anyio
async def test_query_dependency(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_query: str = Depends(Query())):
        return web.json_response({"query": my_query})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/", params={"my_query": "123"})
    assert resp.status == 200
    assert (await resp.json())["query"] == "123"


@pytest.mark.anyio
async def test_empty_querys(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_query: str = Depends(Query())):
        """Nothing."""

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 400


@pytest.mark.anyio
async def test_nullable_querys(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_query: Optional[str] = Depends(Query())):
        return web.json_response({"query": my_query})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert (await resp.json())["query"] is None

    resp = await client.get("/", params={"my_query": "meme"})
    assert resp.status == 200
    assert (await resp.json())["query"] == "meme"


@pytest.mark.anyio
async def test_parse_types(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_query: int = Depends(Query())):
        return web.json_response({"query": my_query})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)

    resp = await client.get("/", params={"my_query": "42"})
    assert resp.status == 200
    assert (await resp.json())["query"] == 42


@pytest.mark.anyio
async def test_default_value(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_query: int = Depends(Query(42))):
        return web.json_response({"query": my_query})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)

    resp = await client.get("/")
    assert resp.status == 200
    assert (await resp.json())["query"] == 42


@pytest.mark.anyio
async def test_multiple(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_query: list[int] = Depends(Query(multiple=True))):
        return web.json_response({"query": my_query})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)

    querys = CIMultiDict()
    querys.extend({"my_query": "123"})
    querys.extend({"my_query": "321"})

    print(querys.getall("my_query"))

    resp = await client.get("/", params=querys)
    assert resp.status == 200
    assert (await resp.json())["query"] == [123, 321]


@pytest.mark.anyio
async def test_untyped(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_query=Depends(Query())):
        return web.json_response({"query": my_query})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)

    resp = await client.get("/", params={"my_query": "123"})
    assert resp.status == 200
    assert (await resp.json())["query"] == "123"
