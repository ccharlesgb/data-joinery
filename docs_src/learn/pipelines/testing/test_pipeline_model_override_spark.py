from dataclasses import dataclass
from typing import Annotated

import pytest
from pyspark.sql import DataFrame, SparkSession
from pyspark.testing import assertDataFrameEqual

from data_joinery import Context, Pipeline, Project, transform
from data_joinery.backends.spark import SparkContext


@dataclass
class Observation:
    value: int


class Model:
    def predict(self, value: int) -> int:
        raise NotImplementedError


class DummyModel(Model):
    def predict(self, value: int) -> int:
        return value * 2


@transform
def read_observations(
    spark: Annotated[SparkSession, Context()],
) -> Annotated[DataFrame, Project(Observation)]:
    return spark.createDataFrame([(1,), (2,)], "value BIGINT")


@transform
def train_model(
    observations: Annotated[DataFrame, Project(Observation)],
) -> Model:
    raise RuntimeError("expensive production training")


@transform
def predict(
    spark: Annotated[SparkSession, Context()],
    observations: Annotated[DataFrame, Project(Observation)],
    model: Model,
) -> Annotated[DataFrame, Project(Observation)]:
    predictions = [(model.predict(row.value),) for row in observations.collect()]
    return spark.createDataFrame(
        predictions,
        "value BIGINT",
    )


def build_pipeline() -> Pipeline[SparkContext]:
    pipeline = Pipeline(SparkContext)
    read = pipeline.add_step(read_observations, name="read")
    train = pipeline.add_step(train_model, name="train")
    prediction = pipeline.add_step(predict, name="predict")
    pipeline.connect(read, train)
    pipeline.connect_many([read, train], prediction)
    return pipeline


@pytest.fixture(scope="module")
def spark():
    return SparkSession.builder.master("local[1]").getOrCreate()


def test_model_pipeline_with_dummy_training(spark: SparkSession):
    @transform
    def train_dummy(
        observations: Annotated[DataFrame, Project(Observation)],
    ) -> Model:
        return DummyModel()

    result = build_pipeline().run(
        SparkContext(spark),
        transform_overrides={"train": train_dummy},
    )

    predicted = result.get_output("predict", DataFrame)
    expected = spark.createDataFrame([(2,), (4,)], "value BIGINT")
    assertDataFrameEqual(predicted, expected)
