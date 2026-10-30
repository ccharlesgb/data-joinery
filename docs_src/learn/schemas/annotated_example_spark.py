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

from data_joinery import Column, JoineryModel, Schema


class AnnotatedSchema(JoineryModel):
    my_byte: Column[Annotated[int, ByteType()]]
    my_short: Column[Annotated[int, ShortType()]]
    my_int: Column[Annotated[int, IntegerType()]]
    my_long: Column[Annotated[int, LongType()]]
    my_float: Column[Annotated[float, FloatType()]]
    my_double: Column[Annotated[float, DoubleType()]]


schema = Schema(AnnotatedSchema)
print(schema.native_schema(StructType).treeString())
