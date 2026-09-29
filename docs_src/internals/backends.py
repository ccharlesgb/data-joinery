from collections.abc import Sequence
from typing import Any

from data_joinery.backends import DataFrameBackend, register_backend
from data_joinery.model_schema import ModelSchema
from data_joinery.schema_types import CoercionMode


class ExampleDataFrame:
    pass


class ExampleBackend:
    name = "example"
    dataframe_types = (ExampleDataFrame,)
    schema_types = (tuple,)

    def compile_schema(self, schema: ModelSchema[Any]) -> object:
        return tuple(field.name for field in schema.fields)

    def coerce_dataframe(
        self,
        dataframe: object,
        schema: ModelSchema[Any],
        mode: CoercionMode,
    ) -> object:
        return dataframe

    def create_dataframe(
        self,
        rows: Sequence[object],
        schema: ModelSchema[Any],
        **kwargs: object,
    ) -> object:
        return ExampleDataFrame()


backend: DataFrameBackend = ExampleBackend()
register_backend(backend)
