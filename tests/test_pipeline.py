from dataclasses import dataclass
from typing import Annotated

import pytest
from pyspark.sql import DataFrame, SparkSession

from data_joinery import (
    Column,
    Context,
    JoineryModel,
    Project,
    Strict,
    transform,
)
from data_joinery.backends.spark import SparkContext
from data_joinery.contract import DataFrameContract
from data_joinery.pipeline import (
    Pipeline,
    PipelineConnectionError,
    PipelineCycleError,
    PipelineExecutionError,
    PipelineOverrideError,
)
from tests.models import Department, PathConfig


class User(JoineryModel):
    user_id: Column[int]


class UserWithDepartment(JoineryModel):
    user_id: Column[int]
    department_id: Column[int]


@dataclass(frozen=True)
class UserContext:
    spark: SparkSession
    path: PathConfig


@dataclass(frozen=True)
class PathContext:
    path: PathConfig


@dataclass(frozen=True)
class FittedModel:
    coefficient: float


@transform
def _read_users_int(
    spark: Annotated[SparkSession, Context()],
) -> Annotated[DataFrame, Project(User)]:
    return spark.createDataFrame([(1,)], "user_id INT")


@transform
def _read_users_bigint(
    spark: Annotated[SparkSession, Context()],
) -> Annotated[DataFrame, Project(User)]:
    return spark.createDataFrame([(1,)], "user_id BIGINT")


@transform
def _fail_if_users_are_read(
    spark: Annotated[SparkSession, Context()],
) -> Annotated[DataFrame, Project(User)]:
    raise AssertionError


@transform
def _pass_through_users(
    users: Annotated[DataFrame, Project(User)],
) -> Annotated[DataFrame, Project(User)]:
    return users


@transform
def _read_departments_int(
    spark: Annotated[SparkSession, Context()],
) -> Annotated[DataFrame, Project(Department)]:
    return spark.createDataFrame([(1,)], "department_id INT")


def test_duplicate_edges_are_idempotent():
    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(_read_users_int, "users")
    filtered = pipeline.add_step(_pass_through_users, "filtered")
    pipeline.connect(users, filtered)
    pipeline.connect(users, filtered)

    # pipeline.validate()


def test_step_right_shift_connects_steps_and_returns_downstream():
    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(_read_users_int, "users")
    filtered = pipeline.add_step(_pass_through_users, "filtered")

    assert users >> filtered is filtered
    assert pipeline.get_upstream_steps(filtered) == {users}


def test_step_right_shift_rejects_non_step_operand():
    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(_read_users_int, "users")

    with pytest.raises(TypeError, match="only connect Step instances"):
        users >> "filtered"  # type: ignore[operator]


@pytest.fixture
def wiring_steps():
    @transform
    def source() -> int:
        return 1

    @transform
    def left(value: int) -> int:
        return value

    @transform
    def right(value: int) -> str:
        return str(value)

    @transform
    def sink(value: int, label: str) -> None:
        pass

    pipeline = Pipeline()
    return (
        pipeline,
        pipeline.add_step(source),
        pipeline.add_step(left),
        pipeline.add_step(right),
        pipeline.add_step(sink),
    )


def test_step_left_shift_connects_upstream(wiring_steps):
    pipeline, source, left, _, _ = wiring_steps

    assert left << source is source
    assert pipeline.get_upstream_steps(left) == {source}


def test_step_right_shift_connects_downstream_list(wiring_steps):
    pipeline, source, left, right, _ = wiring_steps
    downstream = [left, right]

    assert source >> downstream is downstream
    assert {step: pipeline.get_upstream_steps(step) for step in downstream} == {
        left: {source},
        right: {source},
    }


def test_step_left_shift_connects_upstream_list(wiring_steps):
    pipeline, _, left, right, sink = wiring_steps
    upstream = [left, right]

    assert sink << upstream is upstream
    assert pipeline.get_upstream_steps(sink) == {left, right}


def test_list_right_shift_connects_upstream_steps(wiring_steps):
    pipeline, _, left, right, sink = wiring_steps

    assert [left, right] >> sink is sink
    assert pipeline.get_upstream_steps(sink) == {left, right}


def test_list_left_shift_connects_downstream_steps(wiring_steps):
    pipeline, source, left, right, _ = wiring_steps

    assert [left, right] << source is source
    assert {step: pipeline.get_upstream_steps(step) for step in (left, right)} == {
        left: {source},
        right: {source},
    }


def test_step_shift_chains_through_lists(wiring_steps):
    pipeline, source, left, right, sink = wiring_steps

    assert source >> [left, right] >> sink is sink
    assert pipeline.get_upstream_steps(sink) == {left, right}


def test_step_left_shift_chains_through_lists(wiring_steps):
    pipeline, source, left, right, sink = wiring_steps

    assert sink << [left, right] << source is source
    assert pipeline.get_upstream_steps(sink) == {left, right}


def test_step_shift_rejects_empty_list(wiring_steps):
    _, source, _, _, _ = wiring_steps

    with pytest.raises(ValueError, match="at least one"):
        source >> []


def test_list_shift_rejects_empty_list(wiring_steps):
    _, _, _, _, sink = wiring_steps

    with pytest.raises(ValueError, match="at least one"):
        [] >> sink


def test_step_shift_rejects_non_step_in_list(wiring_steps):
    _, source, _, _, _ = wiring_steps

    with pytest.raises(TypeError, match="only connect Step instances"):
        source >> ["bad"]  # type: ignore[operator]


def test_step_shift_uses_contract_validation(wiring_steps):
    _, _, left, right, _ = wiring_steps

    with pytest.raises(PipelineConnectionError, match="No compatible contract"):
        right >> left


@pytest.mark.parametrize(
    "connect",
    [
        pytest.param(
            lambda pipeline, steps, sink: pipeline.connect_many(steps, sink),
            id="connect_many",
        ),
        pytest.param(lambda _, steps, sink: steps >> sink, id="right_shift"),
        pytest.param(lambda _, steps, sink: sink << steps, id="left_shift"),
    ],
)
def test_grouped_connections_leave_input_free_when_second_source_conflicts(
    wiring_steps, connect
):
    pipeline, source, left, _, sink = wiring_steps

    with pytest.raises(PipelineConnectionError, match="already connected"):
        connect(pipeline, [left, source], sink)

    assert pipeline.get_upstream_steps(sink) == set()


@pytest.mark.parametrize(
    "connect",
    [
        pytest.param(lambda source, steps: source >> steps, id="right_shift"),
        pytest.param(lambda source, steps: steps << source, id="left_shift"),
    ],
)
def test_grouped_connections_preserve_existing_edges_on_failure(wiring_steps, connect):
    pipeline, source, left, right, _ = wiring_steps
    pipeline.connect(source, right)

    with pytest.raises(PipelineConnectionError, match="No compatible contract"):
        connect(source, [right, left, source])

    assert {step: pipeline.get_upstream_steps(step) for step in (left, right)} == {
        left: set(),
        right: {source},
    }


def test_grouped_connections_leave_no_edges_when_a_later_edge_creates_a_cycle(
    wiring_steps,
):
    pipeline, _, left, _, sink = wiring_steps
    upstream = pipeline.add_step(left.transform, "upstream")
    pipeline.connect(upstream, left)

    with pytest.raises(PipelineCycleError):
        left >> [sink, upstream]

    assert pipeline.get_upstream_steps(sink) == set()


def test_connect_many_rejects_empty_sources():
    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(_read_users_int, "users")

    with pytest.raises(ValueError, match="at least one"):
        pipeline.connect_many([], users)


def test_pipeline_accepts_typed_instance_parameter():
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()], path: str
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id INT")

    Pipeline(SparkContext).add_step(read_users, "users")


def test_pipeline_allows_parameterless_source():
    @transform
    def create_users() -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    Pipeline().add_step(create_users, "users")


def test_context_free_pipeline_rejects_context():
    pipeline = Pipeline()

    with pytest.raises(TypeError, match="does not accept a context"):
        pipeline.run(SparkContext(object()))  # type: ignore[arg-type, call-overload]


def test_pipeline_rejects_wrong_context_type():
    pipeline = Pipeline(SparkContext)

    with pytest.raises(TypeError, match="expected context of type SparkContext"):
        pipeline.run(PathContext(PathConfig("path")))  # type: ignore[arg-type]


def test_pipeline_allows_write_step_without_output_schema(spark: SparkSession):
    written: list[DataFrame] = []

    @transform
    def write_users(users: Annotated[DataFrame, Project(User)]):
        written.append(users)

    pipeline = Pipeline(SparkContext)
    read_step = pipeline.add_step(_read_users_bigint, "users")
    write_step = pipeline.add_step(write_users, "write_users")
    pipeline.connect(read_step, write_step)

    result = pipeline.run(SparkContext(spark))

    assert result.get_input(write_step, "users", DataFrame) is result.get_output(
        read_step
    )
    assert [row.asDict() for row in written[0].collect()] == [{"user_id": 1}]
    assert result.get_output(write_step) is None


def test_pipeline_rejects_missing_dataframe_match():
    @transform
    def join_departments(
        departments: Annotated[DataFrame, Project(Department)],
    ) -> Annotated[DataFrame, Project(Department)]:
        return departments

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(_read_users_int, "users")
    join = pipeline.add_step(join_departments, "join")
    with pytest.raises(
        PipelineConnectionError,
        match="No compatible contract between steps 'users' and 'join'",
    ):
        pipeline.connect(users, join)


def test_pipeline_rejects_extra_upstream_output():
    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(_read_users_int, "users")
    departments = pipeline.add_step(_read_departments_int, "departments")
    accepted = pipeline.add_step(_pass_through_users, "accepted")
    with pytest.raises(
        PipelineConnectionError,
        match="No compatible contract between steps 'departments' and 'accepted'",
    ):
        pipeline.connect_many([users, departments], accepted)


def test_pipeline_rejects_ambiguous_duplicate_schema_outputs():
    pipeline = Pipeline(SparkContext)
    users_a = pipeline.add_step(_read_users_int, "users_a")
    users_b = pipeline.add_step(_read_users_int, "users_b")
    accepted = pipeline.add_step(_pass_through_users, "accepted")
    with pytest.raises(
        PipelineConnectionError,
        match="Step 'users_a' is already connected to 'accepted'",
    ):
        pipeline.connect_many([users_a, users_b], accepted)


def test_pipeline_rejects_cycles():
    @transform
    def first(
        users: Annotated[DataFrame, Project(User)],
    ) -> Annotated[DataFrame, Project(User)]:
        return users

    @transform
    def second(
        users: Annotated[DataFrame, Project(User)],
    ) -> Annotated[DataFrame, Project(User)]:
        return users

    pipeline = Pipeline(SparkContext)
    first_step = pipeline.add_step(first, "first")
    second_step = pipeline.add_step(second, "second")
    pipeline.connect(first_step, second_step)
    with pytest.raises(PipelineCycleError):
        pipeline.connect(second_step, first_step)


def test_pipeline_supports_multiple_dataframe_inputs():
    @transform
    def join(
        users: Annotated[DataFrame, Project(User)],
        departments: Annotated[DataFrame, Project(Department)],
    ) -> Annotated[DataFrame, Project(UserWithDepartment)]:
        return users.join(departments)

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(_read_users_int, "users")
    departments = pipeline.add_step(_read_departments_int, "departments")
    joined = pipeline.add_step(join, "joined")
    pipeline.connect_many([users, departments], joined)


def test_executable_pipeline_runs_sources_and_downstream_steps(
    spark: SparkSession,
):
    @transform
    def read_users(
        session: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return session.createDataFrame([(1,)], "user_id BIGINT")

    @transform
    def filter_users(
        users: Annotated[DataFrame, Project(User)],
    ) -> Annotated[DataFrame, Project(User)]:
        return users.filter("user_id = 1")

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(read_users, "users")
    filtered = pipeline.add_step(filter_users, "filtered")
    pipeline.connect(users, filtered)

    result = pipeline.run(SparkContext(spark))

    assert [invocation.step for invocation in result.step_invocations] == [
        users,
        filtered,
    ]
    assert result.get_output(filtered).collect()[0].user_id == 1


def test_executable_pipeline_passes_instance_outputs(spark: SparkSession):
    @transform
    def fit_model(users: Annotated[DataFrame, Project(User)]) -> FittedModel:
        return FittedModel(coefficient=float(users.count()))

    printed: list[FittedModel] = []

    @transform
    def print_coefficients(model: FittedModel) -> None:
        printed.append(model)

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(_read_users_bigint, "users")
    model = pipeline.add_step(fit_model, "model")
    printer = pipeline.add_step(print_coefficients, "printer")
    pipeline.connect(users, model)
    pipeline.connect(model, printer)

    result = pipeline.run(SparkContext(spark))

    assert result.get_output(model) == FittedModel(coefficient=1.0)
    assert printed == [FittedModel(coefficient=1.0)]


def test_executable_pipeline_runs_fan_in_and_independent_components(
    spark: SparkSession,
):
    @transform
    def read_departments(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(Department)]:
        return spark.createDataFrame([(2,)], "department_id BIGINT")

    @transform
    def join(
        users: Annotated[DataFrame, Project(User)],
        departments: Annotated[DataFrame, Project(Department)],
    ) -> Annotated[DataFrame, Project(UserWithDepartment)]:
        return users.selectExpr("user_id", "cast(2 as BIGINT) as department_id")

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(_read_users_bigint, "users")
    departments = pipeline.add_step(read_departments, "departments")
    joined = pipeline.add_step(join, "joined")
    pipeline.connect_many([users, departments], joined)

    result = pipeline.run(SparkContext(spark))

    assert len(result.step_invocations) == 3
    assert result.get_output(joined).collect()[0].user_id == 1


def test_executable_pipeline_requires_context_for_spark():
    pipeline = Pipeline(SparkContext)
    pipeline.add_step(_fail_if_users_are_read, "users")

    with pytest.raises(TypeError, match=r"Pipeline\[SparkContext\] requires a context"):
        pipeline.run()  # type: ignore[call-overload]


def test_executable_pipeline_rejects_root_step_requiring_dataframe(
    spark: SparkSession,
):
    @transform
    def filter_users(
        users: Annotated[DataFrame, Project(User)],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError("root step should not be called")

    pipeline = Pipeline()
    pipeline.add_step(filter_users, "filtered")

    with pytest.raises(
        PipelineExecutionError,
        match="requires upstream inputs",
    ):
        pipeline.run()


def test_executable_pipeline_wraps_transform_failure(
    spark: SparkSession,
):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise ValueError("source failed")

    pipeline = Pipeline(SparkContext)
    pipeline.add_step(read_users, "users")

    with pytest.raises(PipelineExecutionError, match="users") as error:
        pipeline.run(SparkContext(spark))

    assert isinstance(error.value.__cause__, ValueError)


def test_pipeline_accepts_context_annotated_parameter():

    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
        path: Annotated[PathConfig, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id INT")

    pipeline = Pipeline(UserContext)
    pipeline.add_step(read_users, "users")  # must not raise


def test_run_resolves_context_parameter_from_dataclass(spark: SparkSession):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
        path: Annotated[PathConfig, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        assert path == PathConfig("gs://bucket/users")
        return spark.createDataFrame([(1,)], "user_id BIGINT")

    pipeline = Pipeline(UserContext)
    users = pipeline.add_step(read_users, "users")

    context = UserContext(spark, PathConfig("gs://bucket/users"))
    result = pipeline.run(context)

    assert result.get_output(users).count() == 1


def test_pipeline_rejects_transform_dependency_missing_from_context():
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
        path: Annotated[PathConfig, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    with pytest.raises(TypeError, match="does not provide it"):
        pipeline.add_step(read_users, "users")


def test_run_uses_named_transform_overrides_without_mutating_pipeline(
    spark: SparkSession,
):
    production_calls = 0

    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
        path: Annotated[PathConfig, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        nonlocal production_calls
        production_calls += 1
        return spark.createDataFrame([(1,)], "user_id BIGINT")

    fixture_users = spark.createDataFrame([(2,)], "user_id BIGINT")

    @transform
    def read_fixture() -> Annotated[DataFrame, Project(User)]:
        return fixture_users

    pipeline = Pipeline(UserContext)
    read = pipeline.add_step(read_users, "read")

    context = UserContext(spark, PathConfig("gs://bucket/users"))
    overridden = pipeline.run(context, transform_overrides={"read": read_fixture})
    production = pipeline.run(context)

    assert overridden.get_output(read).collect()[0].user_id == 2
    assert production.get_output(read).collect()[0].user_id == 1
    assert production_calls == 1


def test_run_overrides_write_step(spark: SparkSession):
    @transform
    def write_users(users: Annotated[DataFrame, Project(User)]) -> None:
        raise AssertionError("production writer must not run")

    written_ids: list[int] = []

    @transform
    def capture_users(users: Annotated[DataFrame, Project(User)]) -> None:
        written_ids.extend(row.user_id for row in users.collect())

    pipeline = Pipeline(SparkContext)
    read = pipeline.add_step(_read_users_bigint, "read")
    write = pipeline.add_step(write_users, "write")
    read >> write

    result = pipeline.run(
        SparkContext(spark), transform_overrides={"write": capture_users}
    )

    assert written_ids == [1]
    assert result.get_input(write, "users", DataFrame).count() == 1
    assert result.get_output(write) is None


def test_run_validates_all_override_names_before_execution(spark: SparkSession):
    called = False

    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        nonlocal called
        called = True
        return spark.createDataFrame([(1,)], "user_id BIGINT")

    @transform
    def replacement() -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    pipeline.add_step(read_users, "read")

    with pytest.raises(PipelineOverrideError, match="unknown step 'read_'"):
        pipeline.run(
            SparkContext(spark),
            transform_overrides={"read_": replacement},
        )

    assert not called


def test_run_requires_override_to_be_a_transform(spark: SparkSession):
    def replacement() -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    pipeline.add_step(_fail_if_users_are_read, "read")

    with pytest.raises(PipelineOverrideError, match="decorated with @transform"):
        pipeline.run(  # type: ignore[no-matching-overload]
            SparkContext(spark),
            transform_overrides={"read": replacement},
        )


def test_run_rejects_override_with_different_input_boundary(spark: SparkSession):
    @transform
    def filter_users(
        users: Annotated[DataFrame, Project(User)],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    @transform
    def replacement() -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    read = pipeline.add_step(_fail_if_users_are_read, "read")
    filtered = pipeline.add_step(filter_users, "filter")
    read >> filtered

    with pytest.raises(PipelineOverrideError, match="different input parameters"):
        pipeline.run(
            SparkContext(spark),
            transform_overrides={"filter": replacement},
        )


@pytest.mark.parametrize(
    "output_contract",
    [
        pytest.param(Project(Department), id="different-model"),
        pytest.param(Strict(User), id="different-coercion-mode"),
    ],
)
def test_run_rejects_override_with_incompatible_output(
    spark: SparkSession, output_contract: DataFrameContract
):
    @transform
    def replacement() -> Annotated[DataFrame, output_contract]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    pipeline.add_step(_fail_if_users_are_read, "read")

    with pytest.raises(PipelineOverrideError, match="same output contract"):
        pipeline.run(
            SparkContext(spark),
            transform_overrides={"read": replacement},
        )


def test_run_rejects_override_that_introduces_context_dependency(
    spark: SparkSession,
):
    @transform
    def replacement(
        spark: Annotated[SparkSession, Context()],
        path: Annotated[PathConfig, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    pipeline.add_step(_fail_if_users_are_read, "read")

    with pytest.raises(
        PipelineOverrideError,
        match="introduces context dependencies.*PathConfig",
    ):
        pipeline.run(
            SparkContext(spark),
            transform_overrides={"read": replacement},
        )


def test_run_compares_override_context_by_lookup_type(spark: SparkSession):
    @transform
    def read_users(
        path: Annotated[PathConfig, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    @transform
    def replacement(
        aliased_path: Annotated[object, Context(PathConfig)],
    ) -> Annotated[DataFrame, Project(User)]:
        assert aliased_path == PathConfig("gs://bucket/users")
        return spark.createDataFrame([(1,)], "user_id BIGINT")

    pipeline = Pipeline(PathContext)
    read = pipeline.add_step(read_users, "read")

    result = pipeline.run(
        PathContext(PathConfig("gs://bucket/users")),
        transform_overrides={"read": replacement},
    )

    assert result.get_output(read).count() == 1


def test_run_rejects_output_from_sink_override(spark: SparkSession):
    @transform
    def write_users(users: Annotated[DataFrame, Project(User)]) -> None:
        raise AssertionError

    @transform
    def replacement(users: Annotated[DataFrame, Project(User)]) -> FittedModel:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    read = pipeline.add_step(_fail_if_users_are_read, "read")
    write = pipeline.add_step(write_users, "write")
    read >> write

    with pytest.raises(PipelineOverrideError, match="same output contract"):
        pipeline.run(
            SparkContext(spark),
            transform_overrides={"write": replacement},
        )


def test_pipeline_does_not_connect_different_dataframe_backends():
    from polars import LazyFrame

    @transform
    def polars_source() -> Annotated[LazyFrame, Project(User)]:
        return LazyFrame({"user_id": [1]})

    @transform
    def spark_sink(frame: Annotated[DataFrame, Project(User)]) -> None:
        pass

    pipeline = Pipeline()
    source = pipeline.add_step(polars_source)
    sink = pipeline.add_step(spark_sink)

    with pytest.raises(PipelineConnectionError, match="No compatible contract"):
        pipeline.connect(source, sink)
