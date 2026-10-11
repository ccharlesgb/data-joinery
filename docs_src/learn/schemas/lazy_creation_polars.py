from dataclasses import dataclass

import polars as pl

from data_joinery import Schema


@dataclass
class Order:
    order_id: int


orders = Schema(Order).create_dataframe([Order(1), Order(2)], pl.LazyFrame)

print(type(orders).__name__)
print(orders.collect())
