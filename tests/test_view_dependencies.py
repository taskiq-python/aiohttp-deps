import pytest
from aiohttp import web

from aiohttp_deps import Depends, View
from aiohttp_deps.keys import DEPENDENCY_OVERRIDES_KEY, VALUES_OVERRIDES_KEY
from tests.conftest import ClientGenerator


@pytest.mark.anyio
async def test_ordinary_views(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    class MyView(web.View):
        async def get(self) -> web.Response:
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
) -> None:
    class MyView(View):
        async def get(self, request: web.Request = Depends()) -> web.Response:
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
) -> None:
    class MyView(View):
        async def get(self) -> web.Response:
            """Nothing."""
            return web.Response()

    my_app.router.add_view("/", MyView)

    client = await aiohttp_client(my_app)
    resp = await client.delete("/")
    assert resp.status == 405


@pytest.mark.anyio
async def test_values_override(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    def original_dep() -> int:
        return 1

    class MyView(View):
        async def get(self, num: int = Depends(original_dep)) -> web.Response:
            """Nothing."""
            return web.json_response({"request": num})

    my_app.router.add_view("/", MyView)
    my_app[VALUES_OVERRIDES_KEY] = {original_dep: 2}

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert (await resp.json())["request"] == 2


@pytest.mark.anyio
async def test_dependency_override(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    def original_dep() -> int:
        return 1

    def replaced() -> int:
        return 2

    class MyView(View):
        async def get(self, num: int = Depends(original_dep)) -> web.Response:
            """Nothing."""
            return web.json_response({"request": num})

    my_app.router.add_view("/", MyView)
    my_app[DEPENDENCY_OVERRIDES_KEY] = {original_dep: replaced}

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert (await resp.json())["request"] == 2
