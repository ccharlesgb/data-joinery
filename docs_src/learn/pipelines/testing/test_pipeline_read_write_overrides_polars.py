from dataclasses import dataclass
from typing import Annotated

import polars as pl
from polars.testing import assert_frame_equal

from data_joinery import Context, Pipeline, Project, transform
from data_joinery.schemas.joinery_model import Column, JoineryModel


@dataclass(frozen=True)
class Storage:
    input_table: str
    output_table: str


@dataclass(frozen=True)
class OrderPipelineContext:
    storage: Storage


class Order(JoineryModel):
    order_id: Column[int]
    amount: Column[int]


class OrderTotal(JoineryModel):
    order_id: Column[int]
    total: Column[int]


@transform
def read_orders(
    storage: Annotated[Storage, Context()],
) -> Annotated[pl.LazyFrame, Project(Order)]:
    return pl.scan_parquet(storage.input_table)


@transform
def calculate_totals(
    orders: Annotated[pl.LazyFrame, Project(Order)],
) -> Annotated[pl.LazyFrame, Project(OrderTotal)]:
    return orders.select(
        Order.order_id, (pl.col(Order.amount) * 2).alias(OrderTotal.total)
    )


@transform
def write_totals(
    totals: Annotated[pl.LazyFrame, Project(OrderTotal)],
    storage: Annotated[Storage, Context()],
) -> None:
    totals.sink_parquet(storage.output_table)


def build_pipeline() -> Pipeline[OrderPipelineContext]:
    pipeline = Pipeline(OrderPipelineContext)
    read = pipeline.add_step(read_orders, name="read")
    calculate = pipeline.add_step(calculate_totals, name="calculate")
    write = pipeline.add_step(write_totals, name="write")
    read >> calculate >> write
    return pipeline


def test_order_pipeline_end_to_end():
    fixture_orders = pl.LazyFrame({Order.order_id: [1, 2], Order.amount: [10, 25]})

    @transform
    def read_fixture() -> Annotated[pl.LazyFrame, Project(Order)]:
        return fixture_orders

    @transform
    def capture_totals(
        totals: Annotated[pl.LazyFrame, Project(OrderTotal)],
    ) -> None:
        pass

    result = build_pipeline().run(
        OrderPipelineContext(Storage("unused", "unused")),
        transform_overrides={
            "read": read_fixture,
            "write": capture_totals,
        },
    )

    written = result.get_one_input("write", pl.LazyFrame)
    expected = pl.LazyFrame({Order.order_id: [1, 2], OrderTotal.total: [20, 50]})
    assert_frame_equal(written.collect(), expected.collect())
