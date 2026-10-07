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
class ModelWithExtraFieldAndDifferentType:
    field1: int
    field2: str
    sub_schema: SubModel


input_schema = Schema(ModelWithExtraFieldAndDifferentType)


input_df = input_schema.create_dataframe(
    [
        ModelWithExtraFieldAndDifferentType(
            field1=123,
            field2="value2",
            sub_schema=SubModel(subfield1="subvalue1", subfield2="subvalue2"),
        )
    ],
    pl.DataFrame,
)

coerced_df = schema.coerce_dataframe(input_df, mode="project_cast")
print(coerced_df)
