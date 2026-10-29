from typing import Annotated

import polars as pl

from data_joinery import Schema
from data_joinery.schemas.joinery_model import Column, JoineryModel


class AnnotatedSchema(JoineryModel):
    number: Column[int]
    short_number: Column[Annotated[int, pl.Int8]]
    another_short_number: Column[Annotated[int, pl.Int16]]


schema = Schema(AnnotatedSchema)
print(schema.native_schema(pl.Schema))
