from typing import Annotated

import polars as pl

from data_joinery import BaseModel, Column, Schema, Strict, transform


class Customer(BaseModel):
    customer_id: Column[str]
    name: Column[str]
    is_active: Column[bool]


class CustomerCount(BaseModel):
    customer_count: Column[int]


@transform
def filter_active_customers(
    customers: Annotated[pl.LazyFrame, Strict(Customer)],
) -> Annotated[pl.LazyFrame, Strict(Customer)]:
    return customers.filter(pl.col(Customer.is_active))


@transform
def get_customer_count(
    customers: Annotated[pl.LazyFrame, Strict(Customer)],
) -> Annotated[pl.LazyFrame, Strict(CustomerCount)]:
    return customers.select(pl.len().cast(pl.Int64).alias(CustomerCount.customer_count))


customer_schema = Schema(Customer)

customers = customer_schema.create_dataframe(
    [
        Customer(customer_id="1", name="Alice", is_active=True),
        Customer(customer_id="2", name="Bob", is_active=False),
        Customer(customer_id="3", name="Charlie", is_active=True),
    ],
    pl.LazyFrame,
)

active_customer_count = get_customer_count(filter_active_customers(customers))
print(active_customer_count.collect())
