from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Schema


@dataclass
class AnnotatedSchema:
    number: int
    short_number: Annotated[int, pl.Int8]
    another_short_number: Annotated[int, pl.Int16]


schema = Schema(AnnotatedSchema)
print(schema.native_schema(pl.Schema))
