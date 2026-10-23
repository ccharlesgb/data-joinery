import datetime
import decimal
from typing import Annotated, Literal, Optional

import pytest
from pyspark.sql import types

from data_joinery.backends.spark import types as spark_types


@pytest.mark.parametrize(
    "python_type, expected_spark_type",
    [
        (int, types.LongType()),
        (str, types.StringType()),
        (float, types.DoubleType()),
        (bool, types.BooleanType()),
        (Optional[int], types.LongType()),  # noqa: UP045 - exercise typing.Optional
        (int | None, types.LongType()),
        (Annotated[int, types.ShortType()], types.ShortType()),
        (Annotated[int, types.IntegerType()], types.IntegerType()),
        (Annotated[int, types.StringType()], types.StringType()),
        (Literal["a", "b"], types.StringType()),
        (Literal[1, 2], types.LongType()),
        (Literal[True, False], types.BooleanType()),
        (Literal[1, 2] | None, types.LongType()),
        (Annotated[Literal[1, 2], types.IntegerType()], types.IntegerType()),
        (Annotated[Literal[1, 2], types.StringType()], types.StringType()),
        (datetime.datetime, types.TimestampType()),
        (datetime.date, types.DateType()),
        (datetime.timedelta, types.DayTimeIntervalType()),
        (
            decimal.Decimal,
            types.DecimalType(
                spark_types.SPARK_MAX_DECIMAL_PRECISION,
                spark_types.DEFAULT_FRACTIONAL_DIGITS,
            ),
        ),
        (bytes, types.BinaryType()),
    ],
)
def test_get_spark_field_type(python_type, expected_spark_type):
    actual_spark_type = spark_types._get_spark_field_type(python_type)
    assert actual_spark_type == expected_spark_type


def test_get_spark_field_type_raises_value_error_for_mixed_literal_types():
    with pytest.raises(
        ValueError,
        match=r"Literal values must resolve to a single Spark type",
    ):
        spark_types._get_spark_field_type(Literal[1, "a"])


def test_get_spark_field_type_maps_nested_optional_models():
    from dataclasses import dataclass

    @dataclass
    class Nested:
        value: int

    expected = types.ArrayType(
        types.StructType([types.StructField("value", types.LongType(), True)]), True
    )

    assert spark_types._get_spark_field_type(list[Nested | None] | None) == expected


def test_get_spark_field_type_preserves_list_element_override():
    expected = types.ArrayType(types.ShortType(), True)

    assert (
        spark_types._get_spark_field_type(list[Annotated[int, types.ShortType()]])
        == expected
    )
