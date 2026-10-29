import polars as pl

from data_joinery import Schema
from data_joinery.schemas.joinery_model import Column, JoineryModel


class SubModel(JoineryModel):
    subfield1: Column[str]
    subfield2: Column[str]


class Model(JoineryModel):
    field1: Column[str]
    field2: Column[str]
    sub_schema: Column[SubModel]


schema = Schema(Model)


class ModelWithExtraFieldAndDifferentType(JoineryModel):
    field1: Column[int]
    field2: Column[str]
    sub_schema: Column[SubModel]


input_schema = Schema(ModelWithExtraFieldAndDifferentType)


input_df = input_schema.create_dataframe(
    [
        ModelWithExtraFieldAndDifferentType(
            field1=123,
            field2="value2",
            sub_schema=SubModel(subfield1="subvalue1", subfield2="subvalue2"),
        )
    ],
    pl.LazyFrame,
)

coerced_df = schema.coerce_dataframe(input_df, mode="project_cast")
print(coerced_df.collect())
