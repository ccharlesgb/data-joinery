from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Schema, Strict, transform


@dataclass
class Customer:
    customer_id: str
    name: str
    is_active: bool


@transform
def filter_active_customers(
    customers: Annotated[pl.DataFrame, Strict(Customer)],
) -> Annotated[pl.DataFrame, Strict(Customer)]:
    return customers.filter(pl.col("is_active"))


def test_filter_active_customers():
    customer_schema = Schema(Customer)

    customers = customer_schema.create_dataframe(
        [
            Customer("1", "Alice", True),
            Customer("2", "Bob", False),
            Customer("3", "Charlie", True),
        ],
        pl.DataFrame,
    )
    expected_active_customers = customer_schema.create_dataframe(
        [
            Customer("1", "Alice", True),
            Customer("3", "Charlie", True),
        ],
        pl.DataFrame,
    )

    active_customers = filter_active_customers(customers)
    assert active_customers.equals(expected_active_customers)
