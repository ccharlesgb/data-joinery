import logging
import re
from dataclasses import dataclass
from typing import Annotated

import pytest

from data_joinery import Context, Pipeline, transform

_DURATION = r"\d+\.\d{3}s"


def assert_logs_produced(
    caplog: pytest.LogCaptureFixture,
    expected: list[str | re.Pattern[str]],
) -> None:
    actual = [
        record.getMessage()
        for record in caplog.records
        if record.name == "data_joinery"
    ]
    assert len(actual) == len(expected) and all(
        message == pattern
        if isinstance(pattern, str)
        else pattern.fullmatch(message) is not None
        for message, pattern in zip(actual, expected, strict=True)
    ), f"Expected logs: {expected!r}\nActual logs: {actual!r}"


def test_run_logs_pipeline_summary_and_result(caplog: pytest.LogCaptureFixture):
    @transform
    def produce() -> int:
        return 2

    @transform
    def consume(value: int) -> None:
        pass

    pipeline = Pipeline()
    source = pipeline.add_step(produce)
    sink = pipeline.add_step(consume)
    source >> sink

    with caplog.at_level(logging.INFO, logger="data_joinery"):
        pipeline.run()

    assert_logs_produced(
        caplog,
        [
            "Pipeline.run() started (steps: 2, context: none, overrides: 0)",
            re.compile(
                rf"Pipeline\.run\(\) returned in {_DURATION} \(step invocations: 2, outputs: 1\)"
            ),
        ],
    )


def test_run_logs_override_and_step_invocation(caplog: pytest.LogCaptureFixture):
    @transform
    def production() -> int:
        return 1

    @transform
    def replacement() -> int:
        return 2

    pipeline = Pipeline()
    pipeline.add_step(production, "read")

    with caplog.at_level(logging.DEBUG, logger="data_joinery"):
        pipeline.run(transform_overrides={"read": replacement})

    assert_logs_produced(
        caplog,
        [
            "Pipeline.run() started (steps: 1, context: none, overrides: 1)",
            "Override for step 'read': transform 'replacement'",
            (
                "Invoking step 'read' with transform 'replacement' "
                "(inputs: (); context fields: ())"
            ),
            re.compile(rf"Step 'read' returned in {_DURATION} \(return type: int\)"),
            re.compile(
                rf"Pipeline\.run\(\) returned in {_DURATION} \(step invocations: 1, outputs: 1\)"
            ),
            "Pipeline result step invocations: read",
        ],
    )


def test_run_logs_all_result_step_invocations(caplog: pytest.LogCaptureFixture):
    @transform
    def read() -> int:
        return 1

    @transform
    def write(value: int) -> None:
        pass

    pipeline = Pipeline()
    source = pipeline.add_step(read)
    sink = pipeline.add_step(write)
    source >> sink

    with caplog.at_level(logging.DEBUG, logger="data_joinery"):
        pipeline.run()

    assert_logs_produced(
        caplog,
        [
            "Pipeline.run() started (steps: 2, context: none, overrides: 0)",
            (
                "Invoking step 'read' with transform 'read' "
                "(inputs: (); context fields: ())"
            ),
            re.compile(rf"Step 'read' returned in {_DURATION} \(return type: int\)"),
            (
                "Invoking step 'write' with transform 'write' "
                "(inputs: ('value',); context fields: ())"
            ),
            re.compile(
                rf"Step 'write' returned in {_DURATION} \(return type: NoneType\)"
            ),
            re.compile(
                rf"Pipeline\.run\(\) returned in {_DURATION} \(step invocations: 2, outputs: 1\)"
            ),
            "Pipeline result step invocations: read, write",
        ],
    )


def test_run_logs_only_executed_steps_when_side_effects_are_skipped(
    caplog: pytest.LogCaptureFixture,
):
    @transform
    def read() -> int:
        return 1

    @transform(side_effect=True)
    def write(value: int) -> None:
        pass

    pipeline = Pipeline()
    source = pipeline.add_step(read)
    sink = pipeline.add_step(write)
    source >> sink

    with caplog.at_level(logging.DEBUG, logger="data_joinery"):
        pipeline.run(include_side_effects=False)

    assert_logs_produced(
        caplog,
        [
            "Pipeline.run() started (steps: 2, context: none, overrides: 0)",
            "Invoking step 'read' with transform 'read' (inputs: (); context fields: ())",
            re.compile(rf"Step 'read' returned in {_DURATION} \(return type: int\)"),
            re.compile(
                rf"Pipeline\.run\(\) returned in {_DURATION} \(step invocations: 1, outputs: 1\)"
            ),
            "Pipeline result step invocations: read",
        ],
    )


def test_run_logs_context_field_without_value(caplog: pytest.LogCaptureFixture):
    @dataclass
    class Secret:
        value: str

    @dataclass
    class RunContext:
        secret: Secret

    @transform
    def read(secret: Annotated[Secret, Context()]) -> int:
        return len(secret.value)

    pipeline = Pipeline(RunContext)
    pipeline.add_step(read)

    with caplog.at_level(logging.DEBUG, logger="data_joinery"):
        pipeline.run(RunContext(Secret("private-value")))

    assert_logs_produced(
        caplog,
        [
            "Pipeline.run() started (steps: 1, context: RunContext, overrides: 0)",
            (
                "Invoking step 'read' with transform 'read' "
                "(inputs: ('secret',); context fields: ('secret',))"
            ),
            re.compile(rf"Step 'read' returned in {_DURATION} \(return type: int\)"),
            re.compile(
                rf"Pipeline\.run\(\) returned in {_DURATION} \(step invocations: 1, outputs: 1\)"
            ),
            "Pipeline result step invocations: read",
        ],
    )
