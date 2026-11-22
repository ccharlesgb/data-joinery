from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import polars as pl
import polars.selectors as cs

from data_joinery.schemas.coercion import (
    CoercionMode,
    check_coercion_mode,
    find_coercion_violations,
)
from data_joinery.schemas.coercion_error import SchemaCoercionError
from data_joinery.schemas.schema_diff import SchemaDiff

from .._schema import compare_schema, compile_fields
from ..protocol import DataFrameBackend
from ..registry import register_backend
from .types import _get_polars_field_type

if TYPE_CHECKING:
    from polars._typing import PolarsDataType

    from data_joinery.schemas.model_schema import ModelSchema
else:
    PolarsDataType = Any


def _struct_fields(dtype: PolarsDataType) -> list[tuple[str, PolarsDataType]] | None:
    if isinstance(dtype, pl.Struct):
        return [(field.name, field.dtype) for field in dtype.fields]
    return None


def _list_element(dtype: PolarsDataType) -> PolarsDataType | None:
    return dtype.inner if isinstance(dtype, pl.List) else None


def _schema_diff(given: pl.Schema, expected: pl.Schema) -> SchemaDiff:
    return compare_schema(
        list(given.items()),
        list(expected.items()),
        struct_fields=_struct_fields,
        list_element=_list_element,
    )


def _is_cast_compatible(given: object | None, expected: object | None) -> bool:
    try:
        given_type = pl.datatypes.parse_into_dtype(given)
        expected_type = pl.datatypes.parse_into_dtype(expected)
    except TypeError:
        return False
    if given_type == expected_type:
        return True
    try:
        pl.DataFrame(schema={"value": given_type}).select(
            pl.col("value").cast(expected_type, strict=True)
        )
    except pl.exceptions.PolarsError:
        return False
    return True


def _build_projected_expression(
    expression: pl.Expr,
    source_type: PolarsDataType,
    target_type: PolarsDataType,
    *,
    cast: bool,
) -> pl.Expr:
    if isinstance(source_type, pl.Struct) and isinstance(target_type, pl.Struct):
        source_fields = {field.name: field.dtype for field in source_type.fields}
        projected = pl.struct(
            [
                _build_projected_expression(
                    expression.struct.field(field.name),
                    source_fields[field.name],
                    field.dtype,
                    cast=cast,
                ).alias(field.name)
                for field in target_type.fields
            ]
        )
        return pl.when(expression.is_null()).then(None).otherwise(projected)

    if isinstance(source_type, pl.List) and isinstance(target_type, pl.List):
        return expression.list.eval(
            _build_projected_expression(
                pl.element(), source_type.inner, target_type.inner, cast=cast
            )
        )

    if source_type == target_type:
        return expression
    if cast:
        return expression.cast(target_type, strict=True)
    raise ValueError(f"Type mismatch: expected {target_type}, found {source_type}")


def _project_fields(
    dataframe: pl.DataFrame | pl.LazyFrame,
    given_schema: pl.Schema,
    expected_schema: pl.Schema,
    mode: CoercionMode,
    diff: SchemaDiff,
) -> pl.DataFrame | pl.LazyFrame:
    if mode == "project_top_level":
        return dataframe.select(cs.by_name(expected_schema.names()))

    cast = mode == "project_cast"
    expressions = [
        _build_projected_expression(
            cs.by_name(name).as_expr(), given_schema[name], target_type, cast=cast
        ).alias(name)
        for name, target_type in expected_schema.items()
    ]
    try:
        return dataframe.select(expressions)
    except pl.exceptions.PolarsError as error:
        if cast and diff.type_mismatches:
            raise SchemaCoercionError(mode, diff.type_mismatches) from error
        raise


def _validate_create_options(options: dict[str, object]) -> None:
    if options:
        names = ", ".join(sorted(options))
        raise TypeError(f"Unexpected Polars dataframe options: {names}")


class PolarsBackend(DataFrameBackend[pl.DataFrame | pl.LazyFrame, pl.Schema]):
    name = "polars"
    dataframe_types = (pl.DataFrame, pl.LazyFrame)
    schema_type = pl.Schema

    def compile_schema(self, schema: ModelSchema[Any]) -> pl.Schema:
        """Compile a model schema into native Polars field types."""
        return pl.Schema(dict(compile_fields(schema, _get_polars_field_type, "Polars")))

    def create_dataframe(
        self,
        rows: Sequence[object],
        schema: ModelSchema[Any],
        frame_type: type[pl.DataFrame | pl.LazyFrame],
        **kwargs: object,
    ) -> pl.DataFrame | pl.LazyFrame:
        _validate_create_options(kwargs)
        dataframe = pl.DataFrame(
            schema.serialize_rows(rows),
            schema=self.compile_schema(schema),
            strict=True,
        )
        return dataframe.lazy() if issubclass(frame_type, pl.LazyFrame) else dataframe

    def coerce_dataframe(
        self,
        dataframe: pl.DataFrame | pl.LazyFrame,
        schema: ModelSchema[Any],
        mode: CoercionMode,
    ) -> pl.DataFrame | pl.LazyFrame:
        if not isinstance(dataframe, (pl.DataFrame, pl.LazyFrame)):
            raise TypeError(
                "Polars coercion requires a polars.DataFrame or polars.LazyFrame; "
                f"got {type(dataframe).__name__}."
            )

        given = (
            dataframe.collect_schema()
            if isinstance(dataframe, pl.LazyFrame)
            else dataframe.schema
        )
        expected = self.compile_schema(schema)
        check_coercion_mode(mode)
        diff = _schema_diff(given, expected)
        violations = find_coercion_violations(diff, mode, _is_cast_compatible)
        if violations:
            raise SchemaCoercionError(mode, violations)
        if mode == "strict":
            return dataframe
        return _project_fields(dataframe, given, expected, mode, diff)


POLARS_BACKEND = PolarsBackend()
register_backend(POLARS_BACKEND)
