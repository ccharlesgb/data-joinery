import polars as pl
from pydantic import BaseModel, Field
from pyspark.sql.types import StructType

from data_joinery import Schema


class Customer(BaseModel):
    customer_id: str
    name: str
    is_active: bool
    discount_rate: float = Field(default=0.0, ge=0.0, le=1.0)


schema = Schema(Customer)
print("PySpark:")
print(schema.native_schema(StructType).treeString())
print("Polars:")
print(schema.native_schema(pl.Schema))
