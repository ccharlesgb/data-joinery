from dataclasses import dataclass

import polars as pl

from data_joinery import Schema


@dataclass
class Customer:
    customer_id: str
    name: str
    is_active: bool


rows = [
    Customer("1", "Alice", True),
    Customer("2", "Bob", False),
    Customer("3", "Charlie", True),
]

schema = Schema(Customer)
df = schema.create_dataframe(rows, pl.DataFrame)
print(df)
