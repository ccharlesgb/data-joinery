from dataclasses import dataclass
from typing import Annotated

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from data_joinery import Schema, Strict, transform


@dataclass
class Order:
    """Input columns for an order."""

    price: float
    quantity: int


@dataclass
class OrderTotal:
    """Output column for the order total."""

    total_price: float


@transform
def calculate_total(
    orders: Annotated[DataFrame, Strict(Order)],
) -> Annotated[DataFrame, Strict(OrderTotal)]:
    """Multiply each order's price by its quantity."""
    return orders.select((F.col("price") * F.col("quantity")).alias("total_price"))


spark = SparkSession.builder.getOrCreate()
orders = Schema(Order).create_dataframe(
    [Order(price=12.5, quantity=2)],
    DataFrame,
    session=spark,
)

calculate_total(orders).show()
