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


class SubModelWithExtraField(JoineryModel):
    subfield1: Column[str]
    subfield2: Column[str]
    extra_field: Column[str]


class ModelWithExtraStructField(JoineryModel):
    field1: Column[str]
    field2: Column[str]
    sub_schema: Column[SubModelWithExtraField]


input_schema = Schema(ModelWithExtraStructField)


input_df = input_schema.create_dataframe(
    [
        ModelWithExtraStructField(
            field1="value1",
            field2="value2",
            sub_schema=SubModelWithExtraField(
                subfield1="subvalue1", subfield2="subvalue2", extra_field="extra_value"
            ),
        )
    ],
    pl.LazyFrame,
)

try:
    schema.coerce_dataframe(input_df, mode="project_top_level")
except SchemaCoercionError:
    print(traceback.format_exc(limit=1))
