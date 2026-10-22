---
name: data-joinery-pipelines
description: Build, run from the CLI, visualize, and end-to-end test Data Joinery pipelines, including typed context, step connections, run results, and per-run transform overrides. Use when multiple transforms form a validated graph.
---

# Data Joinery Pipelines

Pipeline syntax is experimental. Keep graph construction separate from transform behavior so each
transform remains independently testable.

## Build the Graph

Create contracted transforms first. Add each use of a transform as a step, then connect compatible
outputs and inputs:

```python
from data_joinery import Pipeline


def build_pipeline() -> Pipeline[OrderPipelineContext]:
    pipeline = Pipeline(OrderPipelineContext)
    read = pipeline.add_step(read_orders, name="read")
    calculate = pipeline.add_step(calculate_totals, name="calculate")
    write = pipeline.add_step(write_totals, name="write")
    read >> calculate >> write
    return pipeline
```

The same transform can be added more than once because a step represents one named instance in the
graph. Give explicit, stable names to steps that tests or callers address. `connect(upstream,
downstream)` is equivalent to `upstream >> downstream` or `downstream << upstream`. Use
`upstream >> [first, second]` to connect one output to several steps, or
`[first, second] >> downstream` when one step consumes several upstream results. The equivalent
reversed forms are `[first, second] << upstream` and `downstream << [first, second]`.
Lists can also appear between shifts, as in `source >> [first, second] >> joined`.
Use `connect_many([...], downstream)` for the explicit many-to-one form.

Connections are validated as the graph is built. Incompatible schema or instance contracts raise
`PipelineConnectionError`, and a connection that creates a cycle raises `PipelineCycleError`. A run
fails with `PipelineExecutionError` when an input dependency is left dangling. Correct the model or
connection instead of weakening a valid contract to suppress these errors.

Polars steps can use `pl.LazyFrame` or `pl.DataFrame` contracts. Prefer `pl.LazyFrame` across
connected steps and collect at the boundary that needs an eager result. Use matching frame types
in connected output and input annotations.

`Pipeline.run(...)` returns a `PipelineResult`. It also acts as a mapping from step names to
non-`None` outputs, but use `result.get_output(step)` when you kept the `Step`, or
`result.get_output("step_name", ValueType)` when you only have its name. These methods can also
read a step whose output is `None`.

Use `result.get_input(step, "parameter", ValueType)` to inspect a specific bound input. Use
`result.get_one_input(step, ValueType)` only when exactly one input has that runtime type;
context values and defaults count too. Writer inputs are recorded before their input contracts
project or cast them. To test what the writer function actually receives after coercion, capture
the value inside an override. `get_step_invocation(step)` exposes the transform, bound input
sources, and output when the complete invocation record matters.

For a graph overview, install the `vis` extra and call `pipeline.visualize(show=False)` after
connecting steps. It returns a Matplotlib figure that can be saved or inspected.

## Skip Side Effects

Mark final writers, metric loggers, and printers with `@side_effect` (or
`@transform(side_effect=True)`). They must declare `-> None` and cannot feed another step.
`pipeline.run(context, include_side_effects=False)` runs the rest of the graph without calling
marked steps. Side effects run by default, and unmarked transforms that return `None` still run.
Skipped steps have no `StepInvocation` in the result. Calling a marked transform directly still runs it.

The original step's marker controls skipping when a run uses `transform_overrides`: an unmarked
replacement of a marked writer is still skipped, while a marked replacement cannot be used for an
unmarked step. If a test needs to inspect the input to a writer, override the writer instead of
skipping it. Pipeline visualizations show marked steps with an amber accent and `SIDE EFFECT` label.

## Inject Typed Context

Mark non-graph dependencies with `Annotated[DependencyType, Context()]`. Declare the available
dependencies in the pipeline's context dataclass:

```python
from dataclasses import dataclass
from typing import Annotated

from data_joinery import Context


@dataclass(frozen=True)
class OrderPipelineContext:
    spark: SparkSession
    storage: Storage


@transform
def read_orders(
    spark: Annotated[SparkSession, Context()],
    storage: Annotated[Storage, Context()],
) -> Annotated[DataFrame, Project(Order)]:
    return spark.table(storage.input_table)
```

Context is resolved by field type, so a context cannot contain two fields of the same type. Wrap
paths, dates, thresholds, and similar values in meaningfully named types or configuration classes
instead of using ambiguous primitives. Use the built-in `SparkContext` when the Spark session is
the only dependency. A step that asks for a type absent from the declared context fails when it is
added.

For a dbt Python model, put dbt's runtime object in the pipeline context and use it in reader
transforms to fetch upstream models or sources.

## Make a Pipeline Available to the CLI

Put a `Pipeline` object named `pipeline` or a no-argument `build_pipeline()` function in a Python
file. The CLI loads that object or calls the function to get the graph. Keep graph construction
separate from execution: importing the file and building the graph should not run steps, read
data, or create external sessions. `visualize` builds the graph without creating a context or
running the pipeline.

For example, `main.py` can define a context factory that converts a command line date into a
typed dependency:

```python
from dataclasses import dataclass
from datetime import date
from typing import Annotated

from data_joinery import Context, Pipeline, side_effect, transform


class RunDate(date):
    pass


@dataclass(frozen=True)
class ReportContext:
    run_date: RunDate

    @classmethod
    def from_kwargs(cls, *, run_date: str) -> "ReportContext":
        return cls(run_date=RunDate.fromisoformat(run_date))


@transform
def make_report(run_date: Annotated[RunDate, Context()]) -> str:
    return f"Report for {run_date.isoformat()}"


@side_effect
def print_report(report: str) -> None:
    print(report)


def build_pipeline() -> Pipeline[ReportContext]:
    pipeline = Pipeline(ReportContext)
    pipeline.add_step(make_report) >> pipeline.add_step(print_report)
    return pipeline
```

From the directory containing `main.py`, run:

```shell
data-joinery run --context run_date=2026-10-11
data-joinery run --context run_date=2026-10-11 --skip-side-effects
data-joinery visualize --output report.svg
```

For another file, pass its path, such as `data-joinery run pipelines/report.py`. An importable
module also works, such as `data-joinery run my_project.report`. Add `:attribute` when the
pipeline object or builder has a different name, for example
`data-joinery run my_project.report:build_report_pipeline`. Without a target, the CLI uses
`main.py` and looks for `pipeline` first, then `build_pipeline`.

Each repeated `--context NAME=VALUE` supplies one string keyword argument to the context
class's `from_kwargs` method. The method must convert those strings into dependencies and
return an instance of that context class. Define it whenever the CLI must accept context
values; the CLI does not derive options or conversions from dataclass fields. If the pipeline
has a context but no `--context` options, the CLI calls `from_kwargs()` when it exists or
constructs the context with no arguments. A context-free pipeline accepts no `--context`
options. Keep required runtime services in the context factory or steps so drawing the graph
does not start them. Manage the lifetime of services created by the factory yourself; the CLI
does not close them after a run.

`run` executes marked side effects unless `--skip-side-effects` is passed. In the example,
skipping prevents `print_report` from running while `make_report` still runs. Mark only terminal
steps that should be skipped with `@side_effect`; an unmarked `-> None` step still runs. Install
the `vis` extra to use `visualize`. It opens a Matplotlib window by default, or saves an SVG or
PNG when passed `--output report.svg` or `--output report.png`. See the Pipeline CLI guide
in the project documentation for a runnable version of this example.

## Pass Ordinary Instance Values

Transforms can pass typed Python objects such as fitted models between steps. Pipeline validation
checks their runtime classes, not their internal structure, and does no schema coercion. Generic
annotations such as `list[str]` are unsupported. Prefer named classes for structured values and be
mindful that collected objects and pandas or Polars frames normally reside in Spark driver memory.

## Test the Pipeline End to End

Use real transforms for the behavior under test, a local backend session, and small deterministic
fixtures. Change context values when the production implementation works with local paths or
configuration. Replace a step only when its implementation itself should not run, such as external
I/O, a streaming sink, or expensive model training.

Overrides are per-run and keyed by step name:

```python
outputs = build_pipeline().run(
    OrderPipelineContext(spark=spark, storage=test_storage),
    transform_overrides={"read": read_fixture, "write": capture_totals},
)
```

An override must declare the same output contract as the production transform. Its contract
parameters must remain compatible, and it can remove context dependencies but cannot introduce a
context dependency absent from the original. The pipeline still receives its complete declared
context. For an instance output, an override can return a subclass at runtime while retaining the
production transform's declared base-class output contract.

A practical end-to-end test usually:

1. creates input frames from `Schema(Model).create_dataframe(...)` or another small local fixture;
2. overrides unavailable readers and effectful writers with decorated transforms;
3. runs the production graph with a complete context object;
4. compares the writer input or selected step output with the expected result from `PipelineResult`.

Use explicit names for every overridable step. Build an expected object and compare the complete
value when equality is meaningful. For a DataFrame, construct an expected DataFrame and compare
the whole frame with `polars.testing.assert_frame_equal` or
`pyspark.testing.assertDataFrameEqual`. Collect a lazy Polars result before comparing it with an
expected frame. Avoid separate checks of rows, columns, and counts. Prefer one meaningful
assertion per test; split distinct behaviors into
separate tests. Keep separate assertions when they check genuinely different behavior, and do not
combine unrelated checks into a tuple merely to reduce the assertion count.
