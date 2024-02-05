import inspect
from collections import defaultdict
from logging import getLogger
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Optional,
    Tuple,
    TypeVar,
    get_type_hints,
)

import pydantic
from aiohttp import web
from deepmerge import always_merger
from taskiq_dependencies import DependencyGraph

from aiohttp_deps.initializer import InjectableFuncHandler, InjectableViewHandler
from aiohttp_deps.keys import SWAGGER_SCHEMA_KEY
from aiohttp_deps.utils import Form, Header, Json, Path, Query

_T = TypeVar("_T")

REF_TEMPLATE = "#/components/schemas/{model}"
SWAGGER_HTML_TEMPALTE = """
<html lang="en">

<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="SwaggerUI" />
    <title>SwaggerUI</title>
    <link rel="stylesheet"
        href="https://unpkg.com/swagger-ui-dist/swagger-ui.css"
    />
</head>

<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"
    crossorigin></script>
    <script>
        window.onload = () => {
            window.ui = SwaggerUIBundle({
                url: '{schema_url}',
                dom_id: '#swagger-ui',
            });
        };
    </script>
</body>
</html>
"""
METHODS_WITH_BODY = {"POST", "PUT", "PATCH"}

logger = getLogger()


async def _schema_handler(
    request: web.Request,
) -> web.Response:
    return web.json_response(request.app[SWAGGER_SCHEMA_KEY])


def _get_swagger_handler(
    swagger_html: str,
) -> Callable[[web.Request], Awaitable[web.Response]]:
    async def swagger_handler(_: web.Request) -> web.Response:
        return web.Response(text=swagger_html, content_type="text/html")

    return swagger_handler


def _is_optional(annotation: Optional[inspect.Parameter]) -> bool:
    # If it's an empty annotation,
    # we guess that the value can be optional.
    if annotation is None or annotation.annotation == annotation.empty:
        return True

    def dummy(_var: annotation.annotation) -> None:  # type: ignore
        """Dummy function to use for type resolution."""

    var = get_type_hints(dummy).get("_var")
    return var == Optional[var]


def _get_param_schema(annotation: Optional[inspect.Parameter]) -> Dict[str, Any]:
    if annotation is None or annotation.annotation == annotation.empty:
        return {}

    def dummy(_var: annotation.annotation) -> None:  # type: ignore
        """Dummy function to use for type resolution."""

    var = get_type_hints(dummy).get("_var")
    return pydantic.TypeAdapter(var).json_schema(
        ref_template=REF_TEMPLATE,
        mode="validation",
    )


def _add_route_def(  # noqa: C901
    openapi_schema: Dict[str, Any],
    route: web.ResourceRoute,
    method: str,
    graph: DependencyGraph,
    extra_openapi: Dict[str, Any],
    extra_openapi_schemas: Dict[str, Any],
) -> None:
    route_info: Dict[str, Any] = {
        "description": inspect.getdoc(graph.target),
        "responses": {},
        "parameters": [],
    }
    if route.resource is None:  # pragma: no cover
        return

    if extra_openapi_schemas:
        openapi_schema["components"]["schemas"].update(extra_openapi_schemas)

    params: Dict[Tuple[str, str], Any] = {}

    def _insert_in_params(data: Dict[str, Any]) -> None:
        element = params.get((data["name"], data["in"]))
        if element is None:
            params[(data["name"], data["in"])] = data
            return
        element["required"] = element.get("required") or data.get("required")
        element["allowEmptyValue"] = bool(element.get("allowEmptyValue")) and bool(
            data.get("allowEmptyValue"),
        )
        params[(data["name"], data["in"])] = element

    for dependency in graph.ordered_deps:
        if isinstance(dependency.dependency, (Json, Form)):
            content_type = "application/json"
            if isinstance(dependency.dependency, Form):
                content_type = "application/x-www-form-urlencoded"
            if (
                dependency.signature
                and dependency.signature.annotation != inspect.Parameter.empty
            ):
                input_schema = pydantic.TypeAdapter(
                    dependency.signature.annotation,
                ).json_schema(ref_template=REF_TEMPLATE, mode="validation")
                openapi_schema["components"]["schemas"].update(
                    input_schema.pop("$defs", {}),
                )
                route_info["requestBody"] = {
                    "content": {content_type: {"schema": input_schema}},
                }
            else:
                route_info["requestBody"] = {
                    "content": {content_type: {}},
                }
        elif isinstance(dependency.dependency, Query):
            schema = _get_param_schema(dependency.signature)
            openapi_schema["components"]["schemas"].update(schema.pop("$defs", {}))
            _insert_in_params(
                {
                    "name": dependency.dependency.alias or dependency.param_name,
                    "in": "query",
                    "description": dependency.dependency.description,
                    "required": not _is_optional(dependency.signature),
                    "schema": schema,
                },
            )
        elif isinstance(dependency.dependency, Header):
            name = dependency.dependency.alias or dependency.param_name
            schema = _get_param_schema(dependency.signature)
            openapi_schema["components"]["schemas"].update(schema.pop("$defs", {}))
            _insert_in_params(
                {
                    "name": name.capitalize(),
                    "in": "header",
                    "description": dependency.dependency.description,
                    "required": not _is_optional(dependency.signature),
                    "schema": schema,
                },
            )
        elif isinstance(dependency.dependency, Path):
            schema = _get_param_schema(dependency.signature)
            openapi_schema["components"]["schemas"].update(schema.pop("$defs", {}))
            _insert_in_params(
                {
                    "name": dependency.dependency.alias or dependency.param_name,
                    "in": "path",
                    "description": dependency.dependency.description,
                    "required": not _is_optional(dependency.signature),
                    "allowEmptyValue": _is_optional(dependency.signature),
                    "schema": schema,
                },
            )

    route_info["parameters"] = list(params.values())
    openapi_schema["paths"][route.resource.canonical].update(
        {method.lower(): always_merger.merge(route_info, extra_openapi)},
    )


def setup_swagger(  # noqa: C901
    schema_url: str = "/openapi.json",
    swagger_ui_url: str = "/docs",
    enable_ui: bool = True,
    hide_heads: bool = True,
    hide_options: bool = True,
    title: str = "AioHTTP",
    description: Optional[str] = None,
    version: str = "1.0.0",
) -> Callable[[web.Application], Awaitable[None]]:
    """
    Add swagger documentation.

    This function creates new function,
    that can be used in on_startup.

    Add outputs of this function in on_startup array
    to enable swagger.

    >>> app.on_startup.append(setup_swagger())

    This function will generate swagger schema based
    on dependencies that were used.

    :param schema_url: URL where schema will be served.
    :param swagger_ui_url: URL where swagger ui will be served.
    :param enable_ui: whether you want to enable bundled swagger ui.
    :param hide_heads: hide HEAD requests.
    :param hide_options: hide OPTIONS requests.
    :param title: Title of an application.
    :param description: description of an application.
    :param version: version of an application.
    :return: startup event handler.
    """

    async def event_handler(app: web.Application) -> None:  # noqa: C901
        openapi_schema = {
            "openapi": "3.0.0",
            "info": {
                "title": title,
                "description": description,
                "version": version,
            },
            "components": {"schemas": {}},
            "paths": defaultdict(dict),
        }
        for route in app.router.routes():
            if route.resource is None:  # pragma: no cover
                continue
            if hide_heads and route.method.upper() == "HEAD":
                continue
            if hide_options and route.method.upper() == "OPTIONS":
                continue
            if isinstance(route._handler, InjectableFuncHandler):
                extra_openapi = getattr(
                    route._handler.original_handler,
                    "__extra_openapi__",
                    {},
                )
                extra_schemas = getattr(
                    route._handler.original_handler,
                    "__extra_openapi_schemas__",
                    {},
                )
                try:
                    _add_route_def(
                        openapi_schema,
                        route,  # type: ignore
                        route.method,
                        route._handler.graph,
                        extra_openapi=extra_openapi,
                        extra_openapi_schemas=extra_schemas,
                    )
                except Exception as exc:  # pragma: no cover
                    logger.warn(
                        "Cannot add route info: %s",
                        exc,
                        exc_info=True,
                    )

            elif isinstance(route._handler, InjectableViewHandler):
                for key, graph in route._handler.graph_map.items():
                    extra_openapi = getattr(
                        getattr(route._handler.original_handler, key),
                        "__extra_openapi__",
                        {},
                    )
                    extra_schemas = getattr(
                        getattr(route._handler.original_handler, key),
                        "__extra_openapi_schemas__",
                        {},
                    )
                    try:
                        _add_route_def(
                            openapi_schema,
                            route,  # type: ignore
                            key,
                            graph,
                            extra_openapi=extra_openapi,
                            extra_openapi_schemas=extra_schemas,
                        )
                    except Exception as exc:  # pragma: no cover
                        logger.warn(
                            "Cannot add route info: %s",
                            exc,
                            exc_info=True,
                        )

        app[SWAGGER_SCHEMA_KEY] = openapi_schema

        app.router.add_get(
            schema_url,
            _schema_handler,
        )

        if enable_ui:
            app.router.add_get(
                swagger_ui_url,
                _get_swagger_handler(
                    SWAGGER_HTML_TEMPALTE.replace("{schema_url}", schema_url),
                ),
            )

    return event_handler


def extra_openapi(additional_schema: Dict[str, Any]) -> Callable[[_T], _T]:
    """
    Add extra openapi schema.

    This function just adds a parameter for later use
    by openapi schema generator.

    :param additional_schema: dict with updates.
    :return: same function with new attributes.
    """

    def decorator(func: _T) -> _T:
        func.__extra_openapi__ = additional_schema  # type: ignore
        return func

    return decorator


def openapi_response(
    status: int,
    model: Any,
    *,
    content_type: str = "application/json",
    description: Optional[str] = None,
) -> Callable[[_T], _T]:
    """
    Add response schema to the endpoint.

    This function takes a status and model,
    which is going to represent the response.

    :param status: Status of a response.
    :param model: Response model.
    :param content_type: Content-type of a response.
    :param description: Response's description.

    :returns: decorator that modifies your function.
    """

    def decorator(func: _T) -> _T:
        openapi = getattr(func, "__extra_openapi__", {})
        openapi_schemas = getattr(func, "__extra_openapi_schemas__", {})
        adapter: "pydantic.TypeAdapter[Any]" = pydantic.TypeAdapter(model)
        responses = openapi.get("responses", {})
        status_response = responses.get(status, {})
        if not status_response:
            status_response["description"] = description
        status_response["content"] = status_response.get("content", {})
        response_schema = adapter.json_schema(
            ref_template=REF_TEMPLATE,
            mode="serialization",
        )
        openapi_schemas.update(response_schema.pop("$defs", {}))
        status_response["content"][content_type] = {"schema": response_schema}
        responses[status] = status_response
        openapi["responses"] = responses
        func.__extra_openapi__ = openapi  # type: ignore
        func.__extra_openapi_schemas__ = openapi_schemas  # type: ignore
        return func

    return decorator
