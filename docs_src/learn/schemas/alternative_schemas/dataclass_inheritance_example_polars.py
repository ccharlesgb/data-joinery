from dataclasses import dataclass

import polars as pl

from data_joinery import Schema


@dataclass(kw_only=True)
class AddressMixin:
    number: str
    street: str
    postal_code: str


@dataclass(kw_only=True)
class Customer(AddressMixin):
    customer_id: str
    name: str


schema = Schema(Customer)
print(schema.native_schema(pl.Schema))
