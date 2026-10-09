from dataclasses import dataclass
from typing import Annotated

import polars as pl
import pytest

from data_joinery import (
    BoundInput,
    DefaultSource,
    Project,
    Schema,
    StepRun,
    Strict,
    transform,
)
from data_joinery.pipeline import (
    Pipeline,
    PipelineConnectionError,
    PipelineExecutionError,
    PipelineOverrideError,
)
from data_joinery.schema_types import SchemaCoercionError


@dataclass
class User:
    user_id: int
    name: str


@dataclass
class Department:
    department_id: int


def test_schema_error_names_fields_types_and_repair():
    frame = pl.DataFrame({"user_id": ["1"], "extra": [True]})

    with pytest.raises(SchemaCoercionError) as caught:
        Schema(User).coerce_dataframe(frame, "strict")

    message = str(caught.value)
    assert "Schema 'User'" in message
    assert "Missing field 'name': expected String" in message
    assert "Additional field 'extra': got Boolean. Remove it" in message
    assert "Field 'user_id': expected Int64, got String" in message
    assert "'project_cast'" in message


def test_transform_schema_error_names_parameter_and_keeps_violations():
    @transform
    def accept(users: Annotated[pl.DataFrame, Project(User)]) -> None:
        pass

    with pytest.raises(SchemaCoercionError) as caught:
        accept(pl.DataFrame({"user_id": [1]}))

    assert "Transform 'accept' parameter 'users', Schema 'User'" in str(caught.value)
    assert "Missing field 'name'" in str(caught.value)
    assert caught.value.violations[0].path == "name"


def test_pipeline_connection_error_describes_both_contracts():
    @transform
    def users() -> Annotated[pl.DataFrame, Project(User)]:
        return pl.DataFrame()

    @transform
    def accept(departments: Annotated[pl.DataFrame, Project(Department)]) -> None:
        pass

    pipeline = Pipeline()
    source = pipeline.add_step(users)
    sink = pipeline.add_step(accept)

    with pytest.raises(PipelineConnectionError) as caught:
        pipeline.connect(source, sink)

    message = str(caught.value)
    assert "'users'" in message and "'accept'" in message
    assert "polars DataFrame[User]" in message
    assert "'departments': polars DataFrame[Department]" in message
    assert "Change an input or output annotation" in message
    assert "backends, types, and schema models match" in message


def test_ambiguous_connection_rejects_unmatched_explicit_parameter():
    @transform
    def users() -> Annotated[pl.DataFrame, Project(User)]:
        return pl.DataFrame()

    @transform
    def combine(
        left: Annotated[pl.DataFrame, Project(User)],
        right: Annotated[pl.DataFrame, Project(User)],
    ) -> None:
        pass

    pipeline = Pipeline()
    source = pipeline.add_step(users)
    sink = pipeline.add_step(combine)

    with pytest.raises(PipelineConnectionError, match="Choose one of: left, right"):
        pipeline.connect(source, sink, param="missing")


def test_pipeline_rejects_step_from_another_pipeline_with_clear_error():
    @transform
    def users() -> Annotated[pl.DataFrame, Project(User)]:
        return pl.DataFrame()

    first = Pipeline()
    second = Pipeline()
    source = first.add_step(users)
    sink = second.add_step(users)

    with pytest.raises(PipelineConnectionError, match="belongs to another pipeline"):
        second.connect(source, sink)


def test_pipeline_rejects_undecorated_step_with_clear_error():
    def users() -> pl.DataFrame:
        return pl.DataFrame()

    with pytest.raises(TypeError, match="decorated with @transform; got function"):
        Pipeline().add_step(users)  # type: ignore[arg-type]


def test_pipeline_names_unconnected_parameter():
    @transform
    def users() -> Annotated[pl.DataFrame, Project(User)]:
        return pl.DataFrame({"user_id": [1], "name": ["a"]})

    @transform
    def join(
        users: Annotated[pl.DataFrame, Project(User)],
        departments: Annotated[pl.DataFrame, Project(Department)],
    ) -> None:
        pass

    pipeline = Pipeline()
    source = pipeline.add_step(users)
    sink = pipeline.add_step(join)
    pipeline.connect(source, sink)

    with pytest.raises(
        PipelineExecutionError, match="step 'join' has unconnected inputs: departments"
    ):
        pipeline.run()


def test_pipeline_uses_default_for_unconnected_input():
    @transform
    def produce() -> str:
        return "hello world"

    @transform
    def consume(value: str, limit: int = 10) -> str:
        return value[:limit]

    pipeline = Pipeline()
    source = pipeline.add_step(produce)
    sink = pipeline.add_step(consume)
    pipeline.connect(source, sink)

    result = pipeline.run()
    expected = StepRun(
        step=sink,
        transform=consume,
        inputs={
            "value": BoundInput("hello world", source),
            "limit": BoundInput(10, DefaultSource()),
        },
        output="hello worl",
    )
    assert result.get_step_run(sink) == expected


def test_pipeline_runs_root_step_with_only_defaulted_inputs():
    @transform
    def read(path: str = "data.csv") -> str:
        return path

    pipeline = Pipeline()
    step = pipeline.add_step(read)

    result = pipeline.run()
    expected = StepRun(
        step=step,
        transform=read,
        inputs={"path": BoundInput("data.csv", DefaultSource())},
        output="data.csv",
    )
    assert result.get_step_run(step) == expected


def test_pipeline_runs_root_step_with_defaults_from_override():
    @transform
    def read(path: str) -> str:
        return path

    @transform
    def replacement(path: str = "fixture.csv") -> str:
        return path

    pipeline = Pipeline()
    step = pipeline.add_step(read)

    result = pipeline.run(transform_overrides={"read": replacement})
    expected = StepRun(
        step=step,
        transform=replacement,
        inputs={"path": BoundInput("fixture.csv", DefaultSource())},
        output="fixture.csv",
    )
    assert result.get_step_run(step) == expected


def test_pipeline_uses_effective_transform_default_for_unconnected_input():
    @transform
    def produce() -> str:
        return "value"

    @transform
    def consume(value: str, limit: int) -> str:
        return value[:limit]

    @transform
    def replacement(value: str, limit: int = 3) -> str:
        return value[:limit]

    pipeline = Pipeline()
    source = pipeline.add_step(produce)
    sink = pipeline.add_step(consume)
    pipeline.connect(source, sink)

    result = pipeline.run(transform_overrides={"consume": replacement})
    expected = StepRun(
        step=sink,
        transform=replacement,
        inputs={
            "value": BoundInput("value", source),
            "limit": BoundInput(3, DefaultSource()),
        },
        output="val",
    )
    assert result.get_step_run(sink) == expected


def test_override_error_names_expected_and_actual_output():
    @transform
    def users() -> Annotated[pl.DataFrame, Project(User)]:
        return pl.DataFrame()

    @transform
    def replacement() -> Annotated[pl.DataFrame, Strict(Department)]:
        return pl.DataFrame()

    pipeline = Pipeline()
    pipeline.add_step(users)

    with pytest.raises(PipelineOverrideError) as caught:
        pipeline.run(transform_overrides={"users": replacement})

    assert "expected polars DataFrame[User] (project)" in str(caught.value)
    assert "got polars DataFrame[Department] (strict)" in str(caught.value)
