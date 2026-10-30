import polars as pl

from data_joinery import Column, JoineryModel, Schema, column


class Order(JoineryModel):
    price: Column[float]
    quantity: Column[int] = column(default=0)
    extras: Column[list[str]] = column(default_factory=list)


df = Schema(Order).create_dataframe(
    [Order(price=27.0), Order(price=10.0, quantity=5)], pl.DataFrame
)
print(df)
