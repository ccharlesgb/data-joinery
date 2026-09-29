## Creating Dataframes

You can easily create example DataFrames from lists of model instances. This is particularly
useful for building test fixtures for a transformation. Pass the desired frame class to select
its backend. Spark also requires its session through the `session` keyword:

``` python
--8<-- "docs_src/learn/schemas/fixture_example.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/schemas/fixture_example_stdout.log"
```
