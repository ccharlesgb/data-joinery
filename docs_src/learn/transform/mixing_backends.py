from dataclasses import dataclass
from typing import Annotated, cast

import polars as pl
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import LongType, StructType

from data_joinery import Schema, Strict, transform
from data_joinery.contract import ProjectCast


@dataclass
class Record:
    record_id: Annotated[int, pl.UInt32, LongType()]
    label: str


record_schema = Schema(Record)


@transform
def polars_to_spark(
    records: Annotated[pl.DataFrame, Strict(Record)],
    spark: SparkSession,
) -> Annotated[DataFrame, Strict(Record)]:
    return spark.createDataFrame(
        records.to_dicts(), schema=record_schema.native_schema(StructType)
    )


@transform
def spark_to_polars(
    records: Annotated[DataFrame, Strict(Record)],
) -> Annotated[pl.DataFrame, ProjectCast(Record)]:
    return cast(pl.DataFrame, pl.from_arrow(records.toArrow()))


spark = SparkSession.builder.master("local[1]").appName("mixing-backends").getOrCreate()

polars_records = record_schema.create_dataframe(
    [Record(1, "first"), Record(2, "second")], pl.DataFrame
)
spark_records = polars_to_spark(polars_records, spark)
polars_records_back = spark_to_polars(spark_records)

print("Polars:\n", polars_records.schema)
print("Spark:\n", spark_records.schema)
print("Polars Back:\n", polars_records_back.schema)
