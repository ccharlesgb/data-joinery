from pyspark.sql import DataFrame, SparkSession

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


class SubModel2(JoineryModel):
    field2: Column[str]
    field1: Column[str]
    sub_schema: Column[SubModel]


input_schema = Schema(SubModel2)


spark = SparkSession.builder.getOrCreate()

input_df = input_schema.create_dataframe(
    [
        SubModel2(
            field1="value1",
            field2="value2",
            sub_schema=SubModel(subfield1="subvalue1", subfield2="subvalue2"),
        )
    ],
    DataFrame,
    session=spark,
)

coerced_df = schema.coerce_dataframe(input_df, mode="strict")
coerced_df.show()
