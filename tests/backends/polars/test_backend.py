from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from data_joinery import Schema, SchemaCoercionError
from data_joinery.backends.polars.backend import _schema_diff
from data_joinery.schemas.schema_diff import (
    Field,
    ListElement,
    SchemaDiff,
    SchemaDifference,
)
from tests.models import Row


def test_schema_diff_preserves_literal_names_and_nested_list_steps():
    given = pl.Schema(
        {
            "customer.name": pl.Int64,
            "customer": pl.Struct({"name": pl.Int64}),
            "items": pl.List(pl.List(pl.Struct({"legacy[]": pl.String}))),
            "legacy[]": pl.String,
        }
    )
    target = pl.Schema(
        {
            "customer.name": pl.String,
            "customer": pl.Struct({"name": pl.String}),
            "items": pl.List(pl.List(pl.Struct({"required.field": pl.Boolean}))),
        }
    )
    expected = SchemaDiff(
        additional=(
            SchemaDifference(
                "additional",
                (Field("items"), ListElement(), ListElement(), Field("legacy[]")),
                pl.String,
                None,
            ),
            SchemaDifference("additional", (Field("legacy[]"),), pl.String, None),
        ),
        missing=(
            SchemaDifference(
                "missing",
                (Field("items"), ListElement(), ListElement(), Field("required.field")),
                None,
                pl.Boolean,
            ),
        ),
        type_mismatches=(
            SchemaDifference(
                "type_mismatch", (Field("customer.name"),), pl.Int64, pl.String
            ),
            SchemaDifference(
                "type_mismatch", (Field("customer"), Field("name")), pl.Int64, pl.String
            ),
        ),
    )

    actual = _schema_diff(given, target)

    assert actual == expected


def test_eager_project_cast_reports_invalid_values_during_coercion():
    dataframe = pl.DataFrame({"value": ["not-an-integer"]})

    with pytest.raises(SchemaCoercionError) as caught:
        Schema(Row).coerce_dataframe(dataframe, "project_cast")

    assert [(item.kind, item.path) for item in caught.value.violations] == [
        ("type_mismatch", (Field("value"),))
    ]


def test_lazy_project_accepts_a_file_scan(tmp_path: Path):
    path = tmp_path / "rows.csv"
    path.write_text("value,extra\n1,2\n")
    expected = pl.DataFrame({"value": [1]})

    result = Schema(Row).coerce_dataframe(pl.scan_csv(path), "project")

    assert_frame_equal(result.collect(), expected)


def test_lazy_project_cast_defers_value_failure_until_execution():
    dataframe = pl.LazyFrame({"value": ["not-an-integer"]})
    result = Schema(Row).coerce_dataframe(dataframe, "project_cast")

    with pytest.raises(pl.exceptions.PolarsError):
        result.collect()


def test_lazy_coercion_resolves_input_schema_once(monkeypatch: pytest.MonkeyPatch):
    calls = 0
    original = pl.LazyFrame.collect_schema

    def collect_schema(frame: pl.LazyFrame) -> pl.Schema:
        nonlocal calls
        calls += 1
        return original(frame)

    monkeypatch.setattr(pl.LazyFrame, "collect_schema", collect_schema)
    Schema(Row).coerce_dataframe(pl.LazyFrame({"value": [1]}), "project")

    assert calls == 1


def test_lazy_coercion_does_not_execute_input(monkeypatch: pytest.MonkeyPatch):
    def collect(*args: object, **kwargs: object) -> None:
        raise AssertionError("LazyFrame.collect() was called")

    monkeypatch.setattr(pl.LazyFrame, "collect", collect)

    result = Schema(Row).coerce_dataframe(pl.LazyFrame({"value": [1]}), "project")

    assert isinstance(result, pl.LazyFrame)
