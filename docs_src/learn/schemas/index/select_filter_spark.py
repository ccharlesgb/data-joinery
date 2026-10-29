from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from data_joinery.schemas.joinery_model import Column, JoineryModel, column


class Order(JoineryModel):
    price: Column[float]
    quantity: Column[int]


class OrderTotal(JoineryModel):
    total_price: Column[float] = column(name="Total Price")


spark = SparkSession.builder.getOrCreate()
orders = spark.createDataFrame(
    [(12.5, 2), (5.0, 1)],
    schema=[Order.price, Order.quantity],
)

totals = orders.select(
    (F.col(Order.price) * F.col(Order.quantity)).alias(OrderTotal.total_price)
).filter(F.col(OrderTotal.total_price) > 20)

totals.show()
