from typing import Optional

import pytest
from aiohttp import web
from pydantic import BaseModel

from aiohttp_deps import Depends, Json
from tests.conftest import ClientGenerator


class InputSchema(BaseModel):
    name: str


@pytest.mark.anyio
async def test_json_dependency(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_body: InputSchema = Depends(Json())):
        return web.json_response({"body": my_body.model_dump()})

    my_app.router.add_get("/", handler)

    test_obj = InputSchema(name="meme")

    client = await aiohttp_client(my_app)
    resp = await client.get("/", json=test_obj.model_dump())
    assert resp.status == 200
    assert (await resp.json())["body"] == test_obj.model_dump()


@pytest.mark.anyio
async def test_json_untyped(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_body=Depends(Json())):
        return web.json_response({"body": my_body})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/", json={"secret": "string"})
    assert resp.status == 200
    assert (await resp.json())["body"] == {"secret": "string"}


@pytest.mark.anyio
async def test_empty_body(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_body: InputSchema = Depends(Json())):
        """Nothing."""

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 400


@pytest.mark.anyio
async def test_optional_body(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(my_body: Optional[InputSchema] = Depends(Json())):
        return web.json_response({"body": my_body.model_dump() if my_body else None})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert (await resp.json())["body"] is None

    data = InputSchema(name="memelover")

    resp = await client.get("/", json=data.model_dump())
    assert resp.status == 200
    assert (await resp.json())["body"] == data.model_dump()
