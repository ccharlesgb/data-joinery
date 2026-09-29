from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated

from pyspark.sql.types import DecimalType, StructType

from data_joinery import Schema


@dataclass
class Customer:
    customer_id: str
    name: str
    is_active: bool
    discount_rate: float
    max_billing_amount: Annotated[Decimal, DecimalType(precision=10, scale=2)]


schema = Schema(Customer)
print(schema.native_schema(StructType).treeString())
