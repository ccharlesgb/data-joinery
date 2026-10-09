from dataclasses import dataclass
from typing import Annotated, assert_type

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from data_joinery import (
    BoundInput,
    Context,
    ContextSource,
    DefaultSource,
    Pipeline,
    Project,
    StepRun,
    transform,
)


@dataclass
class Row:
    value: int


@dataclass
class RunContext:
    label: str


def test_result_traces_bound_inputs_outputs_and_sources():
    @transform
    def read(label: Annotated[str, Context()]) -> str:
        return label

    @transform
    def write(text: str, suffix: str = "!") -> None:
        pass

    pipeline = Pipeline(RunContext)
    read_step = pipeline.add_step(read)
    write_step = pipeline.add_step(write)
    pipeline.connect(read_step, write_step, param="text")

    result = pipeline.run(RunContext("abc"))
    expected = (
        StepRun(
            step=read_step,
            transform=read,
            inputs={"label": BoundInput("abc", ContextSource("label"))},
            output="abc",
        ),
        StepRun(
            step=write_step,
            transform=write,
            inputs={
                "text": BoundInput("abc", read_step),
                "suffix": BoundInput("!", DefaultSource()),
            },
            output=None,
        ),
    )

    assert result.step_runs == expected
    assert dict(result) == {"read": "abc"}


def test_result_gets_output_by_step_or_name():
    @transform
    def first() -> str:
        return "first"

    @transform
    def second() -> str:
        return "second"

    pipeline = Pipeline()
    first_step = pipeline.add_step(first)
    pipeline.add_step(second)
    result = pipeline.run()

    assert_type(result.get_output(first_step), str)
    assert_type(result.get_output("first", str), str)
    assert result.get_output(first_step) == "first"
    assert result.get_output("second", str) == "second"


def test_result_checks_named_output_type():
    @transform
    def first() -> str:
        return "first"

    pipeline = Pipeline()
    pipeline.add_step(first)
    result = pipeline.run()

    with pytest.raises(TypeError, match="expected int"):
        result.get_output("first", int)


def test_result_gets_void_output_by_name():
    @transform
    def write() -> None:
        pass

    pipeline = Pipeline()
    pipeline.add_step(write)

    assert pipeline.run().get_output("write", type(None)) is None


def test_result_gets_dataframe_output_by_step():
    @transform
    def rows() -> Annotated[pl.DataFrame, Project(Row)]:
        return pl.DataFrame({"value": [1]})

    pipeline = Pipeline()
    left = pipeline.add_step(rows, "left")
    right = pipeline.add_step(rows, "right")
    result = pipeline.run()

    assert_type(result.get_output(left), pl.DataFrame)
    assert_frame_equal(result.get_output(right), pl.DataFrame({"value": [1]}))


def test_result_checks_input_type_and_step_identity():
    @transform
    def rows() -> Annotated[pl.DataFrame, Project(Row)]:
        return pl.DataFrame({"value": [1]})

    @transform
    def write(rows: Annotated[pl.DataFrame, Project(Row)], label: str = "x") -> None:
        pass

    pipeline = Pipeline()
    source = pipeline.add_step(rows)
    sink = pipeline.add_step(write)
    source >> sink
    result = pipeline.run()
    assert_type(result.get_input(sink, "rows", pl.DataFrame), pl.DataFrame)

    with pytest.raises(TypeError, match="expected str"):
        result.get_input(sink, "rows", str)
    with pytest.raises(KeyError, match="missing"):
        result.get_input(sink, "missing", pl.DataFrame)

    other_pipeline = Pipeline()
    other_step = other_pipeline.add_step(rows)
    with pytest.raises(KeyError, match="not in this pipeline result"):
        result.get_step_run(other_step)


def test_result_records_dataframe_passed_before_input_coercion():
    received: list[pl.DataFrame] = []
    default_rows = pl.DataFrame({"value": [1], "extra": [2]})

    @transform
    def write(
        rows: Annotated[pl.DataFrame, Project(Row)] = default_rows,
        label: str = "x",
    ) -> None:
        received.append(rows)

    pipeline = Pipeline()
    step = pipeline.add_step(write)

    recorded = pipeline.run().get_one_input(step, pl.DataFrame)

    assert recorded is default_rows
    assert_frame_equal(received[0], pl.DataFrame({"value": [1]}))


def test_result_get_one_input_raises_for_no_match():
    @transform
    def write(first: str = "a", second: str = "b") -> None:
        pass

    pipeline = Pipeline()
    pipeline.add_step(write)

    with pytest.raises(LookupError, match="found 0"):
        pipeline.run().get_one_input("write", int)


def test_result_get_one_input_raises_for_multiple_matches():
    @transform
    def write(first: str = "a", second: str = "b") -> None:
        pass

    pipeline = Pipeline()
    pipeline.add_step(write)

    with pytest.raises(LookupError, match="found 2"):
        pipeline.run().get_one_input("write", str)
