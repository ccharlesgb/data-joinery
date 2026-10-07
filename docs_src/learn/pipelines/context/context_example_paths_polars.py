from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import polars as pl

from data_joinery import Context, Pipeline, Strict, transform


@dataclass
class A:
    a: str


@dataclass
class B:
    b: str


@dataclass
class PathConfig:
    input_path: Path
    output_path: Path


@dataclass(frozen=True)
class PipelineDependencies:
    paths: PathConfig


@transform
def read_data(
    path_config: Annotated[PathConfig, Context()],
) -> Annotated[pl.DataFrame, Strict(A)]:
    return pl.read_csv(path_config.input_path, schema_overrides={"a": pl.String})


@transform
def transform_data(
    a: Annotated[pl.DataFrame, Strict(A)],
) -> Annotated[pl.DataFrame, Strict(B)]:
    return a.rename({"a": "b"})


@transform
def write_data(
    b: Annotated[pl.DataFrame, Strict(B)],
    path_config: Annotated[PathConfig, Context()],
) -> None:
    print("Write to ", path_config.output_path.name)
    print(b)


order_metrics = Pipeline(PipelineDependencies)
read_data_step = order_metrics.add_step(read_data)
transform_data_step = order_metrics.add_step(transform_data)
write_data_step = order_metrics.add_step(write_data)

order_metrics.connect(read_data_step, transform_data_step)
order_metrics.connect(transform_data_step, write_data_step)

input_path = Path(__file__).parent / "example.csv"
output_path = Path(__file__).parent / "output.parquet"

path_config = PathConfig(input_path=input_path, output_path=output_path)
context = PipelineDependencies(path_config)

order_metrics.run(context)
