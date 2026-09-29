from dataclasses import dataclass

import polars as pl
from pyspark.sql.types import StructType

from data_joinery import Schema


@dataclass
class Location:
    latitude: float
    longitude: float


@dataclass
class Employee:
    name: str
    phone_number: str


@dataclass
class Customer:
    customer_id: str
    name: str
    employees: list[Employee]
    location: Location


schema = Schema(Customer)
print("PySpark:")
print(schema.native_schema(StructType).treeString())
print("Polars:")
print(schema.native_schema(pl.Schema))
