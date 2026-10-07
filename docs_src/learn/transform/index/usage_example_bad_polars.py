import traceback
from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Schema, Strict, transform
from data_joinery.schema_types import SchemaCoercionError


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
    return customers.select(pl.len().alias("count"))


customer_schema = Schema(Customer)

customers = customer_schema.create_dataframe(
    [
        Customer("1", "Alice", True),
        Customer("2", "Bob", False),
        Customer("3", "Charlie", True),
    ],
    pl.DataFrame,
)
try:
    get_customer_count(filter_active_customers(customers))
except SchemaCoercionError:
    print(traceback.format_exc(limit=1))
