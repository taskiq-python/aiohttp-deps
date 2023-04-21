import copy
import inspect
from typing import Awaitable, Callable, Type

from aiohttp import hdrs, web
from taskiq_dependencies import DependencyGraph

from aiohttp_deps.view import View


def _function_handler(
    original_route: Callable[..., Awaitable[web.StreamResponse]],
) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    original_handler = copy.copy(original_route)
    graph = DependencyGraph(original_handler)

    async def custom_responder(request: web.Request) -> web.StreamResponse:
        async with graph.async_ctx(
            {
                web.Request: request,
                web.Application: request.app,
            },
        ) as gra:
            return await original_handler(**(await gra.resolve_kwargs()))

    return custom_responder


def _view_handler(
    original_route: Type[View],
) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    allowed_methods = {
        method.lower()
        for method in hdrs.METH_ALL
        if hasattr(original_route, method.lower())  # noqa: WPS421
    }
    graph_map = {
        method: DependencyGraph(getattr(original_route, method))
        for method in allowed_methods
    }

    async def custom_responder(request: web.Request) -> web.StreamResponse:
        return await original_route(request, graph_map)

    return custom_responder


def _route_generator(
    original_route: Callable[..., Awaitable[web.StreamResponse]],
) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    if inspect.isclass(original_route):
        if issubclass(original_route, View):
            return _view_handler(original_route)
        return original_route
    return _function_handler(original_route)


async def init(app: web.Application) -> None:
    """
    Initialize dependency injection context.

    This function is used to replace your handlers
    with handlers that can inject dependencies.

    To use this function, just add it
    in your startup list.

    >>> app = aiohttp.web.Application()
    >>> app.on_startup.append(init)

    And that's it.

    :param app: current application.
    """
    for route in app.router.routes():
        route._handler = _route_generator(route._handler)  # noqa: WPS437
