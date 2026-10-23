# Joinery Model

!!! example

    Joinery Models are experimental

Dataclasses and Pydantic models can define a schema, but transformations still
refer to column names as strings. For example, take this simple transformation:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/joinery_model/dataclass_transformation_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` python
    --8<-- "docs_src/learn/schemas/joinery_model/dataclass_transformation_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/joinery_model/dataclass_transformation_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` python
    --8<-- "docs_src/learn/schemas/joinery_model/dataclass_transformation_spark_stdout.log"
    ```

This is fine but we don't get any type safety or autocomplete on the column names for our
inputs and outputs. It means we have to keep switching between the model definitions and
our transformations to help us remember what each column is called.

I think this is a common complaint when working with dataframes. This is solved by an extension
of dataclasses called a `JoineryModel`. These models behave similarly to standard dataclasses but
they retain fields as class attributes with string values:

``` python
--8<-- "docs_src/learn/schemas/joinery_model/class_attributes.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/joinery_model/class_attributes_stdout.log"
```

We can use this in our transformations. Our earlier example can now use `Order.price`
and `Order.quantity`. Another advantage of `JoineryModel` is that we can override the column
name with the `column` function. This is especially useful when we want to use a
column name that is not a valid Python identifier:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/schemas/joinery_model/joinery_transformation_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` python
    --8<-- "docs_src/learn/schemas/joinery_model/joinery_transformation_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/schemas/joinery_model/joinery_transformation_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` python
    --8<-- "docs_src/learn/schemas/joinery_model/joinery_transformation_spark_stdout.log"
    ```
