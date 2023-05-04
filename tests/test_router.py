import pytest
from aiohttp import web

from aiohttp_deps import Router
from tests.conftest import ClientGenerator


@pytest.mark.anyio
async def test_router_add_routes(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    api_router = Router()

    @api_router.get("/a")
    async def _():
        return web.json_response({"a": "b"})

    @api_router.get("/b")
    async def _():
        return web.json_response({"b": "c"})

    router = Router()
    router.add_routes(api_router)

    my_app.router.add_routes(router)

    client = await aiohttp_client(my_app)
    response = await client.get("/a")
    assert response.status == 200
    assert await response.json() == {"a": "b"}

    response = await client.get("/b")
    assert response.status == 200
    assert await response.json() == {"b": "c"}


@pytest.mark.anyio
async def test_prefixed_routes(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    api_router = Router()

    @api_router.get("/a")
    async def _():
        return web.json_response({"a": "b"})

    router = Router()
    router.add_routes(api_router, prefix="/api")

    my_app.router.add_routes(router)

    client = await aiohttp_client(my_app)
    response = await client.get("/api/a")
    assert response.status == 200
    assert await response.json() == {"a": "b"}


@pytest.mark.anyio
async def test_deep_nesting(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    last_router = Router()

    @last_router.get("/a")
    async def _():
        return web.json_response({"a": "b"})

    # Generate 20 nested routers.
    for i in range(20):
        new_router = Router()
        new_router.add_routes(last_router, prefix=f"/{i}")
        last_router = new_router

    router = Router()
    router.add_routes(last_router, prefix="/api")

    my_app.router.add_routes(router)

    client = await aiohttp_client(my_app)
    url = "/api/" + "/".join([str(i) for i in range(20)][::-1]) + "/a"

    response = await client.get(url)
    assert response.status == 200
    assert await response.json() == {"a": "b"}


@pytest.mark.anyio
async def test_prefixed_routes_no_start_slash():
    api_router = Router()

    @api_router.get("/a")
    async def _():
        """Nothing."""

    router = Router()
    with pytest.raises(ValueError):
        router.add_routes(api_router, prefix="api")


@pytest.mark.anyio
async def test_prefixed_routes_trailing_slash():
    api_router = Router()

    @api_router.get("/a")
    async def _():
        """Nothing."""

    router = Router()
    with pytest.raises(ValueError):
        router.add_routes(api_router, prefix="/api/")
