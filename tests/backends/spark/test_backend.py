from datetime import date
from typing import Annotated

import pytest
from pyspark.sql import SparkSession, types
from pyspark.testing import assertDataFrameEqual

from data_joinery import Column, JoineryModel, Schema, SchemaCoercionError
from data_joinery.backends.spark import backend as spark_backend

_TIME_TYPE = getattr(types, "TimeType", None)
_CAST_TYPES = {
    "number": types.LongType(),
    "string": types.StringType(),
    "date": types.DateType(),
    "time": _TIME_TYPE() if _TIME_TYPE is not None else None,
    "timestamp": types.TimestampType(),
    "timestamp_ntz": types.TimestampNTZType(),
    "interval": types.DayTimeIntervalType(),
    "boolean": types.BooleanType(),
    "binary": types.BinaryType(),
    "array": types.ArrayType(types.LongType()),
    "map": types.MapType(types.StringType(), types.LongType()),
    "struct": types.StructType([types.StructField("value", types.LongType())]),
}

_ANSI_CAST_TARGETS = {
    "number": ["number", "string", "timestamp", "interval", "boolean"],
    "string": [
        "number",
        "string",
        "date",
        "time",
        "timestamp",
        "timestamp_ntz",
        "interval",
        "boolean",
        "binary",
    ],
    "date": ["string", "date", "timestamp", "timestamp_ntz"],
    "time": ["string", "time"],
    "timestamp": ["number", "string", "date", "timestamp", "timestamp_ntz"],
    "timestamp_ntz": ["string", "date", "timestamp", "timestamp_ntz"],
    "interval": ["number", "string", "interval"],
    "boolean": ["number", "string", "boolean"],
    "binary": ["string", "binary"],
    "array": ["string", "array"],
    "map": ["string", "map"],
    "struct": ["string", "struct"],
}


@pytest.mark.parametrize(
    ("source", "target", "allowed"),
    [
        pytest.param(
            source_type,
            target_type,
            target in _ANSI_CAST_TARGETS[source],
            id=f"{source}-to-{target}",
        )
        for source, source_type in _CAST_TYPES.items()
        for target, target_type in _CAST_TYPES.items()
        if source_type is not None and target_type is not None
    ],
)
def test_is_cast_compatible_matches_spark_ansi_rules(source, target, allowed):
    assert spark_backend._is_cast_compatible(source, target) is allowed


def test_project_cast_reports_unsupported_spark_ansi_casts(spark: SparkSession):
    class SourceRow(JoineryModel):
        binary: Column[bytes | None]
        day: Column[date | None]

    class TargetRow(JoineryModel):
        binary: Column[bool]
        day: Column[int]
        required: Column[str]

    source = spark.createDataFrame(
        [(None, None)], Schema(SourceRow).native_schema(types.StructType)
    )

    with pytest.raises(SchemaCoercionError) as caught:
        Schema(TargetRow).coerce_dataframe(source, "project_cast")

    assert sorted((item.kind, item.path) for item in caught.value.violations) == [
        ("missing", "required"),
        ("type_mismatch", "binary"),
        ("type_mismatch", "day"),
    ]


def test_strict_normalizes_spark_nullability(
    spark: SparkSession,
):
    nested_type = types.StructType(
        [types.StructField("value", types.LongType(), False)]
    )

    class TargetRow(JoineryModel):
        nested: Column[Annotated[object, nested_type]]
        items: Column[Annotated[object, types.ArrayType(types.LongType(), False)]]
        lookup: Column[
            Annotated[
                object, types.MapType(types.StringType(), types.LongType(), False)
            ]
        ]

    rows = [((1,), [2], {"three": 3})]
    dataframe = spark.createDataFrame(
        rows,
        types.StructType(
            [
                types.StructField("nested", nested_type, False),
                types.StructField(
                    "items", types.ArrayType(types.LongType(), False), False
                ),
                types.StructField(
                    "lookup",
                    types.MapType(types.StringType(), types.LongType(), False),
                    False,
                ),
            ]
        ),
    )

    expected = spark.createDataFrame(rows, dataframe.schema.toNullable())

    actual = Schema(TargetRow).coerce_dataframe(dataframe, "strict")

    assertDataFrameEqual(actual, expected, ignoreNullable=False)
