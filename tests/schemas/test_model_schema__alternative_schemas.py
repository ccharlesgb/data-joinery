from dataclasses import dataclass
from datetime import date

import pytest
from pydantic import BaseModel

from data_joinery import Column, JoineryModel, column
from data_joinery.schemas.model_schema import ModelSchema


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


def test_serialize_dataclass_with_nested_joinery_model_uses_column_names():
    class JoineryDetail(JoineryModel):
        day: Column[date] = column(name="Event Day")

    @dataclass
    class Wrapper:
        detail: JoineryDetail

    row = Wrapper(JoineryDetail(day=date(2026, 1, 1)))
    actual = ModelSchema.from_model(Wrapper).serialize_rows([row])
    expected = [{"detail": {"Event Day": date(2026, 1, 1)}}]

    assert actual == expected
