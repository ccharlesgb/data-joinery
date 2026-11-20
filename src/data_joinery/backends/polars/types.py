"""Compile Python model annotations into native Polars types."""

import datetime
import decimal
from typing import TYPE_CHECKING, Annotated, Any, Literal, get_args, get_origin

import polars as pl

from ...schemas.model_schema import get_model_fields, is_schema_model
from ...type_inspection import (
    _resolve_literal,
    get_list_element_type,
    is_list,
    normalize_python_type,
    unwrap_optional_type,
)

POLARS_MAX_DECIMAL_PRECISION = 38
DEFAULT_FRACTIONAL_DIGITS = 18

if TYPE_CHECKING:
    from polars._typing import PolarsDataType
else:
    PolarsDataType = Any


def _polars_type_from_annotated(python_type: Any) -> PolarsDataType | None:
    python_type = unwrap_optional_type(python_type)
    if get_origin(python_type) is not Annotated:
        return None

    annotated_type, *metadata_items = get_args(python_type)
    for metadata in metadata_items:
        if isinstance(metadata, pl.DataType):
            return metadata
        if isinstance(metadata, type) and issubclass(metadata, pl.DataType):
            return metadata
    return _polars_type_from_annotated(annotated_type)


def _get_polars_field_type(field_type: Any) -> PolarsDataType:
    annotated_type = _polars_type_from_annotated(field_type)
    if annotated_type is not None:
        return annotated_type

    normalized_type = normalize_python_type(field_type)
    if get_origin(normalized_type) is Literal:
        return _resolve_literal(normalized_type, _get_polars_field_type, "Polars")

    if is_schema_model(normalized_type):
        return pl.Struct(
            [
                pl.Field(name, _get_polars_field_type(nested_type))
                for name, nested_type in get_model_fields(normalized_type)
            ]
        )

    if is_list(normalized_type):
        element_type = get_list_element_type(normalized_type)
        return pl.List(_get_polars_field_type(element_type))

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
