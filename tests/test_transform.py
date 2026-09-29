from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated

import pytest
from pyspark.sql import DataFrame, SparkSession, types

from data_joinery import (
    Project,
    ProjectCast,
    Schema,
    Strict,
    schemas,
)
from data_joinery.contract import DataFrameContract, InstanceContract, VoidContract
from data_joinery.dependencies import Context
from data_joinery.transform import (
    Transform,
    TransformSpec,
    _inspect_transform,
    transform,
)


@dataclass
class Order:
    order_id: int


@dataclass(frozen=True)
class PathConfig:
    value: str


@pytest.fixture(scope="session")
def spark() -> Generator[SparkSession, None, None]:
    spark = SparkSession.builder.master("local[*]").getOrCreate()
    yield spark
    spark.stop()


def test_inspect_transform_collects_context_parameters():
    def read_orders(
        spark: Annotated[SparkSession, Context()],
        path: Annotated[PathConfig, Context()],
    ) -> Annotated[DataFrame, Order]:
        raise AssertionError

    spec = _inspect_transform(read_orders)

    assert set(spec.context_parameters) == {"spark", "path"}
    declared_type, marker = spec.context_parameters["path"]
    assert declared_type is PathConfig
    assert isinstance(marker, Context)


def test_inspect_transform_context_parameter_not_treated_as_dataframe_input():
    def filter_orders(
        orders: Annotated[DataFrame, Project(Order)],
        path: Annotated[PathConfig, Context()],
    ) -> Annotated[DataFrame, Order]:
        raise AssertionError

    spec = _inspect_transform(filter_orders)

    assert set(spec.input_contracts) == {"orders"}
    assert isinstance(spec.input_contracts["orders"], DataFrameContract)
    assert spec.input_contracts["orders"].schema.model is Order
    assert set(spec.context_parameters) == {"path"}


def test_inspect_transform_collects_spark_as_context_parameter():
    def read_orders(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Order]:
        raise AssertionError

    spec = _inspect_transform(read_orders)

    assert set(spec.context_parameters) == {"spark"}
    declared_type, marker = spec.context_parameters["spark"]
    assert declared_type is SparkSession
    assert isinstance(marker, Context)


def test_transform_accepts_matching_input_and_output_schemas(spark: SparkSession):
    @dataclass
    class InputRow:
        field1: int
        field2: str

    @dataclass
    class OutputRow:
        field1: int

    input_schema = Schema(InputRow).native_schema(types.StructType)
    output_schema = Schema(OutputRow).native_schema(types.StructType)
    input_df = spark.createDataFrame([(1, "a")], input_schema)

    @transform
    def my_function(
        input1: Annotated[DataFrame, InputRow],
    ) -> Annotated[DataFrame, OutputRow]:
        return input1.select("field1")

    result = my_function(input_df)
    assert result.schema == output_schema


def test_transform_retains_inspected_specification():
    @dataclass
    class InputRow:
        field1: int

    @transform
    def my_function(input1: Annotated[DataFrame, Project(InputRow)]):
        return input1

    expected_spec = TransformSpec(
        input_contracts={
            "input1": DataFrameContract(
                schema=Schema(InputRow),
                coercion_mode="project",
                backend_name="spark",
                dataframe_type=DataFrame,
            )
        },
        output_contract=VoidContract(),
        context_parameters={},
    )

    assert isinstance(my_function, Transform)
    assert my_function.__transform_spec__ == expected_spec


def test_transform_rejects_value_returned_without_an_output_contract():
    @transform
    def write_path() -> None:
        return "unexpected"  # type: ignore[return-value]

    with pytest.raises(TypeError, match="Return value from 'write_path' must be None"):
        write_path()


def test_transform_treats_missing_return_annotation_as_void():
    @transform
    def write_path():
        return "unexpected"

    with pytest.raises(TypeError, match="Return value from 'write_path' must be None"):
        write_path()


def test_inspect_transform_uses_instance_contracts_for_python_values():
    def get_path(config: PathConfig) -> str:
        return config.value

    spec = _inspect_transform(get_path)

    assert spec.input_contracts == {"config": InstanceContract(PathConfig)}
    assert spec.output_contract == InstanceContract(str)


def test_transform_rejects_generic_instance_parameter():
    with pytest.raises(
        TypeError,
        match=(
            r"InstanceContract requires an unsubscripted runtime class, "
            r"got list\[str\]"
        ),
    ):

        @transform
        def count_paths(paths: list[str]) -> int:
            return len(paths)


def test_transform_rejects_generic_instance_return_type():
    with pytest.raises(
        TypeError,
        match=(
            r"InstanceContract requires an unsubscripted runtime class, "
            r"got list\[str\]"
        ),
    ):

        @transform
        def get_paths() -> list[str]:
            return []


def test_transform_accepts_unsubscripted_runtime_container_class():
    @transform
    def count_paths(paths: list) -> int:
        return len(paths)

    assert count_paths(["one", "two"]) == 2


def test_transform_validates_instances_through_contract_interface():
    @transform
    def get_path(config: PathConfig) -> str:
        return config.value

    assert get_path(PathConfig("users")) == "users"

    with pytest.raises(TypeError, match="Parameter 'config' must be a PathConfig"):
        get_path("users")  # type: ignore[arg-type]


def test_transform_validates_returned_instances_through_contract_interface():
    @transform
    def get_path() -> PathConfig:
        return "users"  # type: ignore[return-value]

    with pytest.raises(
        TypeError, match="Return value from 'get_path' must be a PathConfig"
    ):
        get_path()


def test_transform_raises_for_input_schema_mismatch(spark: SparkSession):
    @dataclass
    class InputRow:
        field1: int
        field2: str

    bad_input_df = spark.createDataFrame(
        [(1,)],
        types.StructType([types.StructField("field1", types.LongType(), False)]),
    )

    @transform
    def my_function(input1: Annotated[DataFrame, Project(InputRow)]):
        return input1

    with pytest.raises(schemas.SchemaCoercionError) as error:
        my_function(bad_input_df)

    assert [
        (violation.kind, violation.path) for violation in error.value.violations
    ] == [("missing", "field2")]


def test_transform_raises_for_output_schema_mismatch(spark: SparkSession):
    @dataclass
    class InputRow:
        field1: int
        field2: str

    @dataclass
    class OutputRow:
        field1: int

    input_df = Schema(InputRow).create_dataframe(
        [InputRow(1, "a")], DataFrame, session=spark
    )

    @transform
    def my_function(
        input1: Annotated[DataFrame, InputRow],
    ) -> Annotated[DataFrame, Strict(OutputRow)]:
        return input1

    with pytest.raises(schemas.SchemaCoercionError) as error:
        my_function(input_df)

    assert [
        (violation.kind, violation.path) for violation in error.value.violations
    ] == [("additional", "field2")]


def test_transform_can_disable_output_validation(spark: SparkSession):
    @dataclass
    class InputRow:
        field1: int

    @dataclass
    class OutputRow:
        field1: int

    input_df = Schema(InputRow).create_dataframe(
        [InputRow(1)], DataFrame, session=spark
    )

    @transform
    def my_function(
        input1: Annotated[DataFrame, InputRow],
    ) -> Annotated[DataFrame, OutputRow]:
        return "not a dataframe"  # type: ignore

    assert my_function(input_df) == "not a dataframe"


def test_transform_project_drops_extra_output_columns(
    spark: SparkSession,
):
    @dataclass
    class InputRow:
        field1: int
        field2: str

    @dataclass
    class OutputRow:
        field1: int

    input_df = Schema(InputRow).create_dataframe(
        [InputRow(1, "a")], DataFrame, session=spark
    )

    @transform
    def my_function(
        input1: Annotated[DataFrame, Project(InputRow)],
    ) -> Annotated[DataFrame, Project(OutputRow)]:
        return input1

    result = my_function(input_df)
    assert result.columns == ["field1"]


def test_transform_strict_makes_input_nullable(spark: SparkSession):
    @dataclass
    class InputRow:
        field1: int

    bad_input_df = spark.createDataFrame(
        [(1,)],
        types.StructType([types.StructField("field1", types.LongType(), False)]),
    )

    @transform
    def my_function(input1: Annotated[DataFrame, Strict(InputRow)]) -> DataFrame:
        assert input1.schema["field1"].nullable
        return input1

    assert my_function(bad_input_df).schema["field1"].nullable


def test_transform_project_cast_mode_casts_input_dataframe(spark: SparkSession):
    @dataclass
    class InputRow:
        field1: int

    input_df = spark.createDataFrame(
        [(1.9,)],
        types.StructType([types.StructField("field1", types.DoubleType(), True)]),
    )

    @transform
    def my_function(
        input1: Annotated[DataFrame, ProjectCast(InputRow)],
    ) -> Annotated[DataFrame, Project(InputRow)]:
        return input1

    result = my_function(input_df)
    assert result.schema["field1"].dataType == types.LongType()
    assert result.collect() == [types.Row(field1=1)]
