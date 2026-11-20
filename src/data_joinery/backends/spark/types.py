"""Compile Python model annotations into native Spark types."""

import datetime
import decimal
from typing import Annotated, Any, Literal, get_args, get_origin

from pyspark.sql import types

from ...schemas.model_schema import get_model_fields, is_schema_model
from ...type_inspection import (
    _resolve_literal,
    get_list_element_type,
    is_list,
    normalize_python_type,
)

SPARK_MAX_DECIMAL_PRECISION = 38
DEFAULT_FRACTIONAL_DIGITS = 18


def _spark_type_from_annotated(python_type: Any) -> types.DataType | None:
    origin = get_origin(python_type)
    args = get_args(python_type)

    if origin is not Annotated or len(args) < 2:
        return None

    for metadata in args[1:]:
        if isinstance(metadata, types.DataType):
            return metadata

    return None


def _get_spark_field_type(field_type: Any) -> types.DataType:
    annotated_spark_type = _spark_type_from_annotated(field_type)
    if annotated_spark_type is not None:
        return annotated_spark_type

    normalized_type = normalize_python_type(field_type)
    if get_origin(normalized_type) is Literal:
        return _resolve_literal(normalized_type, _get_spark_field_type, "Spark")

    if is_schema_model(normalized_type):
        return types.StructType(
            [
                types.StructField(name, _get_spark_field_type(annotation), True)
                for name, annotation in get_model_fields(normalized_type)
            ]
        )

    if is_list(normalized_type):
        element_type = get_list_element_type(normalized_type)
        return types.ArrayType(_get_spark_field_type(element_type), True)

    if normalized_type is int:
        return types.LongType()
    elif normalized_type is str:
        return types.StringType()
    elif normalized_type is float:
        return types.DoubleType()
    elif normalized_type is bool:
        return types.BooleanType()
    elif normalized_type is datetime.datetime:
        return types.TimestampType()
    elif normalized_type is datetime.date:
        return types.DateType()
    elif normalized_type is datetime.timedelta:
        return types.DayTimeIntervalType()
    elif normalized_type is decimal.Decimal:
        return types.DecimalType(SPARK_MAX_DECIMAL_PRECISION, DEFAULT_FRACTIONAL_DIGITS)
    elif normalized_type is bytes:
        return types.BinaryType()
    else:
        raise ValueError(f"Unsupported Python type: {normalized_type}")
