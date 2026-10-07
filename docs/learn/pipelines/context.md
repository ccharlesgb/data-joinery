# Context

!!! example

    Pipeline syntax is experimental

Context allows you to inject additional dependencies or configuration into your transformations. You
can do this using the `Context()` marker in your transformation definition:

A PySpark pipeline that only requires a Spark session can use the built-in `SparkContext`:

``` python
pipeline = Pipeline(SparkContext)
pipeline.run(SparkContext(spark))
```

Define a custom dataclass when the pipeline has additional dependencies:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/pipelines/context/context_example_paths_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/pipelines/context/context_example_paths_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/pipelines/context/context_example_paths_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/pipelines/context/context_example_paths_spark_stdout.log"
    ```

Context is automatically injected into your transformation from the context dataclass declared by
the pipeline. Each field type identifies one dependency, so a context cannot contain multiple fields
of the same type. Use your own class definitions instead of built-in types like `str` or `int` when
their meaning matters. One common example is a run date for reading day-partitioned data. It is best
practice to define a distinct `date` subclass so the dependency is explicit:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/pipelines/context/context_example_run_date_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/pipelines/context/context_example_run_date_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/pipelines/context/context_example_run_date_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/pipelines/context/context_example_run_date_spark_stdout.log"
    ```

## Validating Context

The pipeline validates every transformation against its declared context when the step is added. If
a transformation requires a dependency that the context dataclass does not provide, construction
fails immediately:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/pipelines/context/context_example_unsatisifed_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/pipelines/context/context_example_unsatisifed_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/pipelines/context/context_example_unsatisifed_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/pipelines/context/context_example_unsatisifed_spark_stdout.log"
    ```
