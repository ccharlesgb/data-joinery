import datetime
import decimal
from types import GenericAlias
from typing import Annotated, Literal

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from pydantic import BaseModel
from pyspark.sql import types

from data_joinery import Column, JoineryModel, Schema, column
from tests.models import Item


class PortableRow(JoineryModel):
    row_id: Column[int] = column(name="id")
    text: Column[str]
    number: Column[float]
    active: Column[Literal[True, False]]
    timestamp: Column[datetime.datetime]
    day: Column[datetime.date]
    duration: Column[datetime.timedelta]
    amount: Column[decimal.Decimal]
    payload: Column[bytes]
    optional: Column[int | None]
    level: Column[Literal[1, 2] | None]
    label: Column[Literal["a", "b"]]
    item: Column[Item]
    items: Column[list[Item | None] | None]
    tags: Column[list[str]]


_POLARS_ITEM = pl.Struct({"value": pl.Int64})
_SPARK_ITEM = types.StructType([types.StructField("value", types.LongType())])


@pytest.mark.parametrize(
    "expected",
    [
        pytest.param(
            pl.Schema(
                {
                    "id": pl.Int64,
                    "text": pl.String,
                    "number": pl.Float64,
                    "active": pl.Boolean,
                    "timestamp": pl.Datetime("us"),
                    "day": pl.Date,
                    "duration": pl.Duration("us"),
                    "amount": pl.Decimal(precision=38, scale=18),
                    "payload": pl.Binary,
                    "optional": pl.Int64,
                    "level": pl.Int64,
                    "label": pl.String,
                    "item": _POLARS_ITEM,
                    "items": pl.List(_POLARS_ITEM),
                    "tags": pl.List(pl.String),
                }
            ),
            id="polars",
        ),
        pytest.param(
            types.StructType(
                [
                    types.StructField("id", types.LongType()),
                    types.StructField("text", types.StringType()),
                    types.StructField("number", types.DoubleType()),
                    types.StructField("active", types.BooleanType()),
                    types.StructField("timestamp", types.TimestampType()),
                    types.StructField("day", types.DateType()),
                    types.StructField("duration", types.DayTimeIntervalType()),
                    types.StructField("amount", types.DecimalType(38, 18)),
                    types.StructField("payload", types.BinaryType()),
                    types.StructField("optional", types.LongType()),
                    types.StructField("level", types.LongType()),
                    types.StructField("label", types.StringType()),
                    types.StructField("item", _SPARK_ITEM),
                    types.StructField("items", types.ArrayType(_SPARK_ITEM)),
                    types.StructField("tags", types.ArrayType(types.StringType())),
                ]
            ),
            id="spark",
        ),
    ],
)
def test_native_schema_compiles_portable_model_fields(
    expected: pl.Schema | types.StructType,
) -> None:
    actual = Schema(PortableRow).native_schema(type(expected))

    assert actual == expected


@pytest.mark.parametrize(
    "expected",
    [
        pytest.param(
            pl.Schema(
                {
                    "amount": pl.Decimal(precision=10, scale=2),
                    "items": pl.List(pl.UInt32),
                    "label": pl.String,
                }
            ),
            id="polars",
        ),
        pytest.param(
            types.StructType(
                [
                    types.StructField("amount", types.DecimalType(10, 2)),
                    types.StructField("items", types.ArrayType(types.ShortType())),
                    types.StructField("label", types.StringType()),
                ]
            ),
            id="spark",
        ),
    ],
)
def test_native_schema_honors_native_annotations(
    expected: pl.Schema | types.StructType,
) -> None:
    class Row(JoineryModel):
        amount: Column[
            Annotated[
                int,
                "metadata",
                pl.Decimal(precision=10, scale=2),
                types.DecimalType(10, 2),
            ]
        ]
        items: Column[list[Annotated[int, pl.UInt32, types.ShortType()]]]
        label: Column[Annotated[Literal[1, "a"], pl.String, types.StringType()]]

    actual = Schema(Row).native_schema(type(expected))

    assert actual == expected


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(Annotated[Literal[300], pl.UInt32] | None, id="inner-override"),
        pytest.param(
            Annotated[Annotated[Literal[300], pl.UInt8] | None, pl.UInt32],
            id="outer-override-takes-precedence",
        ),
        pytest.param(
            Annotated[Annotated[Literal[300], pl.UInt32] | None, "description"],
            id="outer-metadata-without-override",
        ),
    ],
)
@pytest.mark.parametrize("model_kind", ["joinery", "pydantic"])
def test_polars_strict_coercion_honors_optional_literal_override(
    annotation: object,
    model_kind: str,
) -> None:
    class Row(JoineryModel):
        value: Column[annotation]  # type: ignore[invalid-type-form]

    class PydanticRow(BaseModel):
        value: annotation  # type: ignore[invalid-type-form]

    model = PydanticRow if model_kind == "pydantic" else Row
    expected = pl.DataFrame({"value": [300, None]}, schema={"value": pl.UInt32})

    actual = Schema(model).coerce_dataframe(expected.clone(), "strict")

    assert_frame_equal(actual, expected)


@pytest.mark.parametrize(
    "schema_type", [pl.Schema, types.StructType], ids=["polars", "spark"]
)
@pytest.mark.parametrize(
    ("annotation", "message"),
    [
        pytest.param(
            Literal[1, "a"],
            "Literal values must resolve to a single",
            id="mixed-literal",
        ),
        pytest.param(object, "Unsupported Python type", id="unsupported-type"),
        pytest.param(
            GenericAlias(list, ()),
            "should have exactly one type argument",
            id="untyped-list",
        ),
    ],
)
def test_native_schema_rejects_unsupported_annotations(
    schema_type: type[pl.Schema] | type[types.StructType],
    annotation: object,
    message: str,
) -> None:
    class Row(JoineryModel):
        value: Column[annotation]  # type: ignore[invalid-type-form]

    with pytest.raises(ValueError, match=message):
        Schema(Row).native_schema(schema_type)
