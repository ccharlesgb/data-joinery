from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Pipeline, Project, transform


@dataclass
class Order:
    order_id: int


@transform
def read_orders() -> Annotated[pl.DataFrame, Project(Order)]:
    return pl.DataFrame({"order_id": [1, 2]})


@transform
def write_orders(orders: Annotated[pl.DataFrame, Project(Order)]) -> None:
    pass


pipeline = Pipeline()
read_step = pipeline.add_step(read_orders)
writer_step = pipeline.add_step(write_orders)
read_step >> writer_step

result = pipeline.run()
print("Read output:", result.get_output(read_step).to_dicts())
print(
    "Passed to writer:",
    result.get_one_input("write_orders", pl.DataFrame).to_dicts(),
)
