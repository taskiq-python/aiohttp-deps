from io import BytesIO

import pydantic
import pytest
from aiohttp import web

from aiohttp_deps import Depends, Form
from tests.conftest import ClientGenerator


class InputSchema(pydantic.BaseModel):
    id: int
    file: web.FileField

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


@pytest.mark.anyio
async def test_form_dependency(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(my_form: InputSchema = Depends(Form())) -> web.Response:
        return web.Response(body=my_form.file.file.read())

    my_app.router.add_post("/", handler)

    file_data = b"bytes"
    client = await aiohttp_client(my_app)
    resp = await client.post(
        "/",
        data={"id": "1", "file": BytesIO(file_data)},
    )
    assert resp.status == 200
    assert await resp.content.read() == file_data


@pytest.mark.anyio
async def test_form_empty(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(_: InputSchema = Depends(Form())) -> None:
        """Nothing."""

    my_app.router.add_post("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.post(
        "/",
    )
    assert resp.status == 400


@pytest.mark.anyio
async def test_form_incorrect_data(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(_: InputSchema = Depends(Form())) -> None:
        """Nothing."""

    my_app.router.add_post("/", handler)

    client = await aiohttp_client(my_app)
    resp = await client.post("/", data={"id": "meme", "file": BytesIO(b"")})
    assert resp.status == 400


@pytest.mark.anyio
async def test_form_untyped(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    async def handler(form=Depends(Form())) -> web.Response:  # noqa: ANN001
        return web.Response(body=form["file"].file.read())

    my_app.router.add_post("/", handler)

    form_data = b"meme"
    client = await aiohttp_client(my_app)
    resp = await client.post("/", data={"id": "meme", "file": BytesIO(form_data)})
    assert resp.status == 200
    assert await resp.content.read() == form_data
