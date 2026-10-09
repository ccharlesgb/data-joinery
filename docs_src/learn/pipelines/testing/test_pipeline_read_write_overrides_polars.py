from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Context, Pipeline, Project, transform


@dataclass(frozen=True)
class Storage:
    input_table: str
    output_table: str


@dataclass(frozen=True)
class OrderPipelineContext:
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
    storage: Annotated[Storage, Context()],
) -> Annotated[pl.DataFrame, Project(Order)]:
    return pl.read_parquet(storage.input_table)


@transform
def calculate_totals(
    orders: Annotated[pl.DataFrame, Project(Order)],
) -> Annotated[pl.DataFrame, Project(OrderTotal)]:
    return orders.select("order_id", (pl.col("amount") * 2).alias("total"))


@transform
def write_totals(
    totals: Annotated[pl.DataFrame, Project(OrderTotal)],
    storage: Annotated[Storage, Context()],
) -> None:
    totals.write_parquet(storage.output_table)


def build_pipeline() -> Pipeline[OrderPipelineContext]:
    pipeline = Pipeline(OrderPipelineContext)
    read = pipeline.add_step(read_orders, name="read")
    calculate = pipeline.add_step(calculate_totals, name="calculate")
    write = pipeline.add_step(write_totals, name="write")
    read >> calculate >> write
    return pipeline


def test_order_pipeline_end_to_end():
    fixture_orders = pl.DataFrame({"order_id": [1, 2], "amount": [10, 25]})

    @transform
    def read_fixture() -> Annotated[pl.DataFrame, Project(Order)]:
        return fixture_orders

    @transform
    def capture_totals(
        totals: Annotated[pl.DataFrame, Project(OrderTotal)],
    ) -> None:
        pass

    result = build_pipeline().run(
        OrderPipelineContext(Storage("unused", "unused")),
        transform_overrides={
            "read": read_fixture,
            "write": capture_totals,
        },
    )

    written = result.get_one_input("write", pl.DataFrame)
    assert written.to_dicts() == [
        {"order_id": 1, "total": 20},
        {"order_id": 2, "total": 50},
    ]
