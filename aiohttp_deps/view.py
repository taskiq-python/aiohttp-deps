from typing import Dict

from aiohttp import web
from aiohttp.web_response import StreamResponse
from taskiq_dependencies import DependencyGraph


class View(web.View):
    """
    Custom View.

    If you're going to use dependency injection
    in handlers, please subclass this View instad of
    the default View from AioHTTP.
    """

    def __init__(
        self,
        request: web.Request,
        graph_map: Dict[str, DependencyGraph],
    ) -> None:
        self._request = request
        self._graph_map = graph_map

    async def _iter(self) -> StreamResponse:
        """
        This method is similar to the method from AioHTTP.

        It checks for available methods and if the
        method can be resolved, it resolves dependencies and
        calls the method from itself.

        :return: response
        """
        method = getattr(
            self,
            self.request.method.lower(),
            None,
        )
        if method is None:
            self._raise_allowed_methods()
        async with self._graph_map[self.request.method.lower()].async_ctx(
            {
                web.Request: self.request,
                web.Application: self.request.app,
            },
        ) as ctx:
            return await method(**(await ctx.resolve_kwargs()))  # type: ignore
