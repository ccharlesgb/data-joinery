# Defining a Schema

Schemas wrap around `JoineryModel` classes. They allow you to define the structure of your data in a
backend agnostic way. The same schema can be used to define a schema for any backend you choose.

## JoineryModel

Take the below example for a simple JoineryModel schema:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/index/joinery_model_example_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/joinery_model_example_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/index/joinery_model_example_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/joinery_model_example_spark_stdout.log"
    ```

The method [native_schema](/reference/schemas/#data_joinery.Schema.native_schema) can be used to
generate the schema for a specific backend, such as PySpark or Polars.

## Column names as class attributes

JoineryModels retain fields as class attributes with string values. This means we can use `Order.price`
and `Order.quantity` when working with DataFrames, with autocomplete for column names:

``` python
--8<-- "docs_src/learn/schemas/index/class_attributes.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/schemas/index/class_attributes_stdout.log"
```

## Overriding column names

You can override the column name with the `column` function.
This is especially useful when we want to use a column name that is not a valid Python identifier:

``` python
--8<-- "docs_src/learn/schemas/index/column_names.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/schemas/index/column_names_stdout.log"
```

We can use these attributes to select and filter columns in a DataFrame:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/index/select_filter_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/select_filter_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/index/select_filter_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/select_filter_spark_stdout.log"
    ```

## Default Values

For test fixtures it can be useful for your model to provide default values for columns to reduce
the verbosity of your tests. Defaults can be set using the `default` or `default_factory` in the
same way as conventional dataclasses:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/index/model_defaults_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/model_defaults_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/index/model_defaults_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/model_defaults_spark_stdout.log"
    ```

Defaults are only relevant for dataframe construction, they do not have an impact on the underlying
dataframe schema.

## Nested schemas

If your data contains nested structs or arrays, describe them with nested JoineryModels:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/index/joinery_model_example_nested_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/joinery_model_example_nested_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/index/joinery_model_example_nested_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/schemas/index/joinery_model_example_nested_spark_stdout.log"
    ```
