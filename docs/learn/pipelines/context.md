# Context

!!! example

    Pipeline syntax is experimental

Context allows you to inject additional dependencies or configuration into your transformations. You
can do this using the `Context()` marker in your transformation definition:

For pipelines that only require a Spark session, the built-in `SparkContext` can be used directly:

``` python
pipeline = Pipeline(SparkContext)
pipeline.run(SparkContext(spark))
```

Define a custom dataclass when the pipeline has additional dependencies:

``` python
--8<-- "docs_src/learn/pipelines/context/context_example_paths.py"
```

:fontawesome-solid-code: Outputs:

``` md
--8<-- "docs_src/learn/pipelines/context/context_example_paths_stdout.log"
```

Context is automatically injected into your transformation from the context dataclass declared by
the pipeline. Each field type identifies one dependency, so a context cannot contain multiple fields
of the same type. Use your own class definitions instead of built-in types like `str` or `int` when
their meaning matters. One common example is a run date for reading day-partitioned data. It is best
practice to define a distinct `date` subclass so the dependency is explicit:

``` python
--8<-- "docs_src/learn/pipelines/context/context_example_run_date.py"
```

:fontawesome-solid-code: Outputs:

``` md
--8<-- "docs_src/learn/pipelines/context/context_example_run_date_stdout.log"
```

## Validating Context

The pipeline validates every transformation against its declared context when the step is added. If
a transformation requires a dependency that the context dataclass does not provide, construction
fails immediately:

``` python
--8<-- "docs_src/learn/pipelines/context/context_example_unsatisifed.py"
```

:fontawesome-solid-code: Outputs:

``` md
--8<-- "docs_src/learn/pipelines/context/context_example_unsatisifed_stdout.log"
```
