from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from typing import cast as type_cast

from pyspark.sql import Column, DataFrame, SparkSession, types
from pyspark.sql import functions as F

from data_joinery.model_schema import (
    ModelSchema,
    get_model_fields,
    is_schema_model,
)
from data_joinery.schema_types import (
    CoercionMode,
    DifferenceKind,
    SchemaCoercionError,
    SchemaDiff,
    SchemaDifference,
)

from .. import type_inspection
from .base import DataFrameBackend, register_backend


@dataclass(frozen=True)
class SparkContext:
    spark: SparkSession


def _schema_diff(given: types.StructType, expected: types.StructType) -> SchemaDiff:
    additional: list[SchemaDifference] = []
    missing: list[SchemaDifference] = []
    type_mismatches: list[SchemaDifference] = []

    def add_difference(
        kind: DifferenceKind,
        path: str,
        given_type: types.DataType | None,
        expected_type: types.DataType | None,
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
        given_type: types.DataType,
        expected_type: types.DataType,
        path: str,
    ) -> None:
        if isinstance(given_type, types.StructType) and isinstance(
            expected_type, types.StructType
        ):
            walk_structs(given_type, expected_type, path)
            return

        if isinstance(given_type, types.ArrayType) and isinstance(
            expected_type, types.ArrayType
        ):
            walk_types(
                given_type.elementType,
                expected_type.elementType,
                f"{path}[]",
            )
            return

        if given_type != expected_type:
            add_difference("type_mismatch", path, given_type, expected_type)

    def walk_structs(
        given_struct: types.StructType,
        expected_struct: types.StructType,
        parent_path: str,
    ) -> None:
        given_fields = {field.name: field for field in given_struct.fields}
        expected_fields = {field.name: field for field in expected_struct.fields}

        for given_field in given_struct.fields:
            path = (
                given_field.name
                if not parent_path
                else f"{parent_path}.{given_field.name}"
            )
            expected_field = expected_fields.get(given_field.name)
            if expected_field is None:
                add_difference(
                    "additional",
                    path,
                    given_field.dataType,
                    None,
                )
                continue
            walk_types(
                given_field.dataType,
                expected_field.dataType,
                path,
            )

        for expected_field in expected_struct.fields:
            path = (
                expected_field.name
                if not parent_path
                else f"{parent_path}.{expected_field.name}"
            )
            if expected_field.name in given_fields:
                continue
            add_difference(
                "missing",
                path,
                None,
                expected_field.dataType,
            )

    walk_structs(given, expected, "")
    return SchemaDiff(
        tuple(additional),
        tuple(missing),
        tuple(type_mismatches),
    )


_NUMERIC = types.NumericType()
_STRING = types.StringType()
_DATE = types.DateType()
_TIME = types.TimeType()
_TIMESTAMP = types.TimestampType()
_TIMESTAMP_NTZ = types.TimestampNTZType()
_INTERVAL = types.DayTimeIntervalType()
_BOOLEAN = types.BooleanType()
_BINARY = types.BinaryType()
_ARRAY = types.ArrayType(types.NullType())
_MAP = types.MapType(types.NullType(), types.NullType())
_STRUCT = types.StructType()

CAST_MATRIX: dict[tuple[types.DataType, types.DataType], bool] = {
    (_NUMERIC, _NUMERIC): True,
    (_NUMERIC, _STRING): True,
    (_NUMERIC, _DATE): False,
    (_NUMERIC, _TIME): False,
    (_NUMERIC, _TIMESTAMP): True,
    (_NUMERIC, _TIMESTAMP_NTZ): False,
    (_NUMERIC, _INTERVAL): True,
    (_NUMERIC, _BOOLEAN): True,
    (_NUMERIC, _BINARY): False,
    (_NUMERIC, _ARRAY): False,
    (_NUMERIC, _MAP): False,
    (_NUMERIC, _STRUCT): False,
    (_STRING, _NUMERIC): True,
    (_STRING, _STRING): True,
    (_STRING, _DATE): True,
    (_STRING, _TIME): True,
    (_STRING, _TIMESTAMP): True,
    (_STRING, _TIMESTAMP_NTZ): True,
    (_STRING, _INTERVAL): True,
    (_STRING, _BOOLEAN): True,
    (_STRING, _BINARY): True,
    (_STRING, _ARRAY): False,
    (_STRING, _MAP): False,
    (_STRING, _STRUCT): False,
    (_DATE, _NUMERIC): False,
    (_DATE, _STRING): True,
    (_DATE, _DATE): True,
    (_DATE, _TIME): False,
    (_DATE, _TIMESTAMP): True,
    (_DATE, _TIMESTAMP_NTZ): True,
    (_DATE, _INTERVAL): False,
    (_DATE, _BOOLEAN): False,
    (_DATE, _BINARY): False,
    (_DATE, _ARRAY): False,
    (_DATE, _MAP): False,
    (_DATE, _STRUCT): False,
    (_TIME, _NUMERIC): False,
    (_TIME, _STRING): True,
    (_TIME, _DATE): False,
    (_TIME, _TIME): True,
    (_TIME, _TIMESTAMP): False,
    (_TIME, _TIMESTAMP_NTZ): False,
    (_TIME, _INTERVAL): False,
    (_TIME, _BOOLEAN): False,
    (_TIME, _BINARY): False,
    (_TIME, _ARRAY): False,
    (_TIME, _MAP): False,
    (_TIME, _STRUCT): False,
    (_TIMESTAMP, _NUMERIC): True,
    (_TIMESTAMP, _STRING): True,
    (_TIMESTAMP, _DATE): True,
    (_TIMESTAMP, _TIME): False,
    (_TIMESTAMP, _TIMESTAMP): True,
    (_TIMESTAMP, _TIMESTAMP_NTZ): True,
    (_TIMESTAMP, _INTERVAL): False,
    (_TIMESTAMP, _BOOLEAN): False,
    (_TIMESTAMP, _BINARY): False,
    (_TIMESTAMP, _ARRAY): False,
    (_TIMESTAMP, _MAP): False,
    (_TIMESTAMP, _STRUCT): False,
    (_TIMESTAMP_NTZ, _NUMERIC): False,
    (_TIMESTAMP_NTZ, _STRING): True,
    (_TIMESTAMP_NTZ, _DATE): True,
    (_TIMESTAMP_NTZ, _TIME): False,
    (_TIMESTAMP_NTZ, _TIMESTAMP): True,
    (_TIMESTAMP_NTZ, _TIMESTAMP_NTZ): True,
    (_TIMESTAMP_NTZ, _INTERVAL): False,
    (_TIMESTAMP_NTZ, _BOOLEAN): False,
    (_TIMESTAMP_NTZ, _BINARY): False,
    (_TIMESTAMP_NTZ, _ARRAY): False,
    (_TIMESTAMP_NTZ, _MAP): False,
    (_TIMESTAMP_NTZ, _STRUCT): False,
    (_INTERVAL, _NUMERIC): True,
    (_INTERVAL, _STRING): True,
    (_INTERVAL, _DATE): False,
    (_INTERVAL, _TIME): False,
    (_INTERVAL, _TIMESTAMP): False,
    (_INTERVAL, _TIMESTAMP_NTZ): False,
    (_INTERVAL, _INTERVAL): True,
    (_INTERVAL, _BOOLEAN): False,
    (_INTERVAL, _BINARY): False,
    (_INTERVAL, _ARRAY): False,
    (_INTERVAL, _MAP): False,
    (_INTERVAL, _STRUCT): False,
    (_BOOLEAN, _NUMERIC): True,
    (_BOOLEAN, _STRING): True,
    (_BOOLEAN, _DATE): False,
    (_BOOLEAN, _TIME): False,
    (_BOOLEAN, _TIMESTAMP): False,
    (_BOOLEAN, _TIMESTAMP_NTZ): False,
    (_BOOLEAN, _INTERVAL): False,
    (_BOOLEAN, _BOOLEAN): True,
    (_BOOLEAN, _BINARY): False,
    (_BOOLEAN, _ARRAY): False,
    (_BOOLEAN, _MAP): False,
    (_BOOLEAN, _STRUCT): False,
    (_BINARY, _NUMERIC): False,
    (_BINARY, _STRING): True,
    (_BINARY, _DATE): False,
    (_BINARY, _TIME): False,
    (_BINARY, _TIMESTAMP): False,
    (_BINARY, _TIMESTAMP_NTZ): False,
    (_BINARY, _INTERVAL): False,
    (_BINARY, _BOOLEAN): False,
    (_BINARY, _BINARY): True,
    (_BINARY, _ARRAY): False,
    (_BINARY, _MAP): False,
    (_BINARY, _STRUCT): False,
    (_ARRAY, _NUMERIC): False,
    (_ARRAY, _STRING): True,
    (_ARRAY, _DATE): False,
    (_ARRAY, _TIME): False,
    (_ARRAY, _TIMESTAMP): False,
    (_ARRAY, _TIMESTAMP_NTZ): False,
    (_ARRAY, _INTERVAL): False,
    (_ARRAY, _BOOLEAN): False,
    (_ARRAY, _BINARY): False,
    (_ARRAY, _ARRAY): True,
    (_ARRAY, _MAP): False,
    (_ARRAY, _STRUCT): False,
    (_MAP, _NUMERIC): False,
    (_MAP, _STRING): True,
    (_MAP, _DATE): False,
    (_MAP, _TIME): False,
    (_MAP, _TIMESTAMP): False,
    (_MAP, _TIMESTAMP_NTZ): False,
    (_MAP, _INTERVAL): False,
    (_MAP, _BOOLEAN): False,
    (_MAP, _BINARY): False,
    (_MAP, _ARRAY): False,
    (_MAP, _MAP): True,
    (_MAP, _STRUCT): False,
    (_STRUCT, _NUMERIC): False,
    (_STRUCT, _STRING): True,
    (_STRUCT, _DATE): False,
    (_STRUCT, _TIME): False,
    (_STRUCT, _TIMESTAMP): False,
    (_STRUCT, _TIMESTAMP_NTZ): False,
    (_STRUCT, _INTERVAL): False,
    (_STRUCT, _BOOLEAN): False,
    (_STRUCT, _BINARY): False,
    (_STRUCT, _ARRAY): False,
    (_STRUCT, _MAP): False,
    (_STRUCT, _STRUCT): True,
}


def _cast_matrix_type(data_type: types.DataType) -> types.DataType | None:
    if isinstance(data_type, types.NumericType):
        return _NUMERIC
    if isinstance(data_type, types.ArrayType):
        return _ARRAY
    if isinstance(data_type, types.MapType):
        return _MAP
    if isinstance(data_type, types.StructType):
        return _STRUCT
    if isinstance(data_type, types.StringType):
        return _STRING
    if isinstance(data_type, types.DateType):
        return _DATE
    if isinstance(data_type, types.TimeType):
        return _TIME
    if isinstance(data_type, types.TimestampNTZType):
        return _TIMESTAMP_NTZ
    if isinstance(data_type, types.TimestampType):
        return _TIMESTAMP
    if isinstance(data_type, (types.YearMonthIntervalType, types.DayTimeIntervalType)):
        return _INTERVAL
    if isinstance(data_type, types.BooleanType):
        return _BOOLEAN
    if isinstance(data_type, types.BinaryType):
        return _BINARY
    return None


def _is_cast_compatible(
    given: types.DataType | None, expected: types.DataType | None
) -> bool:
    if given is None or expected is None:
        return False
    if given == expected:
        return True

    given_category = _cast_matrix_type(given)
    expected_category = _cast_matrix_type(expected)
    if given_category is None or expected_category is None:
        return False
    return CAST_MATRIX.get((given_category, expected_category), False)


def _get_spark_schema_from_model(klass: type[Any]) -> types.StructType:
    if not is_schema_model(klass):
        raise ValueError(
            f"{klass.__name__} is neither a dataclass nor a pydantic model"
        )

    struct_fields = [
        types.StructField(name, _get_spark_field_type(field_type), True)
        for name, field_type in get_model_fields(klass)
    ]

    return types.StructType(struct_fields)


def _get_spark_field_type(field_type: Any) -> types.DataType:
    annotated_spark_type = type_inspection.spark_type_from_annotated(field_type)
    if annotated_spark_type is not None:
        return annotated_spark_type

    normalized_type = type_inspection.normalize_python_type(field_type)

    if is_schema_model(normalized_type):
        return _get_spark_schema_from_model(normalized_type)

    if type_inspection.is_list(normalized_type):
        element_type = type_inspection.get_list_element_type(normalized_type)
        element_spark_type = _get_spark_field_type(element_type)
        return types.ArrayType(element_spark_type, True)

    return type_inspection.get_spark_type_from_python_type(normalized_type)


def _coerce_strict(
    dataframe: DataFrame,
    schema: types.StructType,
) -> DataFrame:
    diff = _schema_diff(dataframe.schema, schema)
    violations = (*diff.missing, *diff.additional, *diff.type_mismatches)
    if violations:
        raise SchemaCoercionError("strict", violations)
    return dataframe


def _make_column_nullable(column: Column, data_type: types.DataType) -> Column:
    if isinstance(data_type, types.StructType):
        value = F.struct(
            *(
                _make_column_nullable(
                    column.getField(field.name), field.dataType
                ).alias(field.name, metadata=field.metadata)
                for field in data_type.fields
            )
        )
    elif isinstance(data_type, types.ArrayType):
        value = F.transform(
            column,
            lambda element: _make_column_nullable(element, data_type.elementType),
        )
    elif isinstance(data_type, types.MapType):
        value = F.transform_values(
            column,
            lambda _key, value: _make_column_nullable(value, data_type.valueType),
        )
    else:
        value = column

    # Unlike a cast or alias, a conditional expression widens Spark's inferred
    # nullability while preserving values and remaining a lazy transformation.
    return F.when(column.isNull(), F.lit(None)).otherwise(value)


def _make_dataframe_nullable(dataframe: DataFrame) -> DataFrame:
    return dataframe.select(
        *(
            _make_column_nullable(dataframe[field.name], field.dataType).alias(
                field.name, metadata=field.metadata
            )
            for field in dataframe.schema.fields
        )
    )


def _build_projected_column(
    column: Column,
    source_type: types.DataType,
    target_type: types.DataType,
    *,
    cast: bool,
    recurse: bool,
) -> Column:
    if recurse and isinstance(target_type, types.StructType):
        if not isinstance(source_type, types.StructType):
            raise ValueError(f"Expected struct type but found {source_type}")

        source_fields = {field.name: field.dataType for field in source_type.fields}
        nested_columns = []
        for target_field in target_type.fields:
            if target_field.name not in source_fields:
                raise ValueError(f"Missing field '{target_field.name}'")
            nested_column = _build_projected_column(
                column.getField(target_field.name),
                source_fields[target_field.name],
                target_field.dataType,
                cast=cast,
                recurse=recurse,
            )
            nested_columns.append(nested_column.alias(target_field.name))
        return F.struct(*nested_columns)

    if recurse and isinstance(target_type, types.ArrayType):
        if not isinstance(source_type, types.ArrayType):
            raise ValueError(f"Expected array type but found {source_type}")

        return F.transform(
            column,
            lambda element: _build_projected_column(
                element,
                source_type.elementType,
                target_type.elementType,
                cast=cast,
                recurse=recurse,
            ),
        )

    if source_type == target_type:
        return column

    if cast:
        return column.cast(target_type)

    raise ValueError(f"Type mismatch: expected {target_type}, found {source_type}")


def _project_fields(
    dataframe: DataFrame,
    schema: types.StructType,
    *,
    mode: CoercionMode,
    cast: bool,
    recurse: bool,
) -> DataFrame:
    diff = _schema_diff(dataframe.schema, schema)
    type_mismatches = (
        tuple(
            difference
            for difference in diff.type_mismatches
            if not _is_cast_compatible(
                type_cast(types.DataType | None, difference.given),
                type_cast(types.DataType | None, difference.expected),
            )
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

    source_fields = {field.name: field.dataType for field in dataframe.schema.fields}

    columns = [
        _build_projected_column(
            F.col(field.name),
            source_fields[field.name],
            field.dataType,
            cast=cast,
            recurse=recurse,
        ).alias(field.name)
        for field in schema.fields
    ]
    return dataframe.select(*columns)


class SchemaCoercionMode(Protocol):
    def __call__(self, dataframe: DataFrame, schema: types.StructType) -> DataFrame: ...


class Strict(SchemaCoercionMode):
    def __call__(self, dataframe: DataFrame, schema: types.StructType) -> DataFrame:
        return _coerce_strict(dataframe, schema)


class ProjectTopLevel(SchemaCoercionMode):
    def __call__(self, dataframe: DataFrame, schema: types.StructType) -> DataFrame:
        return _project_fields(
            dataframe, schema, mode="project_top_level", cast=False, recurse=False
        )


class Project(SchemaCoercionMode):
    def __call__(self, dataframe: DataFrame, schema: types.StructType) -> DataFrame:
        return _project_fields(
            dataframe, schema, mode="project", cast=False, recurse=True
        )


class ProjectCast(SchemaCoercionMode):
    def __call__(self, dataframe: DataFrame, schema: types.StructType) -> DataFrame:
        return _project_fields(
            dataframe, schema, mode="project_cast", cast=True, recurse=True
        )


_MODE_HANDLERS: dict[
    CoercionMode, Callable[[DataFrame, types.StructType], DataFrame]
] = {
    "strict": Strict(),
    "project": Project(),
    "project_top_level": ProjectTopLevel(),
    "project_cast": ProjectCast(),
}


def _session_from_create_options(options: dict[str, object]) -> SparkSession:
    unexpected = set(options) - {"session"}
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise TypeError(f"Unexpected Spark dataframe options: {names}")
    session = options.get("session")
    if not isinstance(session, SparkSession):
        raise TypeError("Spark dataframe creation requires a SparkSession as 'session'")
    return session


class SparkBackend(DataFrameBackend[DataFrame, types.StructType]):
    name = "spark"
    dataframe_type = DataFrame
    schema_type = types.StructType

    def compile_schema(self, schema: ModelSchema[Any]) -> types.StructType:
        fields = []
        for field in schema.fields:
            try:
                field_type = _get_spark_field_type(field.annotation)
            except ValueError as error:
                raise ValueError(
                    f"Schema '{schema.model.__name__}' field '{field.name}' "
                    f"({field.annotation!r}): {error}. Use a supported Python "
                    "type or an Annotated Spark type."
                ) from error
            fields.append(types.StructField(field.name, field_type, True))
        return types.StructType(fields)

    def create_dataframe(
        self,
        rows: Sequence[object],
        schema: ModelSchema[Any],
        **kwargs: object,
    ) -> DataFrame:
        session = _session_from_create_options(kwargs)
        serialized_rows = schema.serialize_rows(type_cast(Sequence[Any], rows))
        return session.createDataFrame(serialized_rows, self.compile_schema(schema))

    def coerce_dataframe(
        self,
        dataframe: DataFrame,
        schema: ModelSchema[Any],
        mode: CoercionMode,
    ) -> DataFrame:
        if not isinstance(dataframe, DataFrame):
            raise TypeError(
                "Spark coercion requires a pyspark.sql.DataFrame; "
                f"got {type(dataframe).__name__}."
            )
        if mode not in _MODE_HANDLERS:
            raise ValueError(
                f"Unsupported coercion mode {mode!r}. Choose 'strict', 'project', "
                "'project_top_level', or 'project_cast'."
            )
        handler = _MODE_HANDLERS[mode]
        return _make_dataframe_nullable(handler(dataframe, self.compile_schema(schema)))


SPARK_BACKEND = SparkBackend()
register_backend(SPARK_BACKEND)
