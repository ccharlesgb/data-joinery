# Inspecting Pipeline Runs

!!! example

    Pipeline syntax is experimental

`Pipeline.run()` returns a `PipelineResult`. Most tests already have the `Step`
returned by `add_step`, so they can read its output with `result.get_output(step)`.
If you only have the step name, pass the expected runtime type:
`result.get_output("step_name", ValueType)`.

## Inspect what a writer received

For an end-to-end test, check the DataFrame passed to the final writer. Use
`get_one_input("write_orders", pl.DataFrame)` when the writer has one DataFrame
input. The example also reads the upstream step's output:

``` python
--8<-- "docs_src/learn/pipelines/inspecting_pipeline_runs/inspect_by_step.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/pipelines/inspecting_pipeline_runs/inspect_by_step_stdout.log"
```

!!! warning "Writer inputs are recorded before coercion"

    `get_input()` and `get_one_input()` return the DataFrame bound to the
    writer before its input contract projects columns or casts values. The
    writer function may therefore see different columns or types. To check
    the values after coercion, capture them inside a replacement writer.

`get_one_input` raises `LookupError` if no input or more than one input matches
the requested runtime type. It considers all bound inputs, including context
values and defaults. When several match, use
`get_input(writer_step, "orders", pl.DataFrame)` to name the parameter.

In a test, compare the recorded input with an expected DataFrame using the
backend's frame equality helper.

### Assert the writer input in a test

This test compares the complete DataFrame passed to the writer:

``` python
--8<-- "docs_src/learn/pipelines/inspecting_pipeline_runs/test_writer_input_polars.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/pipelines/inspecting_pipeline_runs/test_writer_input_polars_stdout.log"
```

## Read an intermediate DataFrame output

For a DataFrame step, use the same method. A saved `Step` gives the result its
declared output type. When looking up a step by name, pass the backend's
DataFrame class:

``` python
--8<-- "docs_src/learn/pipelines/inspecting_pipeline_runs/inspect_dataframe_polars.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/pipelines/inspecting_pipeline_runs/inspect_dataframe_polars_stdout.log"
```

For PySpark, pass `pyspark.sql.DataFrame` in place of `pl.DataFrame`. A named
lookup raises `TypeError` if the output has a different runtime type.

The [Pipeline result reference](../../reference/Pipeline.md#pipeline-results)
documents the methods and their errors.
