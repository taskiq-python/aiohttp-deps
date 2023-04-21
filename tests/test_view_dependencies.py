import pytest
from aiohttp import web

from aiohttp_deps import Depends, View
from tests.conftest import ClientGenerator


@pytest.mark.anyio
async def test_ordinary_views(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    class MyView(web.View):
        async def get(self):
            return web.json_response({"request": str(self.request)})

    my_app.router.add_view("/", MyView)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert "Request" in (await resp.json())["request"]


@pytest.mark.anyio
async def test_views_with_deps(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    class MyView(View):
        async def get(self, request: web.Request = Depends()):
            return web.json_response({"request": str(request)})

    my_app.router.add_view("/", MyView)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert "Request" in (await resp.json())["request"]


@pytest.mark.anyio
async def test_views_unknown_method(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    class MyView(View):
        async def get(self):
            """Nothing."""

    my_app.router.add_view("/", MyView)

    client = await aiohttp_client(my_app)
    resp = await client.delete("/")
    assert resp.status == 405
