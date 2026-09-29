from dataclasses import dataclass

import polars as pl
from pyspark.sql.types import StructType

from data_joinery import Schema


@dataclass
class Customer:
    customer_id: str
    name: str
    is_active: bool
    discount_rate: float


schema = Schema(Customer)
print("PySpark:")
print(schema.native_schema(StructType).treeString())
print("Polars:")
print(schema.native_schema(pl.Schema))
