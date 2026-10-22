from dataclasses import dataclass
from datetime import date

import pytest
from pydantic import BaseModel

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
