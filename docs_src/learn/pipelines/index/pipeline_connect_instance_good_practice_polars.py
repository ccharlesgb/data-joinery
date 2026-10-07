from dataclasses import dataclass
from typing import Annotated

import polars as pl

from data_joinery import Pipeline, Strict, transform


@dataclass
class InputDataset:
    a: str
    b: str


@dataclass
class CollectedStats:
    distinct_a: int
    distinct_b: int


@transform
def read_data() -> Annotated[pl.DataFrame, Strict(InputDataset)]:
    return pl.DataFrame(
        [
            InputDataset("a1", "b1"),
            InputDataset("a2", "b2"),
            InputDataset("a3", "b2"),
            InputDataset("a4", "b2"),
        ]
    )


@transform
def collect_stats(
    input: Annotated[pl.DataFrame, Strict(InputDataset)],
) -> CollectedStats:
    distinct_a = input.select("a").unique().height
    distinct_b = input.select("b").unique().height
    return CollectedStats(distinct_a=distinct_a, distinct_b=distinct_b)


@transform
def print_result(collected_stats: CollectedStats) -> None:
    print(collected_stats)


housing_price_model = Pipeline()
read_data_step = housing_price_model.add_step(read_data)
collect_stats_step = housing_price_model.add_step(collect_stats)
print_result_step = housing_price_model.add_step(print_result)

housing_price_model.connect(read_data_step, collect_stats_step)
housing_price_model.connect(collect_stats_step, print_result_step)

housing_price_model.run()
