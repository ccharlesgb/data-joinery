from pyspark.sql.types import StructType

from data_joinery import Schema
from data_joinery.schemas.joinery_model import Column, JoineryModel


class Customer(JoineryModel):
    customer_id: Column[str]
    name: Column[str]
    is_active: Column[bool]
    discount_rate: Column[float]


schema = Schema(Customer)
print(schema.native_schema(StructType).treeString())
