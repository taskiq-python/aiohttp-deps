import inspect
from typing import Optional, Union

import pytest

from aiohttp_deps.swagger import _is_optional


def test_optional():
    def tfunc(param: Optional[int]):
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert _is_optional(param)


def test_untyped():
    def tfunc(param):
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert _is_optional(param)


def test_unioned_optional():
    def tfunc(param: Union[int, None]):
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert _is_optional(param)


def test_unioned():
    def tfunc(param: Union[int, str]):
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert not _is_optional(param)


@pytest.mark.skip("We doesn't support 3.10 annotation style yet.")
def test_new_type_style():
    def tfunc(param: "int | None"):
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert _is_optional(param)


@pytest.mark.skip("We doesn't support string annotations yet.")
def test_string_annotation():
    def tfunc(param: "int | None"):
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert _is_optional(param)
