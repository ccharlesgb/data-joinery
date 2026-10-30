import polars as pl

from data_joinery import Column, JoineryModel, column


class Order(JoineryModel):
    price: Column[float]
    quantity: Column[int]


class OrderTotal(JoineryModel):
    total_price: Column[float] = column(name="Total Price")


orders = pl.DataFrame(
    {Order.price: [12.5, 5.0], Order.quantity: [2, 1]},
)

totals = orders.select(
    (pl.col(Order.price) * pl.col(Order.quantity)).alias(OrderTotal.total_price)
).filter(pl.col(OrderTotal.total_price) > 20)

print(totals)
