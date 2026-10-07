from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Schema, Strict, transform


@dataclass
class Customer:
    customer_id: str
    name: str
    is_active: bool


@dataclass
class CustomerCount:
    customer_count: int


@transform
def filter_active_customers(
    customers: Annotated[pl.DataFrame, Strict(Customer)],
) -> Annotated[pl.DataFrame, Strict(Customer)]:
    return customers.filter(pl.col("is_active"))


@transform
def get_customer_count(
    customers: Annotated[pl.DataFrame, Strict(Customer)],
) -> Annotated[pl.DataFrame, Strict(CustomerCount)]:
    return customers.select(pl.len().cast(pl.Int64).alias("customer_count"))


customer_schema = Schema(Customer)

customers = customer_schema.create_dataframe(
    [
        Customer("1", "Alice", True),
        Customer("2", "Bob", False),
        Customer("3", "Charlie", True),
    ],
    pl.DataFrame,
)

active_customer_count = get_customer_count(filter_active_customers(customers))
print(active_customer_count)
