import inspect
import json
from typing import Any, Optional

import pydantic
from aiohttp import web
from taskiq_dependencies import Depends, ParamInfo


class Header:
    """
    Get and parse parameter from headers.

    This dependency, gets header and
    parses it to the type you provided in hints.

    Parameters:
    :param default: default value to use, if the value was not provided.
    :param alias: the name to use instead of the name of the variable, defaults to None
    :param multiple: if you want to get list of headers with similar names.
    """

    def __init__(
        self,
        default: Any = ...,
        *,
        alias: Optional[str] = None,
        multiple: bool = False,
    ):
        self.default = default
        self.alias = alias
        self.multiple = multiple

    def __call__(  # noqa: C901, WPS210
        self,
        param_info: ParamInfo = Depends(),
        request: web.Request = Depends(),
    ) -> Any:
        """
        Performs actual logic, described above.

        :param param_info: information about how the dependency
            was defined with name and type.
        :param request: current request.
        :raises HTTPBadRequest: if incorrect data was found.
        :return: parsed data.
        """
        header_name = self.alias or param_info.name
        default_value = None
        if self.default is not ...:
            default_value = self.default

        if self.multiple:
            value = request.headers.getall(header_name, default_value)
        else:
            value = request.headers.getone(header_name, default_value)

        definition = None
        if (  # noqa: WPS337
            param_info.definition
            and param_info.definition.annotation != inspect.Parameter.empty
        ):
            definition = param_info.definition.annotation

        if definition is None:
            return value

        try:
            return pydantic.parse_obj_as(definition, value)
        except pydantic.ValidationError as err:
            errors = err.errors()
            for error in errors:
                error["loc"] = (
                    "header",
                    header_name,
                ) + error["loc"]
            raise web.HTTPBadRequest(
                headers={"Content-Type": "application/json"},
                text=json.dumps(errors),
            )


class Json:
    """
    Get and parse the body as json.

    This dependency, gets body, tries to parse it as json,
    and then converts it to type from your typehints.
    """

    async def __call__(  # noqa: C901
        self,
        param_info: ParamInfo = Depends(),
        request: web.Request = Depends(),
    ) -> Any:
        """
        Performs actual logic, described above.

        :param param_info: information about how the dependency
            was defined with name and type.
        :param request: current request.
        :raises HTTPBadRequest: if incorrect data was found.
        :return: parsed data.
        """
        try:
            body = await request.json()
        except ValueError:
            body = None

        definition = None
        if (  # noqa: WPS337
            param_info.definition
            and param_info.definition.annotation != inspect.Parameter.empty
        ):
            definition = param_info.definition.annotation

        if definition is None:
            return body

        try:
            return pydantic.parse_obj_as(definition, body)
        except pydantic.ValidationError as err:
            errors = err.errors()
            for error in errors:
                error["loc"] = ("body",) + error["loc"]
            raise web.HTTPBadRequest(
                headers={"Content-Type": "application/json"},
                text=json.dumps(errors),
            )


class Query:
    """
    Get and parse parameter from querystring.

    This dependency, gets querystring and
    parses the parameter it to the type you provided in hints.

    Parameters:
    :param default: default value to use, if the value was not provided.
    :param alias: the name to use instead of the name of the variable, defaults to None
    :param multiple: if you want to get list of query parameters with similar names.
    """

    def __init__(
        self,
        default: Any = ...,
        *,
        alias: Optional[str] = None,
        multiple: bool = False,
    ):
        self.default = default
        self.alias = alias
        self.multiple = multiple

    def __call__(  # noqa: C901, WPS210
        self,
        param_info: ParamInfo = Depends(),
        request: web.Request = Depends(),
    ) -> Any:
        """
        Performs actual logic, described above.

        :param param_info: information about how the dependency
            was defined with name and type.
        :param request: current request.
        :raises HTTPBadRequest: if incorrect data was found.
        :return: parsed data.
        """
        param_name = self.alias or param_info.name
        default_value = None
        if self.default is not ...:
            default_value = self.default

        if self.multiple:
            value = request.query.getall(param_name, default_value)
        else:
            value = request.query.getone(param_name, default_value)

        definition = None
        if (  # noqa: WPS337
            param_info.definition
            and param_info.definition.annotation != inspect.Parameter.empty
        ):
            definition = param_info.definition.annotation

        if definition is None:
            return value

        try:
            return pydantic.parse_obj_as(definition, value)
        except pydantic.ValidationError as err:
            errors = err.errors()
            for error in errors:
                error["loc"] = (
                    "query",
                    param_name,
                ) + error["loc"]
            raise web.HTTPBadRequest(
                headers={"Content-Type": "application/json"},
                text=json.dumps(errors),
            )


class Form:
    """
    Get and validate form data.

    This dependency grabs form data and validates
    it against given schema.

    You should provide schema with typehints.
    """

    async def __call__(
        self,
        param_info: ParamInfo = Depends(),
        request: web.Request = Depends(),
    ) -> Any:
        """
        Performs actual logic, described above.

        :param param_info: information about how the dependency
            was defined with name and type.
        :param request: current request.
        :raises HTTPBadRequest: if incorrect data was found.
        :return: parsed data.
        """
        form_data = await request.post()
        definition = None
        if (  # noqa: WPS337
            param_info.definition
            and param_info.definition.annotation != inspect.Parameter.empty
        ):
            definition = param_info.definition.annotation

        if definition is None:
            return form_data

        try:
            return pydantic.parse_obj_as(definition, form_data)
        except pydantic.ValidationError as err:
            errors = err.errors()
            for error in errors:
                error["loc"] = ("form",) + error["loc"]
            raise web.HTTPBadRequest(
                headers={"Content-Type": "application/json"},
                text=json.dumps(errors),
            )
