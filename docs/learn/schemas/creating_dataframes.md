## Creating Dataframes

You can easily create example DataFrames from lists of model instances. This is particularly
useful for building test fixtures for a transformation. Pass the desired frame class to select
its backend. Spark also requires its session through the `session` keyword:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/fixture_example_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/fixture_example_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/fixture_example_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/fixture_example_spark_stdout.log"
    ```

## Lazy Polars frames

Pass `pl.LazyFrame` to create a lazy frame from model instances. Use `collect()` when
you want to run a query and get a `pl.DataFrame`:

``` python
--8<-- "docs_src/learn/schemas/lazy_creation_polars.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/schemas/lazy_creation_polars_stdout.log"
```
