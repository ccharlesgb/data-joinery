# Testing

!!! example

    Pipeline syntax is experimental

Pipeline tests check that connected transformations produce the expected result. If a
reader, writer, or model cannot run in a test environment, pass a replacement transformation
to `Pipeline.run()` through `transform_overrides`.

To inspect outputs and writer inputs from a completed run, see
[Inspecting Pipeline Runs](inspecting_pipeline_runs.md).

## Replacing readers and writers

Pass overrides to `Pipeline.run()` as a mapping from step name to another transformation. Overrides
apply only to that run. Give steps you plan to replace explicit names with `add_step(..., name="...")`.
This example replaces the reader and writer, then checks the
DataFrame passed to the writer:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/pipelines/testing/test_pipeline_read_write_overrides_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/pipelines/testing/test_pipeline_read_write_overrides_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/pipelines/testing/test_pipeline_read_write_overrides_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/pipelines/testing/test_pipeline_read_write_overrides_spark_stdout.log"
    ```

The production reader and writer are not called. An override may remove context dependencies but
cannot introduce dependencies absent from the original transformation. The pipeline still receives
its complete declared context, keeping its public interface stable. Contract parameters must remain
compatible, and the override must declare the same output contract as the production transformation.

## Replacing a model

Overrides can also replace a model training step with a small dummy model, so the
surrounding steps can be tested:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/pipelines/testing/test_pipeline_model_override_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/pipelines/testing/test_pipeline_model_override_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/pipelines/testing/test_pipeline_model_override_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/pipelines/testing/test_pipeline_model_override_spark_stdout.log"
    ```

An override must declare the same output contract as the production transformation. The dummy
training transformation therefore declares `Model`, but its runtime value can still be a
`DummyModel` instance.

## Context or an override?

Use [`Context()`](context.md) when the implementation is suitable for a test and only its values need
to change. Paths, dates, thresholds, and other configuration usually belong in the pipeline's context
dataclass.

Use an override when the implementation itself should not run, such as:

- a streaming sink that should be replaced with a memory sink
- a reader that depends on unavailable external infrastructure
- an expensive model-training implementation
- a writer with effects that the test needs to capture
