"""Compile Python model annotations into native Polars types."""

import datetime
import decimal
from typing import TYPE_CHECKING, Annotated, Any, Literal, get_args, get_origin

import polars as pl

from ..model_schema import get_model_fields, is_schema_model
from ..type_inspection import normalize_python_type

POLARS_MAX_DECIMAL_PRECISION = 38
DEFAULT_FRACTIONAL_DIGITS = 18

if TYPE_CHECKING:
    from polars._typing import PolarsDataType
else:
    PolarsDataType = Any


def _polars_type_from_annotated(python_type: Any) -> PolarsDataType | None:
    if get_origin(python_type) is not Annotated:
        return None

    for metadata in get_args(python_type)[1:]:
        if isinstance(metadata, pl.DataType):
            return metadata
        if isinstance(metadata, type) and issubclass(metadata, pl.DataType):
            return metadata
    return None


def _polars_type_from_literal(
    python_type: Any,
) -> PolarsDataType | None:
    if get_origin(python_type) is not Literal:
        return None

    values = get_args(python_type)
    if not values:
        raise ValueError("Literal type must include at least one value")
    polars_types = {_get_polars_field_type(type(value)) for value in values}
    if len(polars_types) != 1:
        raise ValueError(
            f"Literal values must resolve to a single Polars type: {python_type}"
        )
    return next(iter(polars_types))


def _get_polars_field_type(field_type: Any) -> PolarsDataType:
    annotated_type = _polars_type_from_annotated(field_type)
    if annotated_type is not None:
        return annotated_type

    literal_type = _polars_type_from_literal(field_type)
    if literal_type is not None:
        return literal_type

    normalized_type = normalize_python_type(field_type)
    if is_schema_model(normalized_type):
        return pl.Struct(
            [
                pl.Field(name, _get_polars_field_type(nested_type))
                for name, nested_type in get_model_fields(normalized_type)
            ]
        )

    if get_origin(normalized_type) is list:
        args = get_args(normalized_type)
        if len(args) != 1:
            raise ValueError(
                f"List type {normalized_type} should have exactly one type argument"
            )
        return pl.List(_get_polars_field_type(args[0]))

    if normalized_type is int:
        return pl.Int64
    if normalized_type is str:
        return pl.String
    if normalized_type is float:
        return pl.Float64
    if normalized_type is bool:
        return pl.Boolean
    if normalized_type is datetime.datetime:
        return pl.Datetime("us")
    if normalized_type is datetime.date:
        return pl.Date
    if normalized_type is datetime.timedelta:
        return pl.Duration("us")
    if normalized_type is decimal.Decimal:
        return pl.Decimal(
            precision=POLARS_MAX_DECIMAL_PRECISION,
            scale=DEFAULT_FRACTIONAL_DIGITS,
        )
    if normalized_type is bytes:
        return pl.Binary
    raise ValueError(f"Unsupported Python type: {normalized_type}")
