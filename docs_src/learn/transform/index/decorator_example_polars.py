from typing import Annotated

import polars as pl

from data_joinery import Project, Strict, transform
from data_joinery.schemas import Schema
from data_joinery.schemas.joinery_model import Column, JoineryModel


class Customer(JoineryModel):
    customer_id: Column[str]
    name: Column[str]
    is_active: Column[bool]


@transform
def filter_active_customers(
    customers: Annotated[pl.LazyFrame, Project(Customer)],
) -> Annotated[pl.LazyFrame, Strict(Customer)]:
    return customers.filter(pl.col(Customer.is_active))


customers = Schema(Customer).create_dataframe(
    [
        Customer(customer_id="1", name="Alice", is_active=True),
        Customer(customer_id="2", name="Bob", is_active=False),
        Customer(customer_id="3", name="Charlie", is_active=True),
    ],
    pl.LazyFrame,
)

active_customers = filter_active_customers(customers)
print(active_customers.collect())
