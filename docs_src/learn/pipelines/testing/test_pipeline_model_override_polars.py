from dataclasses import dataclass
from typing import Annotated

import polars as pl
from polars.testing import assert_frame_equal

from data_joinery import Pipeline, Project, transform


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
def read_observations() -> Annotated[pl.DataFrame, Project(Observation)]:
    return pl.DataFrame({"value": [1, 2]})


@transform
def train_model(
    observations: Annotated[pl.DataFrame, Project(Observation)],
) -> Model:
    raise RuntimeError("expensive production training")


@transform
def predict(
    observations: Annotated[pl.DataFrame, Project(Observation)],
    model: Model,
) -> Annotated[pl.DataFrame, Project(Observation)]:
    return pl.DataFrame(
        {"value": [model.predict(value) for value in observations["value"]]}
    )


def build_pipeline() -> Pipeline:
    pipeline = Pipeline()
    read = pipeline.add_step(read_observations, name="read")
    train = pipeline.add_step(train_model, name="train")
    prediction = pipeline.add_step(predict, name="predict")
    pipeline.connect(read, train)
    pipeline.connect_many([read, train], prediction)
    return pipeline


def test_model_pipeline_with_dummy_training():
    @transform
    def train_dummy(
        observations: Annotated[pl.DataFrame, Project(Observation)],
    ) -> Model:
        return DummyModel()

    result = build_pipeline().run(
        transform_overrides={"train": train_dummy},
    )

    predicted = result.get_output("predict", pl.DataFrame)
    expected = pl.DataFrame({"value": [2, 4]})
    assert_frame_equal(predicted, expected)
