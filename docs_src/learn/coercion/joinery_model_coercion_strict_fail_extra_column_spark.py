import traceback

from pyspark.sql import DataFrame, SparkSession

from data_joinery import Schema, SchemaCoercionError
from data_joinery.schemas.joinery_model import Column, JoineryModel


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


spark = SparkSession.builder.getOrCreate()

input_df = input_schema.create_dataframe(
    [
        ModelWithExtraColumn(
            field1="value1",
            field2="value2",
            sub_schema=SubModel(subfield1="subvalue1", subfield2="subvalue2"),
            extra_field="extra_value",
        )
    ],
    DataFrame,
    session=spark,
)

try:
    schema.coerce_dataframe(input_df, mode="strict")
except SchemaCoercionError:
    print(traceback.format_exc(limit=1))
