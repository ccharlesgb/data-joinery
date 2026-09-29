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

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_strict_fail_extra_column.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_strict_fail_extra_column_stdout.log"
```

However if the Dataframe is equivalent it will pass and return the same DataFrame:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_strict_happy.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_strict_happy_stdout.log"
```

Strict does not care about ordering of the fields.

### Project Top Level

`project_top_level` projects only the model's top-level columns. If there is a difference in struct fields it will fail:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_project_fail_missing_columns.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_project_top_level_fail_extra_struct_field.log"
```

### Project (Default)

The mode `project` projects nested struct fields, removing all fields that are not in
the model:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_project_happy.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_project_happy_stdout.log"
```

Project will still fail if there are missing columns:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_project_fail_missing_column.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_project_fail_missing_column_stdout.log"
```

### Project Cast

The most relaxed mode, `project_cast`, recursively projects fields and casts values to the model's field types. This
will still fail if the types cannot be safely cast by spark but this can be useful if reading external data and
you want to easily align your DataFrame with the model's schema. It will also still fail if there are missing columns:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_project_cast.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/coercion/dataclass_coercion_project_cast_stdout.log"
```

Type casting in Data Joinery follows the Spark casting rules described in
the [spark documentation](https://spark.apache.org/docs/latest/sql-ref-ansi-compliance.html#cast). If the cast is
permitted then the field will be wrapped in a `cast` function to try to change the data type. This could still
raise a runtime error if the cast is not possible for a specific value in your dataframe.
