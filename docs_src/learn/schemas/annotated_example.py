from dataclasses import dataclass
from typing import Annotated

from pyspark.sql.types import (
    ByteType,
    DoubleType,
    FloatType,
    IntegerType,
    LongType,
    ShortType,
    StructType,
)

from data_joinery import Schema


@dataclass
class AnnotatedSchema:
    my_byte: Annotated[int, ByteType()]
    my_short: Annotated[int, ShortType()]
    my_int: Annotated[int, IntegerType()]
    my_long: Annotated[int, LongType()]
    my_float: Annotated[float, FloatType()]
    my_double: Annotated[float, DoubleType()]


schema = Schema(AnnotatedSchema)
print(schema.native_schema(StructType).treeString())
