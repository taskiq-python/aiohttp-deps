import inspect
import sys
from typing import Optional, Union

import pytest

from aiohttp_deps.swagger import _is_optional


def test_optional() -> None:
    def tfunc(param: Optional[int]) -> None:
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert _is_optional(param)


def test_untyped() -> None:
    def tfunc(param) -> None:  # noqa: ANN001
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert _is_optional(param)


def test_unioned_optional() -> None:
    def tfunc(param: Union[int, None]) -> None:
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert _is_optional(param)


def test_unioned() -> None:
    def tfunc(param: Union[int, str]) -> None:
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert not _is_optional(param)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Unsupported syntax")
def test_new_type_style() -> None:
    def tfunc(param: "int | None") -> None:
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert _is_optional(param)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Unsupported syntax")
def test_string_annotation() -> None:
    def tfunc(param: "int | None") -> None:
        """Nothing."""

    param = inspect.signature(tfunc).parameters["param"]

    assert _is_optional(param)
