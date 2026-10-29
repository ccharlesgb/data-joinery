from typing import Annotated

import polars as pl

from data_joinery import Pipeline, Project, transform
from data_joinery.schemas.joinery_model import Column, JoineryModel


class Order(JoineryModel):
    order_id: Column[int]


@transform
def read_orders() -> Annotated[pl.LazyFrame, Project(Order)]:
    return pl.LazyFrame({Order.order_id: [1, 2]})


@transform
def write_orders(orders: Annotated[pl.LazyFrame, Project(Order)]) -> None:
    pass


pipeline = Pipeline()
read_step = pipeline.add_step(read_orders)
writer_step = pipeline.add_step(write_orders)
read_step >> writer_step

result = pipeline.run()
print("Read output:", result.get_output(read_step).collect().to_dicts())
print(
    "Passed to writer:",
    result.get_one_input("write_orders", pl.LazyFrame).collect().to_dicts(),
)
