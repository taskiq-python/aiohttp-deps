from collections import deque
from typing import Any, Dict, Generic, Optional, TypeVar

import pytest
from aiohttp import web
from pydantic import BaseModel

from aiohttp_deps import (
    Depends,
    Form,
    Header,
    Json,
    Path,
    Query,
    View,
    extra_openapi,
    setup_swagger,
)
from aiohttp_deps.swagger import openapi_response
from tests.conftest import ClientGenerator


def follow_ref(ref: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Function for following openapi references."""
    components = deque(ref.split("/"))
    current_model = None
    while components:
        component = components.popleft()
        if component.strip() == "#":
            current_model = data
            continue
        current_model = current_model.get(component)
        if current_model is None:
            return {}
    return current_model


def get_schema_by_ref(full_schema: Dict[str, Any], ref: str):
    ref_path = deque(ref.split("/"))
    current_schema = full_schema
    while ref_path:
        component = ref_path.popleft()
        if component == "#":
            current_schema = full_schema
            continue
        current_schema = current_schema[component]
    return current_schema


@pytest.mark.anyio
async def test_swagger_ui(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    UI_URL = "/swagger"
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(
        setup_swagger(
            schema_url=OPENAPI_URL,
            swagger_ui_url=UI_URL,
            enable_ui=True,
        ),
    )
    client = await aiohttp_client(my_app)
    resp = await client.get(UI_URL)
    assert resp.status == 200
    assert OPENAPI_URL in await resp.text()


@pytest.mark.anyio
async def test_schema_url(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(
        setup_swagger(
            schema_url=OPENAPI_URL,
            title="My app",
            description="My super app",
        ),
    )
    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    assert resp_json["info"]["title"] == "My app"
    assert resp_json["info"]["description"] == "My super app"


@pytest.mark.anyio
async def test_no_dependencies(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    async def my_handler():
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    handler_info = resp_json["paths"]["/a"]["get"]
    assert handler_info["description"] == my_handler.__doc__


@pytest.mark.anyio
async def test_json_success(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    class Meme(BaseModel):
        a: str
        b: str

    async def my_handler(body: Meme = Depends(Json())):
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    handler_info = resp_json["paths"]["/a"]["get"]
    schema = handler_info["requestBody"]["content"]["application/json"]["schema"]
    assert schema["title"] == "Meme"
    assert "a" in schema["properties"]
    assert "b" in schema["properties"]
    assert {"a", "b"} == set(schema["required"])


@pytest.mark.anyio
async def test_json_untyped(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    async def my_handler(body=Depends(Json())):
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    handler_info = resp_json["paths"]["/a"]["get"]
    assert handler_info["requestBody"]["content"]["application/json"] == {}


@pytest.mark.anyio
async def test_json_generic(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    T = TypeVar("T")

    class First(BaseModel):
        name: str

    class Second(BaseModel, Generic[T]):
        data: T

    async def my_handler(body: Second[First] = Depends(Json())):
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    handler_info = resp_json["paths"]["/a"]["get"]
    schema = handler_info["requestBody"]["content"]["application/json"]["schema"]
    first_ref = schema["properties"]["data"]["$ref"]
    first_obj = follow_ref(first_ref, resp_json)
    assert "name" in first_obj["properties"]


@pytest.mark.anyio
async def test_query(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    async def my_handler(my_var: int = Depends(Query(description="desc"))):
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    handler_info = resp_json["paths"]["/a"]["get"]
    param_info = handler_info["parameters"][0]
    assert param_info == {
        "name": "my_var",
        "required": True,
        "in": "query",
        "description": "desc",
    }


@pytest.mark.anyio
async def test_query_optional(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    async def my_handler(my_var: Optional[int] = Depends(Query())):
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    handler_info = resp_json["paths"]["/a"]["get"]
    param_info = handler_info["parameters"][0]
    assert param_info == {
        "name": "my_var",
        "required": False,
        "in": "query",
        "description": "",
    }


@pytest.mark.anyio
async def test_query_aliased(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    async def my_handler(my_var: int = Depends(Query(alias="qqq"))):
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    handler_info = resp_json["paths"]["/a"]["get"]
    param_info = handler_info["parameters"][0]
    assert param_info == {
        "name": "qqq",
        "required": True,
        "in": "query",
        "description": "",
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ["dependecy", "param_info"],
    (
        (
            Query(),
            {"name": "my_var", "required": True, "in": "query", "description": ""},
        ),
        (
            Query(description="my query"),
            {
                "name": "my_var",
                "required": True,
                "in": "query",
                "description": "my query",
            },
        ),
        (
            Query(alias="a"),
            {"name": "a", "required": True, "in": "query", "description": ""},
        ),
        (
            Header(),
            {"name": "My_var", "required": True, "in": "header", "description": ""},
        ),
        (
            Header(description="my header"),
            {
                "name": "My_var",
                "required": True,
                "in": "header",
                "description": "my header",
            },
        ),
        (
            Header(alias="a"),
            {"name": "A", "required": True, "in": "header", "description": ""},
        ),
        (
            Path(),
            {
                "name": "my_var",
                "required": True,
                "in": "path",
                "description": "",
                "allowEmptyValue": False,
            },
        ),
        (
            Path(description="my path"),
            {
                "name": "my_var",
                "required": True,
                "in": "path",
                "description": "my path",
                "allowEmptyValue": False,
            },
        ),
        (
            Path(alias="a"),
            {
                "name": "a",
                "required": True,
                "in": "path",
                "description": "",
                "allowEmptyValue": False,
            },
        ),
    ),
)
async def test_parameters(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
    dependecy: Any,
    param_info: Dict[str, Any],
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    async def my_handler(my_var: int = Depends(dependecy)):
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    handler_info = resp_json["paths"]["/a"]["get"]
    assert handler_info["parameters"][0] == param_info


@pytest.mark.anyio
async def test_view_success(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    class MyView(View):
        async def get():
            """Get handler."""

        async def post():
            """Post handler."""

    my_app.router.add_view("/a", MyView)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    assert {"get", "post"} == set(resp_json["paths"]["/a"].keys())


@pytest.mark.anyio
async def test_form_success(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    class MyForm(BaseModel):
        a: str
        b: str

    async def my_handler(my_var: MyForm = Depends(Form())):
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    handler_info = resp_json["paths"]["/a"]["get"]
    schema = handler_info["requestBody"]["content"][
        "application/x-www-form-urlencoded"
    ]["schema"]
    assert schema["title"] == "MyForm"
    assert "a" in schema["properties"]
    assert "b" in schema["properties"]
    assert {"a", "b"} == set(schema["required"])


@pytest.mark.anyio
async def test_form_untyped(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    async def my_handler(my_var=Depends(Form())):
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    handler_info = resp_json["paths"]["/a"]["get"]
    assert (
        {}
        == handler_info["requestBody"]["content"]["application/x-www-form-urlencoded"]
    )


@pytest.mark.anyio
async def test_extra_openapi_func(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    @extra_openapi({"responses": {"200": {}}})
    async def my_handler():
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()

    handler_info = resp_json["paths"]["/a"]["get"]
    assert handler_info["responses"] == {"200": {}}


@pytest.mark.anyio
async def test_extra_openapi_views(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
):
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    class MyView(View):
        @extra_openapi({"get_info": "wow"})
        async def get():
            """get handler."""

        @extra_openapi({"post_info": "wow"})
        async def post():
            """post handler."""

    my_app.router.add_view("/a", MyView)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()

    handler_info = resp_json["paths"]["/a"]["get"]
    assert handler_info["get_info"] == "wow"

    handler_info = resp_json["paths"]["/a"]["post"]
    assert handler_info["post_info"] == "wow"


@pytest.mark.anyio
async def test_merge_headers(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    async def my_handler(
        my_var: Optional[str] = Depends(Header(alias="head")),
        my_var2: Optional[str] = Depends(Header(alias="head")),
        my_var3: str = Depends(Header(alias="head")),
    ):
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    assert resp.status == 200
    resp_json = await resp.json()
    params = resp_json["paths"]["/a"]["get"]["parameters"]
    assert len(params) == 1
    assert params[0]["name"] == "Head"
    assert params[0]["required"]
    assert not params[0]["allowEmptyValue"]


@pytest.mark.anyio
async def test_custom_responses(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    class RespModel(BaseModel):
        name: str
        age: int

    class UnauthModel(BaseModel):
        why: str

    @openapi_response(200, RespModel)
    @openapi_response(401, UnauthModel)
    async def my_handler():
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    resp_json = await resp.json()
    route_info = resp_json["paths"]["/a"]["get"]
    assert "401" in route_info["responses"]
    assert "200" in route_info["responses"]
    assert "schema" in route_info["responses"]["200"]["content"]["application/json"]
    assert "schema" in route_info["responses"]["401"]["content"]["application/json"]


@pytest.mark.anyio
async def test_custom_responses_multi_content_type(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    class First(BaseModel):
        name: str

    class Second(BaseModel):
        age: int

    @openapi_response(200, First, content_type="application/json")
    @openapi_response(200, Second, content_type="application/xml")
    async def my_handler():
        """Nothing."""

    my_app.router.add_get("/a", my_handler)

    client = await aiohttp_client(my_app)
    resp = await client.get(OPENAPI_URL)
    resp_json = await resp.json()
    route_info = resp_json["paths"]["/a"]["get"]
    assert "200" in route_info["responses"]
    assert "application/json" in route_info["responses"]["200"]["content"]
    assert "application/xml" in route_info["responses"]["200"]["content"]


@pytest.mark.anyio
async def test_custom_responses_generics(
    my_app: web.Application,
    aiohttp_client: ClientGenerator,
) -> None:
    OPENAPI_URL = "/my_api_def.json"
    my_app.on_startup.append(setup_swagger(schema_url=OPENAPI_URL))

    T = TypeVar("T")

    class First(BaseModel):
        name: str

    class Second(BaseModel, Generic[T]):
        data: T

    @openapi_response(200, Second[First])
    async def my_handler():
        """Nothing."""

    my_app.router.add_get("/a", my_handler)
    client = await aiohttp_client(my_app)
    response = await client.get(OPENAPI_URL)
    resp_json = await response.json()
    first_ref = resp_json["paths"]["/a"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["properties"]["data"]["$ref"]
    first_obj = follow_ref(first_ref, resp_json)
    assert "name" in first_obj["properties"]
