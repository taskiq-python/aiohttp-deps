from typing import Any, Dict

from aiohttp import web

SWAGGER_SCHEMA_KEY = web.AppKey("openapi_schema", Dict[str, Any])
VALUES_OVERRIDES_KEY = web.AppKey("values_overrides", Dict[Any, Any])
DEPENDENCY_OVERRIDES_KEY = web.AppKey("dependency_overrides", Dict[Any, Any])
