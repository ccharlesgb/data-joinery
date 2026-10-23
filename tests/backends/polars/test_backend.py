import datetime
import decimal
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from pydantic import BaseModel

from data_joinery import Project, Schema, SchemaCoercionError, transform
from data_joinery.backends import backend_for_frame_type, get_backend


def test_polars_backend_is_registered_for_dataframes():
    backend = get_backend("polars")

    assert backend.name == "polars"
    assert backend_for_frame_type(pl.DataFrame) is backend


def test_polars_backend_is_registered_for_lazyframes():
    assert backend_for_frame_type(pl.LazyFrame) is get_backend("polars")


def test_compile_schema_maps_model_types_to_polars_types():
    @dataclass
    class Nested:
        value: int

    @dataclass
    class Row:
        integer: int
        text: str
        number: float
        flag: bool
        timestamp: datetime.datetime
        day: datetime.date
        duration: datetime.timedelta
        amount: decimal.Decimal
        payload: bytes
        optional: int | None
        literal: Literal["a", "b"]
        overridden: Annotated[int, pl.UInt32]
        nested: Nested
        items: list[Nested]

    assert Schema(Row).native_schema(pl.Schema) == pl.Schema(
        {
            "integer": pl.Int64,
            "text": pl.String,
            "number": pl.Float64,
            "flag": pl.Boolean,
            "timestamp": pl.Datetime("us"),
            "day": pl.Date,
            "duration": pl.Duration("us"),
            "amount": pl.Decimal(precision=38, scale=18),
            "payload": pl.Binary,
            "optional": pl.Int64,
            "literal": pl.String,
            "overridden": pl.UInt32,
            "nested": pl.Struct({"value": pl.Int64}),
            "items": pl.List(pl.Struct({"value": pl.Int64})),
        }
    )


def test_create_dataframe_serializes_dataclass_rows():
    @dataclass
    class Nested:
        value: str

    @dataclass
    class Row:
        row_id: int
        nested: Nested
        items: list[Nested]

    result = Schema(Row).create_dataframe(
        [Row(1, Nested("a"), [Nested("b")])], pl.DataFrame
    )

    expected = pl.DataFrame(
        {"row_id": [1], "nested": [{"value": "a"}], "items": [[{"value": "b"}]]},
        schema={
            "row_id": pl.Int64,
            "nested": pl.Struct({"value": pl.String}),
            "items": pl.List(pl.Struct({"value": pl.String})),
        },
    )
    assert isinstance(result, pl.DataFrame)
    assert_frame_equal(result, expected)


def test_create_dataframe_serializes_pydantic_rows():
    class Row(BaseModel):
        row_id: int
        label: str

    result = Schema(Row).create_dataframe([Row(row_id=1, label="a")], pl.DataFrame)

    assert isinstance(result, pl.DataFrame)
    assert_frame_equal(result, pl.DataFrame({"row_id": [1], "label": ["a"]}))


def test_create_dataframe_rejects_backend_options():
    @dataclass
    class Row:
        row_id: int

    with pytest.raises(TypeError, match="Unexpected Polars dataframe options: context"):
        Schema(Row).create_dataframe([Row(1)], pl.DataFrame, context=object())


def test_strict_accepts_reordered_columns_and_preserves_source_order():
    @dataclass
    class Row:
        first: int
        second: str

    dataframe = pl.DataFrame({"second": ["a"], "first": [1]})

    result = Schema(Row).coerce_dataframe(dataframe, "strict")

    assert result is dataframe
    assert result.columns == ["second", "first"]


def test_strict_reports_all_schema_differences():
    @dataclass
    class Row:
        value: int
        required: str

    dataframe = pl.DataFrame({"value": ["wrong"], "extra": [1]})

    with pytest.raises(SchemaCoercionError) as caught:
        Schema(Row).coerce_dataframe(dataframe, "strict")

    assert [(item.kind, item.path) for item in caught.value.violations] == [
        ("missing", "required"),
        ("additional", "extra"),
        ("type_mismatch", "value"),
    ]


def test_project_top_level_selects_columns_without_projecting_nested_fields():
    @dataclass
    class Nested:
        value: int

    @dataclass
    class Row:
        row_id: int
        nested: Nested

    dataframe = pl.DataFrame(
        {
            "extra": ["drop"],
            "nested": [{"value": 2}],
            "row_id": [1],
        },
        schema={
            "extra": pl.String,
            "nested": pl.Struct({"value": pl.Int64}),
            "row_id": pl.Int64,
        },
    )

    result = Schema(Row).coerce_dataframe(dataframe, "project_top_level")

    assert result.columns == ["row_id", "nested"]
    assert result.schema["nested"] == pl.Struct({"value": pl.Int64})


def test_project_top_level_rejects_nested_schema_differences():
    @dataclass
    class Nested:
        value: int

    @dataclass
    class Row:
        nested: Nested

    dataframe = pl.DataFrame(
        {"nested": [{"value": 2, "nested_extra": "reject"}]},
        schema={"nested": pl.Struct({"value": pl.Int64, "nested_extra": pl.String})},
    )

    with pytest.raises(SchemaCoercionError) as caught:
        Schema(Row).coerce_dataframe(dataframe, "project_top_level")

    assert [(item.kind, item.path) for item in caught.value.violations] == [
        ("additional", "nested.nested_extra")
    ]


def test_project_recursively_projects_structs_and_lists_of_structs():
    @dataclass
    class Nested:
        value: int

    @dataclass
    class Row:
        nested: Nested
        items: list[Nested]

    source_struct = pl.Struct({"extra": pl.String, "value": pl.Int64})
    dataframe = pl.DataFrame(
        {
            "nested": [{"extra": "x", "value": 1}],
            "items": [[{"extra": "y", "value": 2}]],
            "top_extra": [3],
        },
        schema={
            "nested": source_struct,
            "items": pl.List(source_struct),
            "top_extra": pl.Int64,
        },
    )

    result = Schema(Row).coerce_dataframe(dataframe, "project")

    assert result.schema == pl.Schema(
        {
            "nested": pl.Struct({"value": pl.Int64}),
            "items": pl.List(pl.Struct({"value": pl.Int64})),
        }
    )
    assert result.to_dicts() == [{"nested": {"value": 1}, "items": [{"value": 2}]}]


def test_project_rejects_type_mismatches():
    @dataclass
    class Row:
        value: int

    with pytest.raises(SchemaCoercionError) as caught:
        Schema(Row).coerce_dataframe(pl.DataFrame({"value": ["1"]}), "project")

    assert [(item.kind, item.path) for item in caught.value.violations] == [
        ("type_mismatch", "value")
    ]


def test_project_cast_casts_nested_structs_and_lists_of_structs():
    @dataclass
    class Nested:
        value: int

    @dataclass
    class Row:
        nested: Nested
        items: list[Nested]

    source_struct = pl.Struct({"value": pl.String})
    dataframe = pl.DataFrame(
        {
            "nested": [{"value": "1"}],
            "items": [[{"value": "2"}]],
        },
        schema={"nested": source_struct, "items": pl.List(source_struct)},
    )

    result = Schema(Row).coerce_dataframe(dataframe, "project_cast")

    assert result.schema == pl.Schema(
        {
            "nested": pl.Struct({"value": pl.Int64}),
            "items": pl.List(pl.Struct({"value": pl.Int64})),
        }
    )
    assert result.to_dicts() == [{"nested": {"value": 1}, "items": [{"value": 2}]}]


def test_project_cast_translates_data_dependent_cast_failures():
    @dataclass
    class Row:
        value: int

    dataframe = pl.DataFrame({"value": ["not-an-integer"]})

    with pytest.raises(SchemaCoercionError) as caught:
        Schema(Row).coerce_dataframe(dataframe, "project_cast")

    assert caught.value.mode == "project_cast"
    assert [(item.kind, item.path) for item in caught.value.violations] == [
        ("type_mismatch", "value")
    ]


@dataclass
class LazyRow:
    value: int


def test_create_lazyframe_returns_requested_type():
    result = Schema(LazyRow).create_dataframe([LazyRow(1)], pl.LazyFrame)

    assert isinstance(result, pl.LazyFrame)


def test_create_lazyframe_serializes_model_rows():
    result = Schema(LazyRow).create_dataframe([LazyRow(1)], pl.LazyFrame)
    expected = pl.DataFrame({"value": [1]})

    assert_frame_equal(result.collect(), expected)


def test_lazy_default_coercion_preserves_original_frame():
    dataframe = pl.LazyFrame({"value": [1]})

    assert Schema(LazyRow).coerce_dataframe(dataframe) is dataframe


def test_default_coercion_rejects_extra_column():
    dataframe = pl.DataFrame({"value": [1], "extra": [2]})

    with pytest.raises(SchemaCoercionError, match="Additional field 'extra'"):
        Schema(LazyRow).coerce_dataframe(dataframe)


def test_lazy_strict_reports_schema_mismatch_before_execution():
    dataframe = pl.LazyFrame({"value": ["wrong"], "extra": [1]})

    with pytest.raises(SchemaCoercionError) as caught:
        Schema(LazyRow).coerce_dataframe(dataframe, "strict")

    assert [(item.kind, item.path) for item in caught.value.violations] == [
        ("additional", "extra"),
        ("type_mismatch", "value"),
    ]


def test_lazy_project_top_level_selects_expected_columns():
    dataframe = pl.LazyFrame({"extra": [2], "value": [1]})
    expected = pl.DataFrame({"value": [1]})

    result = Schema(LazyRow).coerce_dataframe(dataframe, "project_top_level")

    assert_frame_equal(result.collect(), expected)


def test_lazy_project_accepts_a_file_scan(tmp_path: Path):
    path = tmp_path / "rows.csv"
    path.write_text("value,extra\n1,2\n")
    expected = pl.DataFrame({"value": [1]})

    result = Schema(LazyRow).coerce_dataframe(pl.scan_csv(path), "project")

    assert_frame_equal(result.collect(), expected)


def test_lazy_project_prunes_nested_structs_and_lists():
    @dataclass
    class Nested:
        value: int

    @dataclass
    class Row:
        nested: Nested
        items: list[Nested]

    source_struct = pl.Struct({"extra": pl.String, "value": pl.Int64})
    dataframe = pl.DataFrame(
        {
            "nested": [{"extra": "x", "value": 1}],
            "items": [[{"extra": "y", "value": 2}]],
            "top_extra": [3],
        },
        schema={
            "nested": source_struct,
            "items": pl.List(source_struct),
            "top_extra": pl.Int64,
        },
    ).lazy()
    expected = pl.DataFrame(
        {"nested": [{"value": 1}], "items": [[{"value": 2}]]},
        schema={
            "nested": pl.Struct({"value": pl.Int64}),
            "items": pl.List(pl.Struct({"value": pl.Int64})),
        },
    )

    result = Schema(Row).coerce_dataframe(dataframe, "project")

    assert_frame_equal(result.collect(), expected)


def test_lazy_project_rejects_missing_column_before_execution():
    with pytest.raises(SchemaCoercionError, match="Missing field 'value'"):
        Schema(LazyRow).coerce_dataframe(pl.LazyFrame({"extra": [1]}), "project")


def test_lazy_project_cast_casts_nested_structs_and_lists():
    @dataclass
    class Nested:
        value: int

    @dataclass
    class Row:
        nested: Nested
        items: list[Nested]

    source_struct = pl.Struct({"value": pl.String})
    dataframe = pl.DataFrame(
        {"nested": [{"value": "1"}], "items": [[{"value": "2"}]]},
        schema={"nested": source_struct, "items": pl.List(source_struct)},
    ).lazy()
    expected = pl.DataFrame(
        {"nested": [{"value": 1}], "items": [[{"value": 2}]]},
        schema={
            "nested": pl.Struct({"value": pl.Int64}),
            "items": pl.List(pl.Struct({"value": pl.Int64})),
        },
    )

    result = Schema(Row).coerce_dataframe(dataframe, "project_cast")

    assert_frame_equal(result.collect(), expected)


def test_lazy_project_cast_defers_value_failure_until_execution():
    dataframe = pl.LazyFrame({"value": ["not-an-integer"]})
    result = Schema(LazyRow).coerce_dataframe(dataframe, "project_cast")

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
    Schema(LazyRow).coerce_dataframe(pl.LazyFrame({"value": [1]}), "project")

    assert calls == 1


def test_lazy_coercion_does_not_execute_input(monkeypatch: pytest.MonkeyPatch):
    def collect(*args: object, **kwargs: object) -> None:
        raise AssertionError("LazyFrame.collect() was called")

    monkeypatch.setattr(pl.LazyFrame, "collect", collect)

    result = Schema(LazyRow).coerce_dataframe(pl.LazyFrame({"value": [1]}))

    assert isinstance(result, pl.LazyFrame)


def test_unbound_contract_accepts_lazyframe():
    result = Project(LazyRow).validate(pl.LazyFrame({"value": [1]}))

    assert isinstance(result, pl.LazyFrame)


def test_lazy_transform_rejects_eager_input():
    @transform
    def accept(frame: Annotated[pl.LazyFrame, Project(LazyRow)]) -> None:
        pass

    with pytest.raises(TypeError, match="must be a LazyFrame"):
        accept(pl.DataFrame({"value": [1]}))  # type: ignore[bad-argument-type]
