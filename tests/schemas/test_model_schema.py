from dataclasses import dataclass
from datetime import date
from typing import Annotated

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from pydantic import BaseModel
from pyspark.sql import types

from data_joinery import Schema, Strict, transform
from data_joinery.schemas.joinery_model import Column, JoineryModel, column
from data_joinery.schemas.model_schema import ModelField, ModelSchema


@dataclass
class DataclassDetail:
    day: date


@dataclass
class DataclassRow:
    details: list[DataclassDetail]


class PydanticDetail(BaseModel):
    day: date


class PydanticRow(BaseModel):
    details: list[PydanticDetail]


@pytest.mark.parametrize(
    ("model", "row"),
    [
        (DataclassRow, DataclassRow([DataclassDetail(date(2026, 1, 1))])),
        (
            PydanticRow,
            PydanticRow(details=[PydanticDetail(day=date(2026, 1, 1))]),
        ),
    ],
)
def test_serialize_rows_returns_nested_dictionaries_with_python_values(model, row):
    actual = ModelSchema.from_model(model).serialize_rows([row])

    expected = [{"details": [{"day": date(2026, 1, 1)}]}]
    assert actual == expected


class JoineryDetail(JoineryModel):
    day: Column[date] = column(name="Event Day")


class JoineryRow(JoineryModel):
    detail: Column[JoineryDetail] = column(name="Current Detail")
    history: Column[list[JoineryDetail]]


def test_joinery_fields_use_column_names_and_preserve_annotations():
    class Balance(JoineryModel):
        value: Column[Annotated[int, "metadata"]] = column(name="Account Value")

    expected = ModelSchema(
        Balance, (ModelField("Account Value", Annotated[int, "metadata"]),)
    )

    assert ModelSchema.from_model(Balance) == expected


def test_serialize_joinery_rows_uses_nested_column_names():
    detail = JoineryDetail(day=date(2026, 1, 1))
    row = JoineryRow(detail=detail, history=[detail])
    actual = ModelSchema.from_model(JoineryRow).serialize_rows([row])
    expected = [
        {
            "Current Detail": {"Event Day": date(2026, 1, 1)},
            "history": [{"Event Day": date(2026, 1, 1)}],
        }
    ]

    assert actual == expected


def test_serialize_dataclass_with_nested_joinery_model_uses_column_names():
    @dataclass
    class Wrapper:
        detail: JoineryDetail

    row = Wrapper(JoineryDetail(day=date(2026, 1, 1)))
    actual = ModelSchema.from_model(Wrapper).serialize_rows([row])
    expected = [{"detail": {"Event Day": date(2026, 1, 1)}}]

    assert actual == expected


def test_serialize_joinery_models_in_containers_uses_column_names():
    class Containers(JoineryModel):
        values: Column[dict[str, tuple[JoineryDetail, ...]]]

    row = Containers(values={"events": (JoineryDetail(day=date(2026, 1, 1)),)})
    actual = ModelSchema.from_model(Containers).serialize_rows([row])
    expected = [{"values": {"events": ({"Event Day": date(2026, 1, 1)},)}}]

    assert actual == expected


def test_joinery_aliases_create_polars_dataframes():
    row = JoineryDetail(day=date(2026, 1, 1))
    actual = Schema(JoineryDetail).create_dataframe([row], pl.DataFrame)
    expected = pl.DataFrame({"Event Day": [date(2026, 1, 1)]})

    assert_frame_equal(actual, expected)


def test_joinery_nested_aliases_compile_spark_schemas():
    detail = types.StructType([types.StructField("Event Day", types.DateType(), True)])
    expected = types.StructType(
        [
            types.StructField("Current Detail", detail, True),
            types.StructField("history", types.ArrayType(detail, True), True),
        ]
    )

    assert Schema(JoineryRow).native_schema(types.StructType) == expected


def test_joinery_aliases_validate_transform_dataframes():
    @transform
    def identity(
        frame: Annotated[pl.DataFrame, Strict(JoineryDetail)],
    ) -> pl.DataFrame:
        return frame

    expected = pl.DataFrame({"Event Day": [date(2026, 1, 1)]})

    assert_frame_equal(identity(expected), expected)
