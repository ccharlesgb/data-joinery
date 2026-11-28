"""Join orders to customers and print the order report."""

from dataclasses import dataclass
from datetime import date
from typing import Annotated

import polars as pl

from data_joinery import (
    Column,
    Context,
    JoineryModel,
    Pipeline,
    Strict,
    side_effect,
    transform,
)


class OrderDate(date):
    """Date of the orders to include in the report."""


@dataclass(frozen=True)
class OrderPipelineContext:
    """Dependencies supplied when running the order pipeline."""

    order_date: OrderDate


class Orders(JoineryModel):
    """Orders and the customers who placed them."""

    order_id: Column[int]
    customer_id: Column[int]
    order_date: Column[date]


class Customers(JoineryModel):
    """Customer names keyed by customer ID."""

    customer_id: Column[int]
    name: Column[str]


class CustomerOrders(Orders):
    """Orders with the customer's name."""

    name: Column[str]


@transform
def read_orders(
    order_date: Annotated[OrderDate, Context()],
) -> Annotated[pl.LazyFrame, Strict(Orders)]:
    """Read the example orders for the requested date.

    Args:
        order_date: Date supplied by the pipeline context.

    Returns:
        Orders placed on the requested date.
    """
    orders = pl.LazyFrame(
        {
            Orders.order_id: [1, 2, 3],
            Orders.customer_id: [10, 20, 10],
            Orders.order_date: [date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 2)],
        }
    )
    return orders.filter(pl.col(Orders.order_date) == order_date)


@transform
def read_customers() -> Annotated[pl.LazyFrame, Strict(Customers)]:
    """Read the example customers."""
    return pl.LazyFrame(
        {Customers.customer_id: [10, 20], Customers.name: ["Ada", "Jo"]}
    )


@transform
def join_orders(
    orders: Annotated[pl.LazyFrame, Strict(Orders)],
    customers: Annotated[pl.LazyFrame, Strict(Customers)],
) -> Annotated[pl.LazyFrame, Strict(CustomerOrders)]:
    """Look up the customer name for each order."""
    return orders.join(customers, on=Orders.customer_id, how="left")


@side_effect
def print_orders(orders: Annotated[pl.LazyFrame, Strict(CustomerOrders)]) -> None:
    """Print the report in order ID sequence."""
    print(orders.sort(CustomerOrders.order_id).collect())


order_pipeline = Pipeline(OrderPipelineContext)
orders = order_pipeline.add_step(read_orders, "read orders")
customers = order_pipeline.add_step(read_customers, "read customers")
joined = order_pipeline.add_step(join_orders, "join orders")
report = order_pipeline.add_step(print_orders, "print orders")

order_pipeline.connect(orders, joined, param="orders")
order_pipeline.connect(customers, joined, param="customers")
order_pipeline.connect(joined, report)

order_pipeline.run(OrderPipelineContext(order_date=OrderDate(2026, 1, 1)))
