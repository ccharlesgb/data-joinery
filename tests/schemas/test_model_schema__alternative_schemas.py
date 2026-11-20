from dataclasses import dataclass
from datetime import date

import pytest
from pydantic import BaseModel

from data_joinery import Column, JoineryModel
from data_joinery.schemas.model_schema import ModelSchema
from tests.models import JoineryDetail


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


class JoineryDateDetail(JoineryModel):
    """A nested JoineryModel with a date field."""

    day: Column[date]


class JoineryDateRow(JoineryModel):
    """A JoineryModel row containing a list of nested dates."""

    details: Column[list[JoineryDateDetail]]


@pytest.mark.parametrize(
    "row",
    [
        pytest.param(
            JoineryDateRow(details=[JoineryDateDetail(day=date(2026, 1, 1))]),
            id="joinery",
        ),
        pytest.param(
            DataclassRow([DataclassDetail(date(2026, 1, 1))]),
            id="dataclass",
        ),
        pytest.param(
            PydanticRow(details=[PydanticDetail(day=date(2026, 1, 1))]),
            id="pydantic",
        ),
    ],
)
def test_serialize_rows_returns_nested_dictionaries_with_python_values(row):
    expected = [{"details": [{"day": date(2026, 1, 1)}]}]

    assert ModelSchema.from_model(type(row)).serialize_rows([row]) == expected


def test_serialize_dataclass_with_nested_joinery_model_uses_column_names():
    @dataclass
    class Wrapper:
        detail: JoineryDetail

    row = Wrapper(JoineryDetail(day=date(2026, 1, 1)))
    actual = ModelSchema.from_model(Wrapper).serialize_rows([row])
    expected = [{"detail": {"Event Day": date(2026, 1, 1)}}]

    assert actual == expected
