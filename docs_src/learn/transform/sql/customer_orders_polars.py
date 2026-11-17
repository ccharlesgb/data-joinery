from typing import Annotated

import polars as pl

from data_joinery import Column, JoineryModel, Strict, transform


class Order(JoineryModel):
    """An order and the customer who placed it."""

    order_id: Column[str]
    customer_id: Column[str]


class Customer(JoineryModel):
    """A customer and their display name."""

    customer_id: Column[str]
    name: Column[str]


class CustomerOrder(JoineryModel):
    """An order with its customer's name."""

    order_id: Column[str]
    customer_name: Column[str]


@transform
def customer_orders(
    orders: Annotated[pl.LazyFrame, Strict(Order)],
    customers: Annotated[pl.LazyFrame, Strict(Customer)],
) -> Annotated[pl.LazyFrame, Strict(CustomerOrder)]:
    """Look up the customer name for each matching order."""
    ctx = pl.SQLContext(orders=orders, customers=customers)
    return ctx.execute(
        """
        SELECT o.order_id, c.name AS customer_name
        FROM orders AS o
        JOIN customers AS c ON o.customer_id = c.customer_id
        ORDER BY o.order_id
        """,
    )


orders = pl.LazyFrame({"order_id": ["A", "B"], "customer_id": ["2", "1"]})
customers = pl.LazyFrame({"customer_id": ["1", "2"], "name": ["Alice", "Bob"]})

result = customer_orders(orders, customers)
print(result.collect())
