from dataclasses import dataclass

import polars as pl

from data_joinery import Schema


@dataclass
class Order:
    order_id: int


source = pl.LazyFrame({"order_id": [1, 2], "extra": ["a", "b"]})
orders = Schema(Order).coerce_dataframe(source)

print(type(orders).__name__)
print(orders.filter(pl.col("order_id") > 1).collect())
