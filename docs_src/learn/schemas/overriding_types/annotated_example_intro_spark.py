from dataclasses import dataclass
from typing import Annotated

from pyspark.sql.types import ShortType, StructType

from data_joinery import Schema


@dataclass
class AnnotatedSchema:
    number: int
    short_number: Annotated[int, ShortType()]
    another_short_number: Annotated[int, ShortType()]


schema = Schema(AnnotatedSchema)
print(schema.native_schema(StructType).treeString())
