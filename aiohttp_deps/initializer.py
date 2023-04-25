import copy
import inspect
from typing import Awaitable, Callable, Type

from aiohttp import hdrs, web
from taskiq_dependencies import DependencyGraph

from aiohttp_deps.view import View


class InjectableFuncHandler:
    """
    Dependency injector for function handlers.

    This class creates a dependency injection context on startup
    and then use it to server requests.


    The `__call__` method is used to serve requests.

    Usage:
    new_handler = InjectableFuncHandler(old_handler)
    response = await new_handler(request)
    """

    def __init__(
        self,
        original_route: Callable[..., Awaitable[web.StreamResponse]],
    ) -> None:
        self.original_handler = copy.copy(original_route)
        self.graph = DependencyGraph(self.original_handler)

    async def __call__(self, request: web.Request) -> web.StreamResponse:
        """
        Serve a request.

        This function creates async context and resolves all kwargs,
        required to serve current request.

        :param request: current request.
        :return: response.
        """
        async with self.graph.async_ctx(
            {
                web.Request: request,
                web.Application: request.app,
            },
        ) as resolver:
            return await self.original_handler(**(await resolver.resolve_kwargs()))


class InjectableViewHandler:
    """
    Dependency injector for views.

    This class is different from function injector,
    because it calculates graphs for all implemented methods
    of the view.

    Usage:
    new_handler = InjectableViewHandler(MyView)
    response = await new_handler(request)
    """

    def __init__(
        self,
        original_route: Type[View],
    ) -> None:
        self.original_handler = copy.copy(original_route)
        allowed_methods = {
            method.lower()
            for method in hdrs.METH_ALL
            if hasattr(original_route, method.lower())  # noqa: WPS421
        }
        self.graph_map = {
            method: DependencyGraph(getattr(original_route, method))
            for method in allowed_methods
        }

    async def __call__(self, request: web.Request) -> web.StreamResponse:
        """
        Serve a request.

        This function creates async context and resolves all kwargs,
        required to serve current request.

        :param request: current request.
        :return: response.
        """
        return await self.original_handler(request, self.graph_map)


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
        if inspect.isclass(route._handler):
            if issubclass(route._handler, View):
                route._handler = InjectableViewHandler(route._handler)
            continue
        route._handler = InjectableFuncHandler(route._handler)
