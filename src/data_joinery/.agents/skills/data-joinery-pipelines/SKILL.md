---
name: data-joinery-pipelines
description: Build and end-to-end test Data Joinery pipelines, including typed context, step connections, instance outputs, run results, and per-run transform overrides. Use when multiple transforms form a validated graph.
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
downstream)` is equivalent to `upstream >> downstream`; use `connect_many([...], downstream)` when
one step consumes several upstream results.

Connections are validated as the graph is built. Incompatible schema or instance contracts raise
`PipelineConnectionError`, and a connection that creates a cycle raises `PipelineCycleError`. A run
fails with `PipelineExecutionError` when an input dependency is left dangling. Correct the model or
connection instead of weakening a valid contract to suppress these errors.

`Pipeline.run(...)` returns a `PipelineResult`. It also acts as a mapping from step names to
non-`None` outputs, but use `result.get_output(step)` when you kept the `Step`, or
`result.get_output("step_name", ValueType)` when you only have its name. These methods can also
read a step whose output is `None`.

Use `result.get_input(step, "parameter", ValueType)` to inspect a specific bound input. Use
`result.get_one_input(step, ValueType)` only when exactly one input has that runtime type;
context values and defaults count too. Writer inputs are recorded before their input contracts
project or cast them. To test what the writer function actually receives after coercion, capture
the value inside an override. `get_step_run(step)` exposes the transform, bound input sources,
and output when the complete run record matters.

For a graph overview, install the `vis` extra and call `pipeline.visualize(show=False)` after
connecting steps. It returns a Matplotlib figure that can be saved or inspected.

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
the whole frame with `polars.testing.assert_frame_equal(actual, expected)` or
`pyspark.testing.assertDataFrameEqual(actual, expected)`, rather than checking rows, columns,
and counts separately. Prefer one meaningful assertion per test; split distinct behaviors into
separate tests. Keep separate assertions when they check genuinely different behavior, and do not
combine unrelated checks into a tuple merely to reduce the assertion count.
