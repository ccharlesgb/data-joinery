import builtins
import runpy
from types import GenericAlias
from typing import Annotated, Literal, Optional

import pytest

from data_joinery import type_inspection


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (int, int),
        (Optional[int], int),  # noqa: UP045 - exercise typing.Optional
        (int | None, int),
        (Annotated[int, "metadata"], int),
        (Annotated[list[int] | None, "metadata"], list[int]),
        (Annotated[int, "metadata"] | None, int),
        (int | str | None, int | str | None),
        (Literal[1, 2], Literal[1, 2]),
    ],
)
def test_normalize_python_type(annotation, expected):
    assert type_inspection.normalize_python_type(annotation) == expected


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [(list[int], True), (Annotated[list[int] | None, "metadata"], True), (int, False)],
)
def test_is_list(annotation, expected):
    assert type_inspection.is_list(annotation) is expected


def test_get_list_element_type_preserves_element_annotation():
    element_type = Annotated[int, "metadata"]

    assert (
        type_inspection.get_list_element_type(list[element_type] | None) == element_type
    )


def test_get_list_element_type_rejects_non_list():
    with pytest.raises(ValueError, match="is not a list type"):
        type_inspection.get_list_element_type(int)


def test_get_list_element_type_rejects_missing_element_type():
    with pytest.raises(ValueError, match="should have exactly one type argument"):
        type_inspection.get_list_element_type(GenericAlias(list, ()))


def test_annotation_helpers_load_without_dataframe_backends(monkeypatch):
    original_import = builtins.__import__

    def import_without_backends(name, *args, **kwargs):
        if name.split(".")[0] in {"pyspark", "polars"}:
            raise AssertionError(f"Annotation helpers imported {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_backends)
    helpers = runpy.run_path(type_inspection.__file__)

    assert (
        helpers["normalize_python_type"](Annotated[list[int] | None, "metadata"])
        == list[int]
    )


def test_unknown_module_attribute_raises_attribute_error():
    with pytest.raises(AttributeError, match="has no attribute 'unknown'"):
        _ = type_inspection.unknown
