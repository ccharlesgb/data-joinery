from typing import Annotated

from pyspark.sql import DataFrame, SparkSession

from data_joinery import Column, JoineryModel, Pipeline, Strict, transform


class A(JoineryModel):
    a: Column[str]


class B(JoineryModel):
    b: Column[str]


@transform
def read_data() -> Annotated[DataFrame, Strict(A)]:
    spark = SparkSession.builder.getOrCreate()
    return spark.createDataFrame([{A.a: "value"}])


@transform
def transform_data(
    a: Annotated[DataFrame, Strict(A)],
) -> Annotated[DataFrame, Strict(B)]:
    return a.withColumnRenamed(A.a, B.b)


@transform
def write_data(
    b: Annotated[DataFrame, Strict(B)],
) -> None:
    b.show()


order_metrics = Pipeline()
read_data_step = order_metrics.add_step(read_data)
transform_data_step = order_metrics.add_step(transform_data)
write_data_step = order_metrics.add_step(write_data)

order_metrics.connect(read_data_step, transform_data_step)
order_metrics.connect(transform_data_step, write_data_step)

order_metrics.run()
