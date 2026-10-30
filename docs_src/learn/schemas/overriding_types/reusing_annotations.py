from typing import Annotated

import polars as pl

from data_joinery import Column, JoineryModel, Schema

SmallInt = Annotated[int, pl.Int16]


class Example(JoineryModel):
    """Use a shared type override for multiple fields."""

    first: Column[SmallInt]
    second: Column[SmallInt]


schema = Schema(Example)
print(schema.native_schema(pl.Schema))
