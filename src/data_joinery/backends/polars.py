import datetime
import decimal
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    Union,
    cast,
    get_args,
    get_origin,
)

import polars as pl

from data_joinery.model_schema import ModelSchema, get_model_fields, is_schema_model
from data_joinery.schema_types import (
    CoercionMode,
    DifferenceKind,
    SchemaCoercionError,
    SchemaDiff,
    SchemaDifference,
)

from .base import register_backend

NoneType = type(None)
POLARS_MAX_DECIMAL_PRECISION = 38
DEFAULT_FRACTIONAL_DIGITS = 18

if TYPE_CHECKING:
    from polars._typing import PolarsDataType
else:
    PolarsDataType = Any


def _normalize_python_type(python_type: Any) -> Any:
    origin = get_origin(python_type)
    args = get_args(python_type)

    if origin is Annotated and args:
        return _normalize_python_type(args[0])

    if origin in (Union, UnionType) and args:
        non_none_args = [arg for arg in args if arg is not NoneType]
        if len(non_none_args) == 1 and len(non_none_args) != len(args):
            return _normalize_python_type(non_none_args[0])

    return python_type


def _polars_type_from_annotated(python_type: Any) -> PolarsDataType | None:
    if get_origin(python_type) is not Annotated:
        return None

    for metadata in get_args(python_type)[1:]:
        if isinstance(metadata, pl.DataType):
            return metadata
        if isinstance(metadata, type) and issubclass(metadata, pl.DataType):
            return metadata
    return None


def _polars_type_from_literal(
    python_type: Any,
) -> PolarsDataType | None:
    if get_origin(python_type) is not Literal:
        return None

    values = get_args(python_type)
    if not values:
        raise ValueError("Literal type must include at least one value")
    polars_types = {_get_polars_field_type(type(value)) for value in values}
    if len(polars_types) != 1:
        raise ValueError(
            f"Literal values must resolve to a single Polars type: {python_type}"
        )
    return next(iter(polars_types))


def _get_polars_field_type(field_type: Any) -> PolarsDataType:
    annotated_type = _polars_type_from_annotated(field_type)
    if annotated_type is not None:
        return annotated_type

    literal_type = _polars_type_from_literal(field_type)
    if literal_type is not None:
        return literal_type

    normalized_type = _normalize_python_type(field_type)
    if is_schema_model(normalized_type):
        return pl.Struct(
            [
                pl.Field(name, _get_polars_field_type(nested_type))
                for name, nested_type in get_model_fields(normalized_type)
            ]
        )

    if get_origin(normalized_type) is list:
        args = get_args(normalized_type)
        if len(args) != 1:
            raise ValueError(
                f"List type {normalized_type} should have exactly one type argument"
            )
        return pl.List(_get_polars_field_type(args[0]))

    if normalized_type is int:
        return pl.Int64
    if normalized_type is str:
        return pl.String
    if normalized_type is float:
        return pl.Float64
    if normalized_type is bool:
        return pl.Boolean
    if normalized_type is datetime.datetime:
        return pl.Datetime("us")
    if normalized_type is datetime.date:
        return pl.Date
    if normalized_type is datetime.timedelta:
        return pl.Duration("us")
    if normalized_type is decimal.Decimal:
        return pl.Decimal(
            precision=POLARS_MAX_DECIMAL_PRECISION,
            scale=DEFAULT_FRACTIONAL_DIGITS,
        )
    if normalized_type is bytes:
        return pl.Binary
    raise ValueError(f"Unsupported Python type: {normalized_type}")


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
    dataframe: pl.DataFrame,
    schema: pl.Schema,
    *,
    mode: CoercionMode,
    cast: bool,
    recurse: bool,
) -> pl.DataFrame:
    diff = _schema_diff(dataframe.schema, schema)
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
        return dataframe.select(schema.names())

    expressions = [
        _build_projected_expression(
            pl.col(name), dataframe.schema[name], target_type, cast=cast
        ).alias(name)
        for name, target_type in schema.items()
    ]
    try:
        return dataframe.select(expressions)
    except pl.exceptions.PolarsError as error:
        if cast and diff.type_mismatches:
            raise SchemaCoercionError(mode, diff.type_mismatches) from error
        raise


def _serialize_rows(schema: ModelSchema[Any], rows: Sequence[object]) -> list[object]:
    serialized = schema.serialize_rows(rows)  # type: ignore[arg-type]
    return [
        asdict(cast(Any, row))
        if is_dataclass(row) and not isinstance(row, type)
        else row
        for row in serialized
    ]


def _validate_create_options(options: dict[str, object]) -> None:
    if options:
        names = ", ".join(sorted(options))
        raise TypeError(f"Unexpected Polars dataframe options: {names}")


class PolarsBackend:
    name = "polars"
    dataframe_types = (pl.DataFrame,)
    schema_types = (pl.Schema,)

    def compile_schema(self, schema: ModelSchema[Any]) -> pl.Schema:
        return pl.Schema(
            {
                field.name: _get_polars_field_type(field.annotation)
                for field in schema.fields
            }
        )

    def create_dataframe(
        self,
        rows: Sequence[object],
        schema: ModelSchema[Any],
        **kwargs: object,
    ) -> pl.DataFrame:
        _validate_create_options(kwargs)
        return pl.DataFrame(
            _serialize_rows(schema, rows),
            schema=self.compile_schema(schema),
            strict=True,
        )

    def coerce_dataframe(
        self,
        dataframe: object,
        schema: ModelSchema[Any],
        mode: CoercionMode,
    ) -> pl.DataFrame:
        if not isinstance(dataframe, pl.DataFrame):
            raise TypeError("Polars backend requires a polars.DataFrame")

        expected = self.compile_schema(schema)
        if mode == "strict":
            diff = _schema_diff(dataframe.schema, expected)
            violations = (*diff.missing, *diff.additional, *diff.type_mismatches)
            if violations:
                raise SchemaCoercionError(mode, violations)
            return dataframe
        if mode == "project_top_level":
            return _project_fields(
                dataframe, expected, mode=mode, cast=False, recurse=False
            )
        if mode == "project":
            return _project_fields(
                dataframe, expected, mode=mode, cast=False, recurse=True
            )
        if mode == "project_cast":
            return _project_fields(
                dataframe, expected, mode=mode, cast=True, recurse=True
            )
        raise ValueError(f"Unsupported coercion mode: {mode}")


POLARS_BACKEND = PolarsBackend()
register_backend(POLARS_BACKEND)
