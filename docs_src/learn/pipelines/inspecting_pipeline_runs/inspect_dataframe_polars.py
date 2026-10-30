from typing import Annotated

import polars as pl

from data_joinery import Column, JoineryModel, Pipeline, Project, transform


class Order(JoineryModel):
    amount: Column[int]


class OrderTotal(JoineryModel):
    total: Column[int]


@transform
def read_orders() -> Annotated[pl.LazyFrame, Project(Order)]:
    return pl.LazyFrame({Order.amount: [10, 20]})


@transform
def total_orders(
    orders: Annotated[pl.LazyFrame, Project(Order)],
) -> Annotated[pl.LazyFrame, Project(OrderTotal)]:
    return orders.select(pl.col(Order.amount).sum().alias(OrderTotal.total))


pipeline = Pipeline()
read_step = pipeline.add_step(read_orders)
total_step = pipeline.add_step(total_orders)
read_step >> total_step

result = pipeline.run()
print("Orders:", result.get_output(read_step).collect().to_dicts())
print("Total:", result.get_output("total_orders", pl.LazyFrame).collect().to_dicts())
