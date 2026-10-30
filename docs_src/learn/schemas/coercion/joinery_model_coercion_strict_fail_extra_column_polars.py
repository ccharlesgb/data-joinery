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


class ModelWithExtraColumn(JoineryModel):
    field1: Column[str]
    field2: Column[str]
    sub_schema: Column[SubModel]
    extra_field: Column[str]


input_schema = Schema(ModelWithExtraColumn)


input_df = input_schema.create_dataframe(
    [
        ModelWithExtraColumn(
            field1="value1",
            field2="value2",
            sub_schema=SubModel(subfield1="subvalue1", subfield2="subvalue2"),
            extra_field="extra_value",
        )
    ],
    pl.LazyFrame,
)

try:
    schema.coerce_dataframe(input_df, mode="strict")
except SchemaCoercionError:
    print(traceback.format_exc(limit=1))
