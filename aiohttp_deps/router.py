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
