from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated

import pytest
from pyspark.sql import DataFrame, SparkSession

from data_joinery import (
    Context as ExportedContext,
)
from data_joinery import (
    Project,
    SparkContext,
    Strict,
    transform,
)
from data_joinery.dependencies import Context
from data_joinery.pipeline import (
    Pipeline,
    PipelineConnectionError,
    PipelineCycleError,
    PipelineExecutionError,
    PipelineOverrideError,
)


@dataclass
class User:
    user_id: int


@dataclass
class Department:
    department_id: int


@dataclass
class UserWithDepartment:
    user_id: int
    department_id: int


@dataclass(frozen=True)
class PathConfig:
    value: str


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


@pytest.fixture(scope="session")
def spark() -> Generator[SparkSession, None, None]:
    spark = (
        SparkSession.builder.appName("pyspark-schemas-pipeline-tests")
        .master("local[*]")
        .getOrCreate()
    )
    yield spark
    spark.stop()


def test_duplicate_edges_are_idempotent():
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id INT")

    @transform
    def filter_users(
        users: Annotated[DataFrame, Project(User)],
    ) -> Annotated[DataFrame, Project(User)]:
        return users

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(read_users, "users")
    filtered = pipeline.add_step(filter_users, "filtered")
    pipeline.connect(users, filtered)
    pipeline.connect(users, filtered)

    # pipeline.validate()


def test_step_right_shift_connects_steps_and_returns_downstream():
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id INT")

    @transform
    def filter_users(
        users: Annotated[DataFrame, Project(User)],
    ) -> Annotated[DataFrame, Project(User)]:
        return users

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(read_users, "users")
    filtered = pipeline.add_step(filter_users, "filtered")

    assert users >> filtered is filtered
    assert pipeline.get_upstream_steps(filtered) == {users}


def test_step_right_shift_rejects_non_step_operand():
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id INT")

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(read_users, "users")

    with pytest.raises(TypeError, match="only connect Step instances"):
        users >> "filtered"  # type: ignore[operator]


def test_connect_many_rejects_empty_sources():
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id INT")

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(read_users, "users")

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
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id BIGINT")

    written: list[DataFrame] = []

    @transform
    def write_users(users: Annotated[DataFrame, Project(User)]):
        written.append(users)

    pipeline = Pipeline(SparkContext)
    read_step = pipeline.add_step(read_users, "users")
    write_step = pipeline.add_step(write_users, "write_users")
    pipeline.connect(read_step, write_step)

    outputs = pipeline.run(SparkContext(spark))

    assert len(written) == 1
    assert "write_users" not in outputs


def test_pipeline_rejects_missing_dataframe_match():
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id INT")

    @transform
    def join_departments(
        departments: Annotated[DataFrame, Project(Department)],
    ) -> Annotated[DataFrame, Project(Department)]:
        return departments

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(read_users, "users")
    join = pipeline.add_step(join_departments, "join")
    with pytest.raises(
        PipelineConnectionError,
        match="No compatible contract between steps 'users' and 'join'",
    ):
        pipeline.connect(users, join)


def test_pipeline_rejects_extra_upstream_output():
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id INT")

    @transform
    def read_departments(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(Department)]:
        return spark.createDataFrame([(1,)], "department_id INT")

    @transform
    def accept_users(
        users: Annotated[DataFrame, Project(User)],
    ) -> Annotated[DataFrame, Project(User)]:
        return users

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(read_users, "users")
    departments = pipeline.add_step(read_departments, "departments")
    accepted = pipeline.add_step(accept_users, "accepted")
    with pytest.raises(
        PipelineConnectionError,
        match="No compatible contract between steps 'departments' and 'accepted'",
    ):
        pipeline.connect_many([users, departments], accepted)


def test_pipeline_rejects_ambiguous_duplicate_schema_outputs():
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id INT")

    @transform
    def accept_users(
        users: Annotated[DataFrame, Project(User)],
    ) -> Annotated[DataFrame, Project(User)]:
        return users

    pipeline = Pipeline(SparkContext)
    users_a = pipeline.add_step(read_users, "users_a")
    users_b = pipeline.add_step(read_users, "users_b")
    accepted = pipeline.add_step(accept_users, "accepted")
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
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id INT")

    @transform
    def read_departments(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(Department)]:
        return spark.createDataFrame([(1,)], "department_id INT")

    @transform
    def join(
        users: Annotated[DataFrame, Project(User)],
        departments: Annotated[DataFrame, Project(Department)],
    ) -> Annotated[DataFrame, Project(UserWithDepartment)]:
        return users.join(departments)

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(read_users, "users")
    departments = pipeline.add_step(read_departments, "departments")
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

    outputs = pipeline.run(SparkContext(spark))

    assert set(outputs) == {"users", "filtered"}
    assert outputs["filtered"].collect()[0].user_id == 1


def test_executable_pipeline_passes_instance_outputs(spark: SparkSession):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id BIGINT")

    @transform
    def fit_model(users: Annotated[DataFrame, Project(User)]) -> FittedModel:
        return FittedModel(coefficient=float(users.count()))

    printed: list[FittedModel] = []

    @transform
    def print_coefficients(model: FittedModel) -> None:
        printed.append(model)

    pipeline = Pipeline(SparkContext)
    users = pipeline.add_step(read_users, "users")
    model = pipeline.add_step(fit_model, "model")
    printer = pipeline.add_step(print_coefficients, "printer")
    pipeline.connect(users, model)
    pipeline.connect(model, printer)

    outputs = pipeline.run(SparkContext(spark))

    assert outputs["model"] == FittedModel(coefficient=1.0)
    assert printed == [FittedModel(coefficient=1.0)]


def test_executable_pipeline_runs_fan_in_and_independent_components(
    spark: SparkSession,
):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id BIGINT")

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
    users = pipeline.add_step(read_users, "users")
    departments = pipeline.add_step(read_departments, "departments")
    joined = pipeline.add_step(join, "joined")
    pipeline.connect_many([users, departments], joined)

    outputs = pipeline.run(SparkContext(spark))

    assert set(outputs) == {"users", "departments", "joined"}
    assert outputs["joined"].collect()[0].user_id == 1


def test_executable_pipeline_requires_context_for_spark():
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    pipeline.add_step(read_users, "users")

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
    pipeline.add_step(read_users, "users")

    context = UserContext(spark, PathConfig("gs://bucket/users"))
    outputs = pipeline.run(context)

    assert outputs["users"].count() == 1


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


def test_dependency_types_are_exported_from_package():
    assert ExportedContext is Context


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
    pipeline.add_step(read_users, "read")

    context = UserContext(spark, PathConfig("gs://bucket/users"))
    overridden = pipeline.run(context, transform_overrides={"read": read_fixture})
    production = pipeline.run(context)

    assert overridden["read"].collect()[0].user_id == 2
    assert production["read"].collect()[0].user_id == 1
    assert production_calls == 1


def test_run_overrides_write_step(spark: SparkSession):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        return spark.createDataFrame([(1,)], "user_id BIGINT")

    @transform
    def write_users(users: Annotated[DataFrame, Project(User)]) -> None:
        raise AssertionError("production writer must not run")

    written_ids: list[int] = []

    @transform
    def capture_users(users: Annotated[DataFrame, Project(User)]) -> None:
        written_ids.extend(row.user_id for row in users.collect())

    pipeline = Pipeline(SparkContext)
    read = pipeline.add_step(read_users, "read")
    write = pipeline.add_step(write_users, "write")
    read >> write

    outputs = pipeline.run(
        SparkContext(spark), transform_overrides={"write": capture_users}
    )

    assert written_ids == [1]
    assert "write" not in outputs


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

    with pytest.raises(PipelineOverrideError, match="unknown step 'raed'"):
        pipeline.run(
            SparkContext(spark),
            transform_overrides={"raed": replacement},
        )

    assert not called


def test_run_requires_override_to_be_a_transform(spark: SparkSession):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    def replacement() -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    pipeline.add_step(read_users, "read")

    with pytest.raises(PipelineOverrideError, match="decorated with @transform"):
        pipeline.run(  # type: ignore[no-matching-overload]
            SparkContext(spark),
            transform_overrides={"read": replacement},
        )


def test_run_rejects_override_with_different_input_boundary(spark: SparkSession):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    @transform
    def filter_users(
        users: Annotated[DataFrame, Project(User)],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    @transform
    def replacement() -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    read = pipeline.add_step(read_users, "read")
    filtered = pipeline.add_step(filter_users, "filter")
    read >> filtered

    with pytest.raises(PipelineOverrideError, match="different input parameters"):
        pipeline.run(
            SparkContext(spark),
            transform_overrides={"filter": replacement},
        )


def test_run_rejects_override_with_incompatible_output(spark: SparkSession):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    @transform
    def replacement() -> Annotated[DataFrame, Project(Department)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    pipeline.add_step(read_users, "read")

    with pytest.raises(PipelineOverrideError, match="same output contract"):
        pipeline.run(
            SparkContext(spark),
            transform_overrides={"read": replacement},
        )


def test_run_rejects_override_that_introduces_context_dependency(
    spark: SparkSession,
):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    @transform
    def replacement(
        spark: Annotated[SparkSession, Context()],
        path: Annotated[PathConfig, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    pipeline.add_step(read_users, "read")

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
    pipeline.add_step(read_users, "read")

    outputs = pipeline.run(
        PathContext(PathConfig("gs://bucket/users")),
        transform_overrides={"read": replacement},
    )

    assert outputs["read"].count() == 1


def test_run_rejects_override_with_different_output_coercion_mode(
    spark: SparkSession,
):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    @transform
    def replacement() -> Annotated[DataFrame, Strict(User)]:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    pipeline.add_step(read_users, "read")

    with pytest.raises(PipelineOverrideError, match="same output contract"):
        pipeline.run(
            SparkContext(spark),
            transform_overrides={"read": replacement},
        )


def test_run_rejects_output_from_sink_override(spark: SparkSession):
    @transform
    def read_users(
        spark: Annotated[SparkSession, Context()],
    ) -> Annotated[DataFrame, Project(User)]:
        raise AssertionError

    @transform
    def write_users(users: Annotated[DataFrame, Project(User)]) -> None:
        raise AssertionError

    @transform
    def replacement(users: Annotated[DataFrame, Project(User)]) -> FittedModel:
        raise AssertionError

    pipeline = Pipeline(SparkContext)
    read = pipeline.add_step(read_users, "read")
    write = pipeline.add_step(write_users, "write")
    read >> write

    with pytest.raises(PipelineOverrideError, match="same output contract"):
        pipeline.run(
            SparkContext(spark),
            transform_overrides={"write": replacement},
        )
