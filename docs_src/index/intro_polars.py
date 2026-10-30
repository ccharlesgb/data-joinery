from datetime import date
from typing import Annotated

import polars as pl

from data_joinery import Column, JoineryModel, Strict, transform


class Customer(JoineryModel):
    snapshot_date: Column[date]
    customer_id: Column[str]
    name: Column[str]
    is_active: Column[bool]
    package: Column[str]


class CustomerMetrics(JoineryModel):
    snapshot_date: Column[date]
    total_customer_count: Column[int]
    active_customer_count: Column[int]
    basic_package_customer_count: Column[int]
    pro_package_customer_count: Column[int]


@transform
def get_metrics(
    fact_table: Annotated[pl.LazyFrame, Strict(Customer)],
) -> Annotated[pl.LazyFrame, Strict(CustomerMetrics)]: ...
