import polars as pl

from data_joinery import Schema
from data_joinery.schemas.joinery_model import Column, JoineryModel


class Location(JoineryModel):
    latitude: Column[float]
    longitude: Column[float]


class Employee(JoineryModel):
    name: Column[str]
    phone_number: Column[str]


class Customer(JoineryModel):
    customer_id: Column[str]
    name: Column[str]
    employees: Column[list[Employee]]
    location: Column[Location]


schema = Schema(Customer)
print(schema.native_schema(pl.Schema))
