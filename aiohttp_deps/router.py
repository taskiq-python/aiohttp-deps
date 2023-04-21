from typing import Iterable

from aiohttp import web


class Router(web.RouteTableDef):
    """
    Custom router for mypy.

    This class is used to define new routes.

    Because after you initialize dependencies contexts,
    handler functions won't have the same types as
    in default AioHTTP code.

    New types are introduced in stub file: router.pyi.
    """

    def add_routes(self, router: Iterable[web.RouteDef], prefix: str = "") -> None:
        """
        Append another router's routes to this one.

        :param router: router to get routes from.
        :param prefix: url prefix for routes, defaults to ""
        :raises ValueError: if prefix is incorrect.
        """
        if prefix and not prefix.startswith("/"):
            raise ValueError("Prefix must start with a `/`")
        if prefix and prefix.endswith("/"):
            raise ValueError("Prefix should not end with a `/`")
        for route in router:
            self._items.append(
                web.RouteDef(
                    method=route.method,
                    path=prefix + route.path,
                    handler=route.handler,
                    kwargs=route.kwargs,
                ),
            )
