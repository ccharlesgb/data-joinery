from typing import Annotated

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from data_joinery import Schema, Strict, transform
from data_joinery.schemas.joinery_model import Column, JoineryModel, column


class Order(JoineryModel):
    """Input columns for an order."""

    price: Column[float]
    quantity: Column[int]


class OrderTotal(JoineryModel):
    """Output column for the order total."""

    total_price: Column[float] = column(name="Total Price")


@transform
def calculate_total(
    orders: Annotated[DataFrame, Strict(Order)],
) -> Annotated[DataFrame, Strict(OrderTotal)]:
    """Multiply each order's price by its quantity."""
    return orders.select(
        (F.col(Order.price) * F.col(Order.quantity)).alias(OrderTotal.total_price)
    )


spark = SparkSession.builder.getOrCreate()
orders = Schema(Order).create_dataframe(
    [Order(price=12.5, quantity=2)],
    DataFrame,
    session=spark,
)

calculate_total(orders).show()
