from dataclasses import dataclass
from typing import Annotated

import polars as pl
from polars.testing import assert_frame_equal

from data_joinery import Pipeline, Project, transform


@dataclass
class Order:
    order_id: int


@transform
def read_orders() -> Annotated[pl.LazyFrame, Project(Order)]:
    return pl.LazyFrame({"order_id": [1, 2]})


@transform
def write_orders(orders: Annotated[pl.LazyFrame, Project(Order)]) -> None:
    pass


def test_writer_input():
    pipeline = Pipeline()
    read = pipeline.add_step(read_orders)
    write = pipeline.add_step(write_orders)
    read >> write

    result = pipeline.run()
    actual = result.get_one_input(write, pl.LazyFrame)
    expected = pl.LazyFrame({"order_id": [1, 2]})
    assert_frame_equal(actual.collect(), expected.collect())
