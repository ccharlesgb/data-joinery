from typing import Annotated

from pyspark.sql.types import ShortType, StructType

from data_joinery import Schema
from data_joinery.schemas.joinery_model import Column, JoineryModel


class AnnotatedSchema(JoineryModel):
    number: Column[int]
    short_number: Column[Annotated[int, ShortType()]]
    another_short_number: Column[Annotated[int, ShortType()]]


schema = Schema(AnnotatedSchema)
print(schema.native_schema(StructType).treeString())
