from dataclasses import dataclass
from types import GenericAlias
from typing import Annotated, Literal

import polars as pl
import pytest

from data_joinery.backends.polars_types import _get_polars_field_type


@dataclass
class Nested:
    value: int


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (Annotated[int, "metadata", pl.UInt32], pl.UInt32),
        (
            Annotated[int, pl.Decimal(precision=10, scale=2)],
            pl.Decimal(precision=10, scale=2),
        ),
        (Annotated[Literal[1, "a"], pl.String], pl.String),
        (list[Nested | None] | None, pl.List(pl.Struct({"value": pl.Int64}))),
        (list[Annotated[int, pl.UInt32]], pl.List(pl.UInt32)),
        (Literal[True, False], pl.Boolean),
    ],
)
def test_get_polars_field_type(annotation, expected):
    assert _get_polars_field_type(annotation) == expected


@pytest.mark.parametrize(
    ("annotation", "message"),
    [
        (Literal[1, "a"], "Literal values must resolve to a single Polars type"),
        (object, "Unsupported Python type"),
        (GenericAlias(list, ()), "should have exactly one type argument"),
    ],
)
def test_get_polars_field_type_rejects_unsupported_annotations(annotation, message):
    with pytest.raises(ValueError, match=message):
        _get_polars_field_type(annotation)
