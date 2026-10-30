import polars as pl

from data_joinery import Column, JoineryModel, Schema


class Customer(JoineryModel):
    customer_id: Column[str]
    name: Column[str]
    is_active: Column[bool]


rows = [
    Customer(customer_id="1", name="Alice", is_active=True),
    Customer(customer_id="2", name="Bob", is_active=False),
    Customer(customer_id="3", name="Charlie", is_active=True),
]

schema = Schema(Customer)
df = schema.create_dataframe(rows, pl.LazyFrame)
print(df.collect())
