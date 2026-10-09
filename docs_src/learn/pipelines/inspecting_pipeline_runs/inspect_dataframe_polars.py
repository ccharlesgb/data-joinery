from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Pipeline, Project, transform


@dataclass
class Order:
    amount: int


@dataclass
class OrderTotal:
    total: int


@transform
def read_orders() -> Annotated[pl.DataFrame, Project(Order)]:
    return pl.DataFrame({"amount": [10, 20]})


@transform
def total_orders(
    orders: Annotated[pl.DataFrame, Project(Order)],
) -> Annotated[pl.DataFrame, Project(OrderTotal)]:
    return orders.select(pl.col("amount").sum().alias("total"))


pipeline = Pipeline()
read_step = pipeline.add_step(read_orders)
total_step = pipeline.add_step(total_orders)
read_step >> total_step

result = pipeline.run()
print("Orders:", result.get_output(read_step).to_dicts())
print("Total:", result.get_output("total_orders", pl.DataFrame).to_dicts())
