from dataclasses import dataclass
from typing import Annotated

import polars as pl
from pyspark.sql.types import ShortType, StructType

from data_joinery import Schema


@dataclass
class AnnotatedSchema:
    number: int
    short_number_spark: Annotated[int, ShortType()]
    short_number_polars: Annotated[int, pl.Int8]
    short_number_both: Annotated[int, ShortType(), pl.Int8]


schema = Schema(AnnotatedSchema)
print("PySpark:")
print(schema.native_schema(StructType).treeString())
print("Polars:")
print(schema.native_schema(pl.Schema))
