from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from data_joinery import Schema
from data_joinery.backends import DataFrameBackend, register_backend
from data_joinery.model_schema import ModelSchema
from data_joinery.schema_types import (
    CoercionMode,
    SchemaCoercionError,
    SchemaDifference,
)


@dataclass(frozen=True)
class ExampleDataFrame:
    columns: tuple[str, ...]


class ExampleBackend(DataFrameBackend[ExampleDataFrame, tuple[str, ...]]):
    name = "example"
    dataframe_type = ExampleDataFrame
    schema_type = tuple

    def compile_schema(self, schema: ModelSchema[Any]) -> tuple[str, ...]:
        return tuple(field.name for field in schema.fields)

    def coerce_dataframe(
        self,
        dataframe: ExampleDataFrame,
        schema: ModelSchema[Any],
        mode: CoercionMode,
    ) -> ExampleDataFrame:
        expected = self.compile_schema(schema)
        missing = tuple(
            SchemaDifference("missing", name, None, name)
            for name in expected
            if name not in dataframe.columns
        )
        additional = tuple(
            SchemaDifference("additional", name, name, None)
            for name in dataframe.columns
            if name not in expected
        )
        violations = missing + (additional if mode == "strict" else ())
        if violations:
            raise SchemaCoercionError(mode, violations)
        if mode == "strict":
            return dataframe
        return ExampleDataFrame(expected)

    def create_dataframe(
        self,
        rows: Sequence[object],
        schema: ModelSchema[Any],
        **kwargs: object,
    ) -> ExampleDataFrame:
        if kwargs:
            raise TypeError(f"Unexpected options: {', '.join(kwargs)}")
        schema.serialize_rows(rows)
        return ExampleDataFrame(self.compile_schema(schema))


backend: DataFrameBackend[ExampleDataFrame, tuple[str, ...]] = ExampleBackend()
register_backend(backend)


@dataclass
class Order:
    order_id: int


print(Schema(Order).native_schema(tuple))
print(Schema(Order).create_dataframe([Order(1)], ExampleDataFrame))
