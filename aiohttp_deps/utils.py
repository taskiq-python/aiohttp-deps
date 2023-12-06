import inspect
import json
from typing import Any, Optional, Union

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
        description: str = "",
    ) -> None:
        self.default = default
        self.alias = alias
        self.multiple = multiple
        self.description = description
        self.type_initialized = False
        self.type_cache: "Union[pydantic.TypeAdapter[Any], None]" = None

    def __call__(
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

        if not self.type_initialized:
            if (
                param_info.definition
                and param_info.definition.annotation != inspect.Parameter.empty
            ):
                self.type_cache = pydantic.TypeAdapter(param_info.definition.annotation)
            else:
                self.type_cache = None
            self.type_initialized = True

        if self.multiple:
            value = request.headers.getall(header_name, default_value)
        else:
            value = request.headers.getone(header_name, default_value)

        if self.type_cache is None:
            return value

        try:
            return self.type_cache.validate_python(value)
        except pydantic.ValidationError as err:
            errors = err.errors(include_url=False)
            for error in errors:
                error["loc"] = (
                    "header",
                    header_name,
                ) + error["loc"]
                error.pop("input", None)  # type: ignore
            raise web.HTTPBadRequest(
                headers={"Content-Type": "application/json"},
                text=json.dumps(errors),
            ) from err


class Json:
    """
    Get and parse the body as json.

    This dependency, gets body, tries to parse it as json,
    and then converts it to type from your typehints.
    """

    def __init__(self) -> None:
        self.type_initialized = False
        self.type_cache: "Union[pydantic.TypeAdapter[Any], None]" = None

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
        try:
            body = await request.json()
        except ValueError:
            body = None

        if not self.type_initialized:
            if (
                param_info.definition
                and param_info.definition.annotation != inspect.Parameter.empty
            ):
                self.type_cache = pydantic.TypeAdapter(param_info.definition.annotation)
            else:
                self.type_cache = None
            self.type_initialized = True

        if self.type_cache is None:
            return body

        try:
            return self.type_cache.validate_python(body)
        except pydantic.ValidationError as err:
            errors = err.errors(include_url=False)
            for error in errors:
                error["loc"] = ("body",) + error["loc"]
                error.pop("input", None)  # type: ignore
            raise web.HTTPBadRequest(
                headers={"Content-Type": "application/json"},
                text=json.dumps(errors),
            ) from err


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
        description: str = "",
    ) -> None:
        self.default = default
        self.alias = alias
        self.multiple = multiple
        self.description = description
        self.type_initialized = False
        self.type_cache: "Union[pydantic.TypeAdapter[Any], None]" = None

    def __call__(
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

        if not self.type_initialized:
            if (
                param_info.definition
                and param_info.definition.annotation != inspect.Parameter.empty
            ):
                self.type_cache = pydantic.TypeAdapter(param_info.definition.annotation)
            else:
                self.type_cache = None
            self.type_initialized = True

        if self.multiple:
            value = request.query.getall(param_name, default_value)
        else:
            value = request.query.getone(param_name, default_value)

        if self.type_cache is None:
            return value

        try:
            return self.type_cache.validate_python(value)
        except pydantic.ValidationError as err:
            errors = err.errors(include_url=False)
            for error in errors:
                error["loc"] = (
                    "query",
                    param_name,
                ) + error["loc"]
                error.pop("input", None)  # type: ignore
            raise web.HTTPBadRequest(
                headers={"Content-Type": "application/json"},
                text=json.dumps(errors),
            ) from err


class Form:
    """
    Get and validate form data.

    This dependency grabs form data and validates
    it against given schema.

    You should provide schema with typehints.
    """

    def __init__(self) -> None:
        self.type_initialized = False
        self.type_cache: "Union[pydantic.TypeAdapter[Any], None]" = None

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

        if not self.type_initialized:
            if (
                param_info.definition
                and param_info.definition.annotation != inspect.Parameter.empty
            ):
                self.type_cache = pydantic.TypeAdapter(param_info.definition.annotation)
            else:
                self.type_cache = None
            self.type_initialized = True

        if self.type_cache is None:
            return form_data

        try:
            return self.type_cache.validate_python(form_data)
        except pydantic.ValidationError as err:
            errors = err.errors(include_url=False)
            for error in errors:
                error.pop("input", None)  # type: ignore
                error["loc"] = ("form",) + error["loc"]
            raise web.HTTPBadRequest(
                headers={"Content-Type": "application/json"},
                text=json.dumps(errors),
            ) from err


class Path:
    """
    Get path parameter.

    This class takes a path parameter
    from request and tries to parse it
    in target type.
    """

    def __init__(
        self,
        default: Any = ...,
        *,
        alias: Optional[str] = None,
        description: str = "",
    ) -> None:
        self.default = default
        self.alias = alias
        self.description = description
        self.type_initialized = False
        self.type_cache: "Union[pydantic.TypeAdapter[Any], None]" = None

    def __call__(
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
        matched_data = request.match_info.get(self.alias or param_info.name)

        if not self.type_initialized:
            if (
                param_info.definition
                and param_info.definition.annotation != inspect.Parameter.empty
            ):
                self.type_cache = pydantic.TypeAdapter(param_info.definition.annotation)
            else:
                self.type_cache = None
            self.type_initialized = True

        if self.type_cache is None:
            return matched_data

        try:
            return self.type_cache.validate_python(matched_data)
        except pydantic.ValidationError as err:
            errors = err.errors(include_url=False)
            for error in errors:
                error.pop("input", None)  # type: ignore
                error["loc"] = ("path",) + error["loc"]
            raise web.HTTPBadRequest(
                headers={"Content-Type": "application/json"},
                text=json.dumps(errors),
            ) from err
