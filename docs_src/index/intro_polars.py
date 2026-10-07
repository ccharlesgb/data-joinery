from dataclasses import dataclass
from datetime import date
from typing import Annotated

import polars as pl

from data_joinery import Strict, transform


@dataclass
class Customer:
    snapshot_date: date
    customer_id: str
    name: str
    is_active: bool
    package: str


@dataclass
class CustomerMetrics:
    snapshot_date: date
    total_customer_count: int
    active_customer_count: int
    basic_package_customer_count: int
    pro_package_customer_count: int


@transform
def get_metrics(
    fact_table: Annotated[pl.DataFrame, Strict(Customer)],
) -> Annotated[pl.DataFrame, Strict(CustomerMetrics)]: ...
