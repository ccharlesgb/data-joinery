import pytest

from data_joinery import Pipeline, PipelineOverrideError, side_effect, transform


def test_run_executes_side_effects_by_default():
    calls: list[str] = []

    @side_effect
    def publish() -> None:
        calls.append("publish")

    pipeline = Pipeline()
    pipeline.add_step(publish)

    pipeline.run()

    assert calls == ["publish"]


def test_run_skips_side_effects_and_runs_upstream_steps():
    calls: list[str] = []

    @transform
    def produce() -> int:
        calls.append("produce")
        return 1

    @transform(side_effect=True)
    def publish(value: int) -> None:
        calls.append("publish")

    pipeline = Pipeline()
    source = pipeline.add_step(produce)
    sink = pipeline.add_step(publish)
    source >> sink

    pipeline.run(include_side_effects=False)

    assert calls == ["produce"]


def test_skipped_step_is_absent_from_result():
    @transform
    def produce() -> int:
        return 1

    @transform(side_effect=True)
    def publish(value: int) -> None:
        pass

    pipeline = Pipeline()
    source = pipeline.add_step(produce)
    sink = pipeline.add_step(publish)
    source >> sink

    result = pipeline.run(include_side_effects=False)

    assert [invocation.step for invocation in result.step_invocations] == [source]


def test_get_step_invocation_rejects_skipped_step():
    @transform(side_effect=True)
    def publish() -> None:
        pass

    pipeline = Pipeline()
    step = pipeline.add_step(publish)

    result = pipeline.run(include_side_effects=False)

    with pytest.raises(KeyError, match="publish"):
        result.get_step_invocation(step)


def test_unmarked_void_step_still_runs_when_side_effects_are_skipped():
    calls: list[str] = []

    @transform
    def check() -> None:
        calls.append("check")

    pipeline = Pipeline()
    pipeline.add_step(check)

    pipeline.run(include_side_effects=False)

    assert calls == ["check"]


def test_skipped_side_effect_does_not_require_upstream_inputs():
    @transform(side_effect=True)
    def publish(value: int) -> None:
        pass

    pipeline = Pipeline()
    pipeline.add_step(publish)

    result = pipeline.run(include_side_effects=False)

    assert result.step_invocations == ()


def test_unmarked_override_of_side_effect_remains_skippable():
    calls: list[str] = []

    @transform(side_effect=True)
    def publish() -> None:
        calls.append("original")

    @transform
    def replacement() -> None:
        calls.append("replacement")

    pipeline = Pipeline()
    pipeline.add_step(publish)

    pipeline.run(
        include_side_effects=False,
        transform_overrides={"publish": replacement},
    )

    assert calls == []


def test_side_effect_override_cannot_replace_unmarked_step():
    @transform
    def check() -> None:
        pass

    @transform(side_effect=True)
    def replacement() -> None:
        pass

    pipeline = Pipeline()
    pipeline.add_step(check)

    with pytest.raises(PipelineOverrideError, match="cannot introduce a side effect"):
        pipeline.run(
            include_side_effects=False,
            transform_overrides={"check": replacement},
        )


def test_invalid_override_of_skipped_step_is_still_rejected():
    @transform(side_effect=True)
    def publish() -> None:
        pass

    @transform
    def replacement() -> int:
        return 1

    pipeline = Pipeline()
    pipeline.add_step(publish)

    with pytest.raises(PipelineOverrideError, match="same output contract"):
        pipeline.run(
            include_side_effects=False,
            transform_overrides={"publish": replacement},
        )
