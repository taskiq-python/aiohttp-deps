import pytest
from aiohttp import web

from aiohttp_deps import Depends
from tests.conftest import ClientGenerator


@pytest.mark.anyio
async def test_request_dependency(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(request: web.Request = Depends()):
        return web.json_response({"request": str(request)})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert "Request" in (await resp.json())["request"]


@pytest.mark.anyio
async def test_app_dependency(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    async def handler(app: web.Application = Depends()):
        return web.json_response({"request": str(app)})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert "Application" in (await resp.json())["request"]
