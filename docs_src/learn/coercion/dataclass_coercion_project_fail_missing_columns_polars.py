import traceback
from dataclasses import dataclass

import polars as pl

from data_joinery import Schema
from data_joinery.schema_types import SchemaCoercionError


@dataclass
class SubModel:
    subfield1: str
    subfield2: str


@dataclass
class Model:
    field1: str
    field2: str
    sub_schema: SubModel


schema = Schema(Model)


@dataclass
class ModelWithMissingColumn:
    field1: str
    sub_schema: SubModel


input_schema = Schema(ModelWithMissingColumn)


input_df = input_schema.create_dataframe(
    [
        ModelWithMissingColumn(
            field1="value1",
            sub_schema=SubModel(subfield1="subvalue1", subfield2="subvalue2"),
        )
    ],
    pl.DataFrame,
)

try:
    schema.coerce_dataframe(input_df, mode="project")
except SchemaCoercionError:
    print(traceback.format_exc(limit=1))
