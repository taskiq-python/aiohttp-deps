import inspect
from collections import defaultdict
from logging import getLogger
from typing import Any, Awaitable, Callable, Dict, Optional, Union

from aiohttp import web
from pydantic import schema_of
from taskiq_dependencies import DependencyGraph

from aiohttp_deps.initializer import InjectableFuncHandler, InjectableViewHandler
from aiohttp_deps.utils import Header, Json, Path, Query

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
        href="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui.css"
    />
</head>

<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-bundle.js"
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


async def schema_handler(
    request: web.Request,
) -> web.Response:
    return web.json_response(request.app[SCHEMA_KEY])


def get_swagger_handler(
    swagger_html: str,
) -> Callable[[web.Request], Awaitable[web.Response]]:
    async def swagger_handler(_: web.Request) -> web.Response:
        return web.Response(text=swagger_html, content_type="text/html")

    return swagger_handler


def is_optional(annotation: Optional[inspect.Parameter]) -> bool:
    # If it's an empty annotation,
    # we guess that the value can be optional.
    if annotation is None or annotation == annotation.empty:
        return True

    origin = getattr(annotation.annotation, "__origin__", None)
    if origin is None:
        return False

    if origin == Union:
        args = getattr(annotation.annotation, "__args__", ())
        for arg in args:
            if arg is type(None):
                return True
    return False


def add_route_def(
    openapi_schema: Dict[str, Any],
    route: web.ResourceRoute,
    method: str,
    graph: DependencyGraph,
) -> None:
    route_info: Dict[str, Any] = {
        "description": inspect.getdoc(graph.target),
        "responses": {},
        "parameters": [],
    }
    if route.resource is None:
        return

    for dependency in graph.ordered_deps:
        if isinstance(dependency.dependency, Json):
            if (
                dependency.signature
                and dependency.signature.annotation != inspect.Parameter.empty
            ):
                input_schema = schema_of(
                    dependency.signature.annotation,
                    ref_template=REF_TEMPLATE,
                )
                openapi_schema["components"]["schemas"].update(
                    input_schema.pop("definitions"),
                )
                route_info["requestBody"] = {
                    "content": {"applicaiton/json": {"schema": input_schema}},
                }
        elif isinstance(dependency.dependency, Query):
            route_info["parameters"].append(
                {
                    "name": dependency.param_name,
                    "in": "query",
                    "description": dependency.dependency.description,
                    "required": not is_optional(dependency.signature),
                },
            )
        elif isinstance(dependency.dependency, Header):
            route_info["parameters"].append(
                {
                    "name": dependency.param_name,
                    "in": "header",
                    "description": dependency.dependency.description,
                    "required": not is_optional(dependency.signature),
                },
            )
        elif isinstance(dependency.dependency, Path):
            route_info["parameters"].append(
                {
                    "name": dependency.param_name,
                    "in": "path",
                    "description": dependency.dependency.description,
                    "required": not is_optional(dependency.signature),
                    "allowEmptyValue": is_optional(dependency.signature),
                },
            )

    openapi_schema["paths"][route.resource.canonical].update(
        {method.lower(): route_info},
    )


def setup_swagger(
    schema_url: str = "/openapi.json",
    swagger_ui_url: str = "/docs",
    enable_ui: bool = True,
    hide_heads: bool = True,
    title: str = "AioHTTP",
    description: Optional[str] = None,
    version: str = "1.0.0",
) -> Callable[[web.Application], Awaitable[None]]:
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
            if route.resource is None:
                continue
            if hide_heads and route.method == "HEAD":
                continue
            if isinstance(route._handler, InjectableFuncHandler):
                try:
                    add_route_def(
                        openapi_schema,
                        route,  # type: ignore
                        route.method,
                        route._handler.graph,
                    )
                except Exception as exc:
                    logger.warn(
                        "Cannot add route info: %s",
                        exc,
                        exc_info=True,
                    )

            elif isinstance(route._handler, InjectableViewHandler):
                for key, graph in route._handler.graph_map.items():
                    try:
                        add_route_def(
                            openapi_schema,
                            route,  # type: ignore
                            key,
                            graph,
                        )
                    except Exception as exc:
                        logger.warn(
                            "Cannot add route info: %s",
                            exc,
                            exc_info=True,
                        )

            else:
                continue

        app[SCHEMA_KEY] = openapi_schema

        app.router.add_get(
            schema_url,
            schema_handler,
        )

        if enable_ui:
            app.router.add_get(
                swagger_ui_url,
                get_swagger_handler(
                    SWAGGER_HTML_TEMPALTE.replace("{schema_url}", schema_url),
                ),
            )

    return event_handler
