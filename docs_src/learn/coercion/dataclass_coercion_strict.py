import traceback
from dataclasses import dataclass

from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructField, StructType

from data_joinery import Schema
from data_joinery.schema_types import SchemaCoercionError


@dataclass
class Customer:
    customer_id: str
    name: str


spark = SparkSession.builder.appName("OrderMetricsApp").getOrCreate()
df = spark.createDataFrame(
    [
        ("1", "Alice", "England"),
        ("2", "Bob", "France"),
    ],
    schema=StructType(
        [
            StructField("customer_id", StringType(), nullable=True),
            StructField("name", StringType(), nullable=True),
            StructField("country", StringType(), nullable=True),
        ]
    ),
)

try:
    Schema(Customer).coerce_dataframe(df, mode="strict")
except SchemaCoercionError:
    print(traceback.format_exc(limit=1))
