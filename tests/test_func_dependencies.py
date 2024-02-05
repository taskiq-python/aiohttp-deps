import pytest
from aiohttp import web

from aiohttp_deps import Depends
from aiohttp_deps.keys import DEPENDENCY_OVERRIDES_KEY, VALUES_OVERRIDES_KEY
from tests.conftest import ClientGenerator


@pytest.mark.anyio
async def test_request_dependency(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(request: web.Request = Depends()) -> web.Response:
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
) -> None:
    async def handler(app: web.Application = Depends()) -> web.Response:
        return web.json_response({"request": str(app)})

    my_app.router.add_get("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert "Application" in (await resp.json())["request"]


@pytest.mark.anyio
async def test_values_override(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    def original_dep() -> int:
        return 1

    async def handler(num: int = Depends(original_dep)) -> web.Response:
        return web.json_response({"request": num})

    my_app.router.add_get("/", handler)
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

    def custom_dep() -> int:
        return 2

    async def handler(num: int = Depends(original_dep)) -> web.Response:
        return web.json_response({"request": num})

    my_app.router.add_get("/", handler)
    my_app[DEPENDENCY_OVERRIDES_KEY] = {original_dep: custom_dep}

    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert (await resp.json())["request"] == 2


@pytest.mark.anyio
async def test_ordinary_functions_support(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"request": "ordinary"})

    my_app.router.add_get("/", handler)
    client = await aiohttp_client(my_app)
    resp = await client.get("/")
    assert resp.status == 200
    assert await resp.json() == {"request": "ordinary"}
