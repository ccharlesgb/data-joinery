from dataclasses import dataclass
from typing import Annotated

import pytest
from pyspark.sql import DataFrame, SparkSession

from data_joinery import Context, Pipeline, Project, transform


@dataclass(frozen=True)
class Storage:
    input_table: str
    output_table: str


@dataclass(frozen=True)
class OrderPipelineContext:
    spark: SparkSession
    storage: Storage


@dataclass
class Order:
    order_id: int
    amount: int


@dataclass
class OrderTotal:
    order_id: int
    total: int


@transform
def read_orders(
    spark: Annotated[SparkSession, Context()],
    storage: Annotated[Storage, Context()],
) -> Annotated[DataFrame, Project(Order)]:
    return spark.table(storage.input_table)


@transform
def calculate_totals(
    orders: Annotated[DataFrame, Project(Order)],
) -> Annotated[DataFrame, Project(OrderTotal)]:
    return orders.selectExpr("order_id", "amount * 2 AS total")


@transform
def write_totals(
    totals: Annotated[DataFrame, Project(OrderTotal)],
    storage: Annotated[Storage, Context()],
) -> None:
    totals.write.saveAsTable(storage.output_table)


def build_pipeline() -> Pipeline[OrderPipelineContext]:
    pipeline = Pipeline(OrderPipelineContext)
    read = pipeline.add_step(read_orders, name="read")
    calculate = pipeline.add_step(calculate_totals, name="calculate")
    write = pipeline.add_step(write_totals, name="write")
    read >> calculate >> write
    return pipeline


@pytest.fixture(scope="module")
def spark():
    session = SparkSession.builder.master("local[1]").getOrCreate()
    yield session
    session.stop()


def test_order_pipeline_end_to_end(spark: SparkSession):
    fixture_orders = spark.createDataFrame(
        [(1, 10), (2, 25)], "order_id BIGINT, amount BIGINT"
    )
    captured: list[tuple[int, int]] = []

    @transform
    def read_fixture() -> Annotated[DataFrame, Project(Order)]:
        return fixture_orders

    @transform
    def capture_totals(
        totals: Annotated[DataFrame, Project(OrderTotal)],
    ) -> None:
        captured.extend((row.order_id, row.total) for row in totals.collect())

    build_pipeline().run(
        OrderPipelineContext(spark, Storage("unused", "unused")),
        transform_overrides={
            "read": read_fixture,
            "write": capture_totals,
        },
    )

    assert captured == [(1, 20), (2, 50)]
