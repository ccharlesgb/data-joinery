import traceback
from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession

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
class ModelWithExtraColumn:
    field1: str
    field2: str
    sub_schema: SubModel
    extra_field: str


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
