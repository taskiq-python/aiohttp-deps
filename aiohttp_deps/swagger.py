import inspect
from collections import defaultdict
from logging import getLogger
from typing import Any, Awaitable, Callable, Dict, Optional, Union

from aiohttp import web
from pydantic import schema_of
from pydantic.utils import deep_update
from taskiq_dependencies import DependencyGraph

from aiohttp_deps.initializer import InjectableFuncHandler, InjectableViewHandler
from aiohttp_deps.utils import Form, Header, Json, Path, Query

REF_TEMPLATE = "#/components/schemas/{model}"
SCHEMA_KEY = "openapi_schema"
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
METHODS_WITH_BODY = {"POST", "PUT", "PATCH"}  # noqa: WPS407

logger = getLogger()


async def _schema_handler(
    request: web.Request,
) -> web.Response:
    return web.json_response(request.app[SCHEMA_KEY])


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

    origin = getattr(annotation.annotation, "__origin__", None)
    if origin is None:
        return False

    if origin == Union:
        args = getattr(annotation.annotation, "__args__", ())
        for arg in args:
            if arg is type(None):  # noqa: E721, WPS516
                return True
    return False


def _add_route_def(  # noqa: C901
    openapi_schema: Dict[str, Any],
    route: web.ResourceRoute,
    method: str,
    graph: DependencyGraph,
    extra_openapi: Dict[str, Any],
) -> None:
    route_info: Dict[str, Any] = {
        "description": inspect.getdoc(graph.target),
        "responses": {},
        "parameters": [],
    }
    if route.resource is None:  # pragma: no cover
        return

    for dependency in graph.ordered_deps:
        if isinstance(dependency.dependency, (Json, Form)):
            content_type = "application/json"
            if isinstance(dependency.dependency, Form):
                content_type = "application/x-www-form-urlencoded"
            if (
                dependency.signature
                and dependency.signature.annotation != inspect.Parameter.empty
            ):
                input_schema = schema_of(
                    dependency.signature.annotation,
                    ref_template=REF_TEMPLATE,
                )
                openapi_schema["components"]["schemas"].update(
                    input_schema.pop("definitions", {}),
                )
                route_info["requestBody"] = {
                    "content": {content_type: {"schema": input_schema}},
                }
            else:
                route_info["requestBody"] = {
                    "content": {content_type: {}},
                }
        elif isinstance(dependency.dependency, Query):
            route_info["parameters"].append(
                {
                    "name": dependency.dependency.alias or dependency.param_name,
                    "in": "query",
                    "description": dependency.dependency.description,
                    "required": not _is_optional(dependency.signature),
                },
            )
        elif isinstance(dependency.dependency, Header):
            route_info["parameters"].append(
                {
                    "name": dependency.dependency.alias or dependency.param_name,
                    "in": "header",
                    "description": dependency.dependency.description,
                    "required": not _is_optional(dependency.signature),
                },
            )
        elif isinstance(dependency.dependency, Path):
            route_info["parameters"].append(
                {
                    "name": dependency.dependency.alias or dependency.param_name,
                    "in": "path",
                    "description": dependency.dependency.description,
                    "required": not _is_optional(dependency.signature),
                    "allowEmptyValue": _is_optional(dependency.signature),
                },
            )

    openapi_schema["paths"][route.resource.canonical].update(
        {method.lower(): deep_update(route_info, extra_openapi)},
    )


def setup_swagger(  # noqa: C901, WPS211
    schema_url: str = "/openapi.json",
    swagger_ui_url: str = "/docs",
    enable_ui: bool = True,
    hide_heads: bool = True,
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
    :param title: Title of an application.
    :param description: description of an application.
    :param version: version of an application.
    :return: startup event handler.
    """

    async def event_handler(app: web.Application) -> None:
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
            if hide_heads and route.method == "HEAD":
                continue
            if isinstance(route._handler, InjectableFuncHandler):
                extra_openapi = getattr(
                    route._handler.original_handler,
                    "__extra_openapi__",
                    {},
                )
                try:
                    _add_route_def(
                        openapi_schema,
                        route,  # type: ignore
                        route.method,
                        route._handler.graph,
                        extra_openapi=extra_openapi,
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
                        getattr(
                            route._handler.original_handler,
                            key,
                        ),
                        "__extra_openapi__",
                        {},
                    )
                    try:
                        _add_route_def(
                            openapi_schema,
                            route,  # type: ignore
                            key,
                            graph,
                            extra_openapi=extra_openapi,
                        )
                    except Exception as exc:  # pragma: no cover
                        logger.warn(
                            "Cannot add route info: %s",
                            exc,
                            exc_info=True,
                        )

        app[SCHEMA_KEY] = openapi_schema

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


def extra_openapi(additional_schema: Dict[str, Any]) -> Callable[..., Any]:
    """
    Add extra openapi schema.

    This function just adds a parameter for later use
    by openapi schema generator.

    :param additional_schema: dict with updates.
    :return: same function with new attributes.
    """

    def decorator(func: Any) -> Any:
        func.__extra_openapi__ = additional_schema

        return func

    return decorator
