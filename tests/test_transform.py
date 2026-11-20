from collections.abc import Generator
from dataclasses import dataclass
from functools import partial
from typing import Annotated

import pytest
from polars import DataFrame as PolarsDataFrame
from pyspark.sql import DataFrame, SparkSession, types

from data_joinery import (
    Column,
    JoineryModel,
    Project,
    ProjectCast,
    Schema,
    Strict,
    schemas,
)
from data_joinery.context import Context
from data_joinery.contract import DataFrameContract, InstanceContract, VoidContract
from data_joinery.transform import (
    Transform,
    TransformSpec,
    _inspect_transform,
    side_effect,
    transform,
)


class Order(JoineryModel):
    order_id: Column[int]


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
    ) -> DataFrame:
        raise AssertionError

    spec = _inspect_transform(read_orders)

    assert set(spec.context_parameters) == {"spark", "path"}
    declared_type, marker = spec.context_parameters["path"]
    assert declared_type is PathConfig
    assert isinstance(marker, Context)


def test_inspect_transform_context_parameter_not_treated_as_dataframe_input():
    def filter_orders(
        orders: Annotated[DataFrame, "orders to filter", Project(Order)],
        path: Annotated[PathConfig, Context()],
    ) -> DataFrame:
        raise AssertionError

    spec = _inspect_transform(filter_orders)

    assert set(spec.input_contracts) == {"orders"}
    assert isinstance(spec.input_contracts["orders"], DataFrameContract)
    assert spec.input_contracts["orders"].schema.model is Order
    assert set(spec.context_parameters) == {"path"}


def test_inspect_transform_collects_spark_as_context_parameter():
    def read_orders(
        spark: Annotated[SparkSession, Context()],
    ) -> DataFrame:
        raise AssertionError

    spec = _inspect_transform(read_orders)

    assert set(spec.context_parameters) == {"spark"}
    declared_type, marker = spec.context_parameters["spark"]
    assert declared_type is SparkSession
    assert isinstance(marker, Context)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        pytest.param(Strict(Order), Context(), id="strict-then-context"),
        pytest.param(Context(), Strict(Order), id="context-then-strict"),
        pytest.param(Strict(Order), Project(Order), id="two-dataframe-contracts"),
        pytest.param(Context(), Context(), id="two-context-markers"),
    ],
)
def test_transform_rejects_multiple_markers_on_one_parameter(
    first: DataFrameContract | Context, second: DataFrameContract | Context
):
    def consume_orders(orders: Annotated[DataFrame, first, second]) -> None:
        raise AssertionError

    with pytest.raises(
        TypeError,
        match="parameter 'orders': only one DataFrame contract or Context",
    ):
        transform(consume_orders)


def test_transform_rejects_multiple_markers_on_return():
    def read_orders() -> Annotated[DataFrame, Strict(Order), Project(Order)]:
        raise AssertionError

    with pytest.raises(
        TypeError,
        match="return annotation: only one DataFrame contract or Context",
    ):
        transform(read_orders)


def test_transform_rejects_context_marker_on_return():
    def get_path() -> Annotated[PathConfig, Context()]:
        raise AssertionError

    with pytest.raises(
        TypeError, match=r"return annotation: Context\(\) can only mark a parameter"
    ):
        transform(get_path)


def test_transform_passes_through_dataframe_with_descriptive_metadata():
    @transform
    def keep_frame(
        frame: Annotated[PolarsDataFrame, "input description"],
    ) -> Annotated[PolarsDataFrame, "output description"]:
        return frame

    frame = PolarsDataFrame({"field": [1]})

    assert keep_frame(frame) is frame


def test_transform_accepts_partial_with_copied_annotations():
    def add(left: int, right: int) -> int:
        return left + right

    add_one = partial(add, 1)
    add_one.__annotations__ = add.__annotations__.copy()

    assert transform(add_one)(2) == 3


def test_transform_retains_inspected_specification():
    class InputRow(JoineryModel):
        field1: Column[int]

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


def test_transform_marks_terminal_side_effect():
    @transform(side_effect=True)
    def write_path() -> None:
        pass

    assert write_path.side_effect is True


def test_side_effect_decorator_marks_transform():
    @side_effect
    def write_path() -> None:
        pass

    assert write_path.side_effect is True


def test_side_effect_decorator_requires_none_annotation():
    with pytest.raises(TypeError, match="must explicitly annotate its return as None"):

        @side_effect
        def write_path():
            pass


def test_transform_defaults_to_no_side_effect():
    @transform()
    def check_path() -> None:
        pass

    assert check_path.side_effect is False


def test_side_effect_transform_requires_explicit_none_annotation():
    with pytest.raises(TypeError, match="must explicitly annotate its return as None"):

        @transform(side_effect=True)
        def write_path():
            pass


def test_side_effect_transform_rejects_value_return_annotation():
    with pytest.raises(TypeError, match="must explicitly annotate its return as None"):

        @transform(side_effect=True)
        def write_path() -> str:
            return "path"


def test_side_effect_transform_rejects_returned_value():
    @transform(side_effect=True)
    def write_path() -> None:
        return "unexpected"  # type: ignore[return-value]

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
            r"Transform 'count_paths' parameter 'paths': InstanceContract requires "
            r"an unsubscripted runtime class, got list\[str\]"
        ),
    ):

        @transform
        def count_paths(paths: list[str]) -> int:
            return len(paths)


def test_transform_rejects_generic_instance_return_type():
    with pytest.raises(
        TypeError,
        match=(
            r"Transform 'get_paths' return annotation: InstanceContract requires "
            r"an unsubscripted runtime class, got list\[str\]"
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

    with pytest.raises(
        TypeError, match="parameter 'config' must be a PathConfig; got str"
    ):
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
    class InputRow(JoineryModel):
        field1: Column[int]
        field2: Column[str]

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
    class InputRow(JoineryModel):
        field1: Column[int]
        field2: Column[str]

    class OutputRow(JoineryModel):
        field1: Column[int]

    input_df = Schema(InputRow).create_dataframe(
        [InputRow(field1=1, field2="a")], DataFrame, session=spark
    )

    @transform
    def my_function(
        input1: DataFrame,
    ) -> Annotated[DataFrame, Strict(OutputRow)]:
        return input1

    with pytest.raises(schemas.SchemaCoercionError) as error:
        my_function(input_df)

    assert [
        (violation.kind, violation.path) for violation in error.value.violations
    ] == [("additional", "field2")]


def test_transform_rejects_invalid_input_with_descriptive_metadata():
    @transform
    def consume_frame(frame: Annotated[DataFrame, "input description"]) -> None:
        raise AssertionError("Invalid input should be rejected before the call")

    with pytest.raises(
        TypeError, match="parameter 'frame' must be a DataFrame; got int"
    ):
        consume_frame(7)  # type: ignore[arg-type]


def test_transform_rejects_invalid_output_with_descriptive_metadata():
    @transform
    def produce_frame() -> Annotated[DataFrame, "output description"]:
        return 42  # type: ignore[return-value]

    with pytest.raises(
        TypeError,
        match="Return value from 'produce_frame' must be a DataFrame; got int",
    ):
        produce_frame()


def test_transform_project_drops_extra_output_columns(
    spark: SparkSession,
):
    class InputRow(JoineryModel):
        field1: Column[int]
        field2: Column[str]

    class OutputRow(JoineryModel):
        field1: Column[int]

    input_df = Schema(InputRow).create_dataframe(
        [InputRow(field1=1, field2="a")], DataFrame, session=spark
    )

    @transform
    def my_function(
        input1: Annotated[DataFrame, Project(InputRow)],
    ) -> Annotated[DataFrame, Project(OutputRow)]:
        return input1

    result = my_function(input_df)
    assert result.columns == ["field1"]


def test_transform_strict_makes_input_nullable(spark: SparkSession):
    class InputRow(JoineryModel):
        field1: Column[int]

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
    class InputRow(JoineryModel):
        field1: Column[int]

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
