from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Any

import pytest
from pyspark.sql import DataFrame

from data_joinery import Pipeline, Project, Schema, Strict, transform
from data_joinery.backends import backend_for_schema_type, register_backend
from data_joinery.model_schema import ModelSchema
from data_joinery.pipeline import PipelineConnectionError
from data_joinery.schema_types import CoercionMode


@dataclass(frozen=True)
class FakeDataFrame:
    columns: tuple[str, ...]


class FakeBackend:
    name = "fake"
    dataframe_types: tuple[type, ...] = (FakeDataFrame,)
    schema_types: tuple[type, ...] = (tuple,)

    def compile_schema(self, schema: ModelSchema[Any]) -> object:
        return tuple(field.name for field in schema.fields)

    def coerce_dataframe(
        self,
        dataframe: object,
        schema: ModelSchema[Any],
        mode: CoercionMode,
    ) -> object:
        if not isinstance(dataframe, FakeDataFrame):
            raise TypeError
        expected = tuple(field.name for field in schema.fields)
        if mode == "strict" and set(dataframe.columns) != set(expected):
            raise ValueError("schema mismatch")
        return FakeDataFrame(expected)

    def create_dataframe(
        self,
        rows: Sequence[object],
        schema: ModelSchema[Any],
        **kwargs: object,
    ) -> object:
        if kwargs:
            raise TypeError
        schema.serialize_rows(rows)
        return FakeDataFrame(tuple(field.name for field in schema.fields))


FAKE_BACKEND = FakeBackend()
register_backend(FAKE_BACKEND)


@dataclass
class Order:
    order_id: int


def test_schema_delegates_to_a_registered_backend():
    schema = Schema(Order)

    assert schema.native_schema(tuple) == ("order_id",)
    assert schema.create_dataframe([Order(1)], FakeDataFrame) == FakeDataFrame(
        ("order_id",)
    )


def test_backend_is_discovered_from_its_native_schema_type():
    assert backend_for_schema_type(tuple) is FAKE_BACKEND


def test_registration_rejects_an_ambiguous_dataframe_type():
    class AmbiguousBackend(FakeBackend):
        name = "ambiguous-frame"
        schema_types = (dict,)

    with pytest.raises(TypeError, match="ambiguous dataframe type"):
        register_backend(AmbiguousBackend())


def test_registration_rejects_an_ambiguous_schema_type():
    class OtherDataFrame:
        pass

    class AmbiguousBackend(FakeBackend):
        name = "ambiguous-schema"
        dataframe_types = (OtherDataFrame,)

    with pytest.raises(TypeError, match="ambiguous schema type"):
        register_backend(AmbiguousBackend())


def test_transform_binds_dataframe_contract_to_annotation_backend():
    @transform
    def select_order(
        frame: Annotated[FakeDataFrame, Project(Order)],
    ) -> Annotated[FakeDataFrame, Strict(Order)]:
        return frame

    contract = select_order.__transform_spec__.input_contracts["frame"]

    assert contract.backend_name == "fake"  # type: ignore[attr-defined]
    assert select_order(FakeDataFrame(("extra", "order_id"))) == FakeDataFrame(
        ("order_id",)
    )


def test_pipeline_does_not_connect_different_dataframe_backends():
    @transform
    def fake_source() -> Annotated[FakeDataFrame, Project(Order)]:
        return FakeDataFrame(("order_id",))

    @transform
    def spark_sink(frame: Annotated[DataFrame, Project(Order)]) -> None:
        pass

    pipeline = Pipeline()
    source = pipeline.add_step(fake_source)
    sink = pipeline.add_step(spark_sink)

    with pytest.raises(PipelineConnectionError, match="No compatible contract"):
        pipeline.connect(source, sink)
