# Coercing Schemas

Coercion in Data Joinery is the process of automatically converting an input DataFrame to a specified schema. There
are several modes available to control how strict/relaxed the coercion process should be for your transformations.

Use `Schema(Model).coerce_dataframe()` to take an input DataFrame and return either a new DataFrame that
matches the model's schema or raise a validation error if coercion fails based on the mode's strictness.

Let's take the following schema and walk through how each mode works:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_schemas.py"
```

## Coercion Modes

Depending on your workflow and needs, you can choose from several coercion modes.

### Strict

In strict mode, the input DataFrame must have exactly the same named fields and types as the
specified model. Any extra columns, missing columns or type mismatches will result in an error.
Field order and nullability are ignored, and the input field order is preserved. This DataFrame
has an extra column so will fail the `strict` validation check:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_strict_fail_extra_column_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_strict_fail_extra_column_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_strict_fail_extra_column_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_strict_fail_extra_column_spark_stdout.log"
    ```

However if the Dataframe is equivalent it will pass and return the same DataFrame:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_strict_happy_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_strict_happy_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_strict_happy_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_strict_happy_spark_stdout.log"
    ```

Strict does not care about ordering of the fields.

### Project Top Level

`project_top_level` projects only the model's top-level columns. If there is a difference in struct fields it will fail:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_top_level_fail_extra_struct_field_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_top_level_fail_extra_struct_field_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_top_level_fail_extra_struct_field_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_top_level_fail_extra_struct_field_spark_stdout.log"
    ```

### Project (Default)

The mode `project` projects nested struct fields, removing all fields that are not in
the model:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_happy_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_happy_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_happy_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_happy_spark_stdout.log"
    ```

Project will still fail if there are missing columns:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_fail_missing_columns_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_fail_missing_columns_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_fail_missing_columns_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_fail_missing_columns_spark_stdout.log"
    ```

### Project Cast

The most relaxed mode, `project_cast`, recursively projects fields and casts values to the model's field types. This
will still fail if the backend cannot cast a type safely, but this can be useful if reading external data and
you want to easily align your DataFrame with the model's schema. It will also still fail if there are missing columns:

=== "Polars"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_cast_polars.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_cast_polars_stdout.log"
    ```

=== "PySpark"

    ``` python
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_cast_spark.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` text
    --8<-- "docs_src/learn/coercion/dataclass_coercion_project_cast_spark_stdout.log"
    ```

Type casting in Data Joinery follows the backend's casting rules. If the cast is
permitted then a conversion attempt will happen to try to change the data type. This could still
raise a runtime error if the cast is not possible for a specific value in your dataframe.
