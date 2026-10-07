from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession

from data_joinery import Schema


@dataclass
class Customer:
    customer_id: str
    name: str
    is_active: bool


spark = SparkSession.builder.getOrCreate()

rows = [
    Customer("1", "Alice", True),
    Customer("2", "Bob", False),
    Customer("3", "Charlie", True),
]

schema = Schema(Customer)
df = schema.create_dataframe(rows, DataFrame, session=spark)
df.show()
