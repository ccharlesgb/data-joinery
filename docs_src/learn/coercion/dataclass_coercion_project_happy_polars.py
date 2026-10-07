from dataclasses import dataclass

import polars as pl

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
    pl.DataFrame,
)

coerced_df = schema.coerce_dataframe(input_df, mode="project")
print(coerced_df)
