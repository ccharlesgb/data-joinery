# Transformations

Data Joinery provides a decorator for defining transformations on DataFrames. This allows you to
annotate input and output schemas making it much clearer what the transformation does:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/transform/index/decorator_example_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/transform/index/decorator_example_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/transform/index/decorator_example_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/transform/index/decorator_example_spark_stdout.log"
    ```

## Defining a contract

You can define an input contract by annotating any input parameters with a valid [coercion mode](../../reference/contract.md) and
schema. The example above accepts a projected input and checks its output strictly. The contract
lets the transformation accept input with extra fields while keeping its output precise.

For read steps of wide/nested tables you might want to use `Project` as the output coercion mode
instead of writing out the full schema explicitly. This can be especially useful if you only
want to select a few fields of highly nested data:

``` python
@transform
def read_nested_event_data(
    spark: Annotated[SparkSession, Context()],
    path: str
) -> Annotated[DataFrame, Project(Event)]:
    return spark.read.parquet(path)
```

## Running Transformations

Call a transformation on a DataFrame. You can chain transformations in either backend:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/transform/index/usage_example_happy_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/transform/index/usage_example_happy_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/transform/index/usage_example_happy_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/transform/index/usage_example_happy_spark_stdout.log"
    ```

A schema mismatch in a transformation chain raises an error:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/transform/index/usage_example_bad_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/transform/index/usage_example_bad_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/transform/index/usage_example_bad_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/transform/index/usage_example_bad_spark_stdout.log"
    ```

!!! warning

    A PySpark transformation that performs an action such as `collect()` may process data
    before a later schema check raises `SchemaCoercionError`.
