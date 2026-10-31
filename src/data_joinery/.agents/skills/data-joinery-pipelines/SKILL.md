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

Import `SparkContext` from `data_joinery.backends.spark`. That package exposes only
`SPARK_BACKEND`, `SparkBackend`, and `SparkContext` as its public API. Import contract markers
such as `Project`, `ProjectCast`, `ProjectTopLevel`, and `Strict` from `data_joinery`.

For a dbt Python model, put dbt's runtime object in the pipeline context and use it in reader
transforms to fetch upstream models or sources.

## Make a Pipeline Available to the CLI

Create `Job(pipeline=...)` named `job`, or a zero-argument `build_job()` returning one.
Keep module imports and graph construction free of runtime resource acquisition.
Register a typed provider to prepare the context only when `run` executes:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from data_joinery import Job, Pipeline


@dataclass(frozen=True)
class ReportContext:
    destination: Path


job = Job(pipeline=Pipeline(ReportContext))


@job.context()
def context(
    destination: Annotated[Path, typer.Option(help="Report destination.")],
) -> ReportContext:
    """Prepare dependencies for a report run."""
    return ReportContext(destination)


if __name__ == "__main__":
    job()
```

Add transforms and connections to the graph as usual. Typer parses the provider's parameters,
including `Annotated` metadata, defaults, positional arguments, and enum choices. Use
`typer.BadParameter` for application input validation. Context dataclasses just hold dependencies.

```shell
python main.py run --destination report.csv
data-joinery run main.py --destination report.csv
data-joinery run main.py --destination report.csv --skip-side-effects
data-joinery run main.py --help
data-joinery visualize main.py --output report.svg
```

The shared launcher accepts `COMMAND [TARGET] [COMMAND_INPUTS...]`. A target can be a file,
module, or explicit attribute such as `my_project.report:build_report_job`. It defaults to
`main.py`, looking for `job` then `build_job()`. Always supply a target before positional
application inputs. Bare launcher help does not import the application; help after a target
shows the job's inputs. Direct scripts always show job-specific help.

To manage resources, decorate a synchronous `@contextmanager` provider with `@job.context()`
on the outside. Acquire resources inside the provider, yield the context, and release owned
resources in `finally`. Job exits the manager after success, validation errors, execution errors,
and interruptions. Plain context objects are never automatically entered or closed. Keep Spark
session provisioning in the application provider, and stop sessions only when the application
owns them. An environment enum can select application configuration; it does not itself select
a Spark cluster.

Register one provider before accessing `job.app` or calling `job()`. Raw generators, async
providers, positional-only parameters, `*args`, and `**kwargs` are unsupported. The name
`skip_side_effects` and option aliases `--skip-side-effects` and `--help` are reserved.
A context-free Job needs no provider and rejects registration. Help and visualization do not
invoke providers. Install the `vis` extra to display diagrams or save SVG/PNG files.

`--skip-side-effects` skips only marked side effects. Ordinary steps and context initialization
still run, and managed resources still close. Use `pipeline.run(context)` from Python for results
and transform overrides. The registered provider remains independently callable; `job.app`
supports Typer's `CliRunner`.

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
