from dataclasses import dataclass
from typing import Annotated

from pyspark.sql import DataFrame, SparkSession

from data_joinery import Context, Pipeline, Strict, transform
from data_joinery.backends.spark import SparkContext


@dataclass
class InputDataset:
    a: str
    b: str


@dataclass
class CollectedStats:
    distinct_a: int
    distinct_b: int


@transform
def read_data(
    spark: Annotated[SparkSession, Context()],
) -> Annotated[DataFrame, Strict(InputDataset)]:
    return spark.createDataFrame(
        [
            InputDataset("a1", "b1"),
            InputDataset("a2", "b2"),
            InputDataset("a3", "b2"),
            InputDataset("a4", "b2"),
        ]
    )


@transform
def collect_stats(
    input: Annotated[DataFrame, Strict(InputDataset)],
) -> CollectedStats:
    distinct_a = input.select("a").distinct().count()
    distinct_b = input.select("b").distinct().count()
    return CollectedStats(distinct_a=distinct_a, distinct_b=distinct_b)


@transform
def print_result(collected_stats: CollectedStats) -> None:
    print(collected_stats)


housing_price_model = Pipeline(SparkContext)
read_data_step = housing_price_model.add_step(read_data)
collect_stats_step = housing_price_model.add_step(collect_stats)
print_result_step = housing_price_model.add_step(print_result)

housing_price_model.connect(read_data_step, collect_stats_step)
housing_price_model.connect(collect_stats_step, print_result_step)

housing_price_model.run(SparkContext(SparkSession.builder.getOrCreate()))
