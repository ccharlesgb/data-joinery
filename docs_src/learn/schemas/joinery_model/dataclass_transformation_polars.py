from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Schema, Strict, transform


@dataclass
class Order:
    """Input columns for an order."""

    price: float
    quantity: int


@dataclass
class OrderTotal:
    """Output column for the order total."""

    total_price: float


@transform
def calculate_total(
    orders: Annotated[pl.LazyFrame, Strict(Order)],
) -> Annotated[pl.LazyFrame, Strict(OrderTotal)]:
    """Multiply each order's price by its quantity."""
    return orders.select((pl.col("price") * pl.col("quantity")).alias("total_price"))


orders = Schema(Order).create_dataframe(
    [Order(price=12.5, quantity=2)],
    pl.LazyFrame,
)

print(calculate_total(orders).collect())
