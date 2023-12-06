import pytest
from aiohttp import web

from aiohttp_deps import Depends, Path
from tests.conftest import ClientGenerator


@pytest.mark.anyio
async def test_path_dependency(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(var: str = Depends(Path())) -> web.Response:
        return web.json_response({"path": var})

    my_app.router.add_get("/{var}", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/hehe")
    assert resp.status == 200
    assert (await resp.json())["path"] == "hehe"


@pytest.mark.anyio
async def test_path_wrong_type(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(var: int = Depends(Path())) -> web.Response:
        return web.json_response({"path": var})

    my_app.router.add_get("/{var}", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/hehe")
    assert resp.status == 400


@pytest.mark.anyio
async def test_path_untyped(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(var=Depends(Path())) -> web.Response:  # noqa: ANN001
        return web.json_response({"path": var})

    my_app.router.add_get("/{var}", handler)

    client = await aiohttp_client(my_app)
    resp = await client.get("/hehe")
    assert resp.status == 200
    assert (await resp.json())["path"] == "hehe"
