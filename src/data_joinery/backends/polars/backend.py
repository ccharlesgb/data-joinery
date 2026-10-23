from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import polars as pl

from data_joinery.schemas.coercion_error import (
    CoercionMode,
    DifferenceKind,
    SchemaCoercionError,
    SchemaDiff,
    SchemaDifference,
)

from ..protocol import DataFrameBackend
from ..registry import register_backend
from .types import _get_polars_field_type

if TYPE_CHECKING:
    from polars._typing import PolarsDataType

    from data_joinery.schemas.model_schema import ModelSchema
else:
    PolarsDataType = Any


def _schema_diff(given: pl.Schema, expected: pl.Schema) -> SchemaDiff:
    additional: list[SchemaDifference] = []
    missing: list[SchemaDifference] = []
    type_mismatches: list[SchemaDifference] = []

    def add_difference(
        kind: DifferenceKind,
        path: str,
        given_type: object | None,
        expected_type: object | None,
    ) -> None:
        difference = SchemaDifference(kind, path, given_type, expected_type)
        match kind:
            case "additional":
                additional.append(difference)
            case "missing":
                missing.append(difference)
            case "type_mismatch":
                type_mismatches.append(difference)

    def walk_types(
        given_type: PolarsDataType,
        expected_type: PolarsDataType,
        path: str,
    ) -> None:
        if isinstance(given_type, pl.Struct) and isinstance(expected_type, pl.Struct):
            walk_fields(given_type.fields, expected_type.fields, path)
            return
        if isinstance(given_type, pl.List) and isinstance(expected_type, pl.List):
            walk_types(given_type.inner, expected_type.inner, f"{path}[]")
            return
        if given_type != expected_type:
            add_difference("type_mismatch", path, given_type, expected_type)

    def walk_fields(
        given_fields: Sequence[pl.Field],
        expected_fields: Sequence[pl.Field],
        parent_path: str,
    ) -> None:
        given_by_name = {field.name: field for field in given_fields}
        expected_by_name = {field.name: field for field in expected_fields}

        for given_field in given_fields:
            path = (
                given_field.name
                if not parent_path
                else f"{parent_path}.{given_field.name}"
            )
            expected_field = expected_by_name.get(given_field.name)
            if expected_field is None:
                add_difference("additional", path, given_field.dtype, None)
            else:
                walk_types(given_field.dtype, expected_field.dtype, path)

        for expected_field in expected_fields:
            if expected_field.name in given_by_name:
                continue
            path = (
                expected_field.name
                if not parent_path
                else f"{parent_path}.{expected_field.name}"
            )
            add_difference("missing", path, None, expected_field.dtype)

    walk_fields(
        [pl.Field(name, dtype) for name, dtype in given.items()],
        [pl.Field(name, dtype) for name, dtype in expected.items()],
        "",
    )
    return SchemaDiff(tuple(additional), tuple(missing), tuple(type_mismatches))


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
        return pl.struct(
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
    *,
    mode: CoercionMode,
    cast: bool,
    recurse: bool,
) -> pl.DataFrame | pl.LazyFrame:
    diff = _schema_diff(given_schema, expected_schema)
    type_mismatches = (
        tuple(
            difference
            for difference in diff.type_mismatches
            if not _is_cast_compatible(difference.given, difference.expected)
        )
        if cast
        else diff.type_mismatches
    )
    nested_additional = (
        tuple(
            difference
            for difference in diff.additional
            if "." in difference.path or "[]" in difference.path
        )
        if not recurse
        else ()
    )
    violations = (*diff.missing, *nested_additional, *type_mismatches)
    if violations:
        raise SchemaCoercionError(mode, violations)

    if not recurse:
        return dataframe.select(expected_schema.names())

    expressions = [
        _build_projected_expression(
            pl.col(name), given_schema[name], target_type, cast=cast
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
        fields: dict[str, PolarsDataType] = {}
        for field in schema.fields:
            try:
                fields[field.name] = _get_polars_field_type(field.annotation)
            except ValueError as error:
                raise ValueError(
                    f"Schema '{schema.model.__name__}' field '{field.name}' "
                    f"({field.annotation!r}): {error}. Use a supported Python "
                    "type or an Annotated Polars type."
                ) from error
        return pl.Schema(fields)

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
        if mode == "strict":
            diff = _schema_diff(given, expected)
            violations = (*diff.missing, *diff.additional, *diff.type_mismatches)
            if violations:
                raise SchemaCoercionError(mode, violations)
            return dataframe
        if mode == "project_top_level":
            return _project_fields(
                dataframe, given, expected, mode=mode, cast=False, recurse=False
            )
        if mode == "project":
            return _project_fields(
                dataframe, given, expected, mode=mode, cast=False, recurse=True
            )
        if mode == "project_cast":
            return _project_fields(
                dataframe, given, expected, mode=mode, cast=True, recurse=True
            )
        raise ValueError(
            f"Unsupported coercion mode {mode!r}. Choose 'strict', 'project', "
            "'project_top_level', or 'project_cast'."
        )


POLARS_BACKEND = PolarsBackend()
register_backend(POLARS_BACKEND)
