import traceback
from dataclasses import dataclass

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StringType, StructField, StructType

from data_joinery import Schema
from data_joinery.schema_types import SchemaCoercionError

from dataclasses import dataclass

from data_joinery import Schema


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
class SubModelWithExtraField:
    subfield1: str
    subfield2: str
    extra_field: str

@dataclass
class ModelWithExtraStructField:
    field1: str
    field2: str
    sub_schema: SubModelWithExtraField

input_schema = Schema(ModelWithExtraStructField)



spark = SparkSession.builder.getOrCreate()

input_df = input_schema.create_dataframe([
    ModelWithExtraStructField(
        field1="value1",
        field2="value2",
        sub_schema=SubModelWithExtraField(subfield1="subvalue1", subfield2="subvalue2", extra_field="extra_value")
    )
], DataFrame, session=spark)

coerced_df = schema.coerce_dataframe(input_df, mode="project")
coerced_df.show(truncate=50)
