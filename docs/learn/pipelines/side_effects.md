# Side effects

A pipeline often ends by saving data, recording metrics, or printing a report.
These actions are side effects.

Use `@side_effect` to mark a transform that returns `None` and does a side effect:

``` python
@side_effect
def write_output(df: Annotated[DataFrame, Project(OutputSchema)], path: str) -> None:
    df.write.parquet(path)

@side_effect
def log_ml_model(model: LinearRegression, experimet_id: str) -> None:
    mlflow.log_model(model, experiment_id)
```

## Running without side effects

You might want to run a pipeline without it's side effects to inspect the
intermediate results. Or if you a running in an environment where you don't
have write permissions, you might want to skip the steps that write to disk. Pass
`include_side_effects=False` when running pipelines to run all steps leading up to side effects:

``` python
--8<-- "docs_src/learn/pipelines/side_effects.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/pipelines/side_effects_stdout.log"
```

In the first run, the pipeline creates the report but skips `print_report`.
The second run prints the report as normal.

Running without side effects can also be a great CICD check to ensure that your pipeline will run
without mutating the state of your environment.

## Polars Lazy Sinks

Polars supports [lazy sinks](https://docs.pola.rs/user-guide/lazy/sources_sinks/#multiplexing-sinks).
With `lazy=True`, each write step returns a query plan instead of writing a file.
Mark only the step that calls `pl.collect_all` as a side effect to run both sinks
together:

``` python
--8<-- "docs_src/learn/pipelines/side_effects_lazy_sinks.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/pipelines/side_effects_lazy_sinks_stdout.log"
```

