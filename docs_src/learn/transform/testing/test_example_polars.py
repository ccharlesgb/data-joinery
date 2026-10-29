from typing import Annotated

import polars as pl
from polars.testing import assert_frame_equal

from data_joinery import Schema, Strict, transform
from data_joinery.schemas.joinery_model import Column, JoineryModel


class Customer(JoineryModel):
    customer_id: Column[str]
    name: Column[str]
    is_active: Column[bool]


@transform
def filter_active_customers(
    customers: Annotated[pl.LazyFrame, Strict(Customer)],
) -> Annotated[pl.LazyFrame, Strict(Customer)]:
    return customers.filter(pl.col(Customer.is_active))


def test_filter_active_customers():
    customer_schema = Schema(Customer)

    customers = customer_schema.create_dataframe(
        [
            Customer(customer_id="1", name="Alice", is_active=True),
            Customer(customer_id="2", name="Bob", is_active=False),
            Customer(customer_id="3", name="Charlie", is_active=True),
        ],
        pl.LazyFrame,
    )
    expected_active_customers = customer_schema.create_dataframe(
        [
            Customer(customer_id="1", name="Alice", is_active=True),
            Customer(customer_id="3", name="Charlie", is_active=True),
        ],
        pl.LazyFrame,
    )

    active_customers = filter_active_customers(customers)
    assert_frame_equal(active_customers.collect(), expected_active_customers.collect())
