"""Compile Python model annotations into native Spark types."""

import datetime
import decimal
from typing import Annotated, Any, Literal, get_args, get_origin

from pyspark.sql import types

from ..schemas.model_schema import get_model_fields, is_schema_model
from ..type_inspection import (
    get_list_element_type,
    is_list,
    normalize_python_type,
)

SPARK_MAX_DECIMAL_PRECISION = 38
DEFAULT_FRACTIONAL_DIGITS = 18


def spark_type_from_annotated(python_type: Any) -> types.DataType | None:
    origin = get_origin(python_type)
    args = get_args(python_type)

    if origin is not Annotated or len(args) < 2:
        return None

    for metadata in args[1:]:
        if isinstance(metadata, types.DataType):
            return metadata

    return None


def spark_type_from_literal(python_type: Any) -> types.DataType | None:
    if get_origin(python_type) is not Literal:
        return None

    literal_values = get_args(python_type)
    if not literal_values:
        raise ValueError("Literal type must include at least one value")

    spark_types = {
        get_spark_type_from_python_type(type(literal_value))
        for literal_value in literal_values
    }

    if len(spark_types) != 1:
        raise ValueError(
            f"Literal values must resolve to a single Spark type: {python_type}"
        )

    return next(iter(spark_types))


def get_spark_type_from_python_type(python_type: type) -> types.DataType:
    annotated_spark_type = spark_type_from_annotated(python_type)
    if annotated_spark_type is not None:
        return annotated_spark_type

    literal_spark_type = spark_type_from_literal(python_type)
    if literal_spark_type is not None:
        return literal_spark_type

    python_type = normalize_python_type(python_type)

    if python_type is int:
        return types.LongType()
    elif python_type is str:
        return types.StringType()
    elif python_type is float:
        return types.DoubleType()
    elif python_type is bool:
        return types.BooleanType()
    elif python_type is datetime.datetime:
        return types.TimestampType()
    elif python_type is datetime.date:
        return types.DateType()
    elif python_type is datetime.timedelta:
        return types.DayTimeIntervalType()
    elif python_type is decimal.Decimal:
        return types.DecimalType(SPARK_MAX_DECIMAL_PRECISION, DEFAULT_FRACTIONAL_DIGITS)
    elif python_type is bytes:
        return types.BinaryType()
    else:
        raise ValueError(f"Unsupported Python type: {python_type}")


def _get_spark_schema_from_model(klass: type[Any]) -> types.StructType:
    if not is_schema_model(klass):
        raise ValueError(
            f"{klass.__name__} is neither a dataclass nor a pydantic model"
        )

    struct_fields = [
        types.StructField(name, _get_spark_field_type(field_type), True)
        for name, field_type in get_model_fields(klass)
    ]

    return types.StructType(struct_fields)


def _get_spark_field_type(field_type: Any) -> types.DataType:
    annotated_spark_type = spark_type_from_annotated(field_type)
    if annotated_spark_type is not None:
        return annotated_spark_type

    normalized_type = normalize_python_type(field_type)

    if is_schema_model(normalized_type):
        return _get_spark_schema_from_model(normalized_type)

    if is_list(normalized_type):
        element_type = get_list_element_type(normalized_type)
        element_spark_type = _get_spark_field_type(element_type)
        return types.ArrayType(element_spark_type, True)

    return get_spark_type_from_python_type(normalized_type)
