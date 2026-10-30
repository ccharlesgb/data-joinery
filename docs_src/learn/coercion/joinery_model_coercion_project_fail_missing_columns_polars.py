import traceback

import polars as pl

from data_joinery import Column, JoineryModel, Schema, SchemaCoercionError


class SubModel(JoineryModel):
    subfield1: Column[str]
    subfield2: Column[str]


class Model(JoineryModel):
    field1: Column[str]
    field2: Column[str]
    sub_schema: Column[SubModel]


schema = Schema(Model)


class ModelWithMissingColumn(JoineryModel):
    field1: Column[str]
    sub_schema: Column[SubModel]


input_schema = Schema(ModelWithMissingColumn)


input_df = input_schema.create_dataframe(
    [
        ModelWithMissingColumn(
            field1="value1",
            sub_schema=SubModel(subfield1="subvalue1", subfield2="subvalue2"),
        )
    ],
    pl.LazyFrame,
)

try:
    schema.coerce_dataframe(input_df, mode="project")
except SchemaCoercionError:
    print(traceback.format_exc(limit=1))
