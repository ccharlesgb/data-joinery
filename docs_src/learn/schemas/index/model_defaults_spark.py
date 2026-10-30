from pyspark.sql import DataFrame, SparkSession

from data_joinery import Column, JoineryModel, Schema, column

spark = SparkSession.builder.getOrCreate()


class Order(JoineryModel):
    price: Column[float]
    quantity: Column[int] = column(default=0)
    extras: Column[list[str]] = column(default_factory=list)


df = Schema(Order).create_dataframe(
    [Order(price=27.0), Order(price=10.0, quantity=5)], DataFrame, session=spark
)
print(df)
