from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Project, Strict, transform
from data_joinery.schemas import Schema


@dataclass
class Customer:
    customer_id: str
    name: str
    is_active: bool


@transform
def filter_active_customers(
    customers: Annotated[pl.DataFrame, Project(Customer)],
) -> Annotated[pl.DataFrame, Strict(Customer)]:
    return customers.filter(pl.col("is_active"))


customers = Schema(Customer).create_dataframe(
    [
        Customer(customer_id="1", name="Alice", is_active=True),
        Customer(customer_id="2", name="Bob", is_active=False),
        Customer(customer_id="3", name="Charlie", is_active=True),
    ],
    pl.DataFrame,
)

active_customers = filter_active_customers(customers)
print(active_customers)
