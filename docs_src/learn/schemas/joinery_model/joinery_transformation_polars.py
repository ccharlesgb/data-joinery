from typing import Annotated

import polars as pl

from data_joinery import Schema, Strict, transform
from data_joinery.schemas.joinery_model import Column, JoineryModel, column


class Order(JoineryModel):
    """Input columns for an order."""

    price: Column[float]
    quantity: Column[int]


class OrderTotal(JoineryModel):
    """Output column for the order total."""

    total_price: Column[float] = column(name="Total Price")


@transform
def calculate_total(
    orders: Annotated[pl.LazyFrame, Strict(Order)],
) -> Annotated[pl.LazyFrame, Strict(OrderTotal)]:
    """Multiply each order's price by its quantity."""
    return orders.select(
        (pl.col(Order.price) * pl.col(Order.quantity)).alias(OrderTotal.total_price)
    )


orders = Schema(Order).create_dataframe(
    [Order(price=12.5, quantity=2)],
    pl.LazyFrame,
)

print(calculate_total(orders).collect())
