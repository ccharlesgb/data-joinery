# Pipelines

!!! example

    Pipeline syntax is experimental

Pipelines allow you to chain together multiple transformations. The pipeline will validate
that the output of each transformation is compatible with the input of the next one.

## Defining a pipeline

To define a pipeline first create all your transformations and input/output schemas. Then create
your pipeline class and add each transformation as a `Step`. A `Step` represents a single
instance of that transformation within the pipeline. This distinction allows you to reuse the same
transformation multiple times within the same pipeline. Once the transformations have been added
you must connect them together using the `connect` method. This method will verify that the
transformations are compatible and can be connected together:

``` python
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_happy.py"
```

:fontawesome-solid-code: Outputs:

``` md
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_happy_stdout.log"
```

## Validating the pipeline

The pipeline will validate itself as you connect transformations. If there is a schema or type
incompatibility then you will see a `PipelineConnectionError`. An example of this is shown below:

``` python
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_mismatch.py"
```

:fontawesome-solid-code: Outputs:

``` md
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_mismatch_stdout.log"
```

The pipeline will also fail to run if you have left a transformation 'dangling', meaning that it
is missing a connection for one of it's upstream dependencies:

``` python
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_dangling_transformation.py"
```

:fontawesome-solid-code: Outputs:

``` md
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_dangling_transformation_stdout.log"
```

## Detecting cycles

The pipeline will automatically detect cycles as you build it to ensure that the end result is
runnable. The below example shows how the error is raised as you are connecting transformations:

``` python
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_cycle.py"
```

:fontawesome-solid-code: Outputs:

``` md
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_cycle_stdout.log"
```

## Instance inputs/outputs

Pipeline steps can link transformations that accept and produce instance values. This allows you to pass around
typed objects such as machine learning models, pandas DataFrames or any general Python object
between steps in the pipeline. For instance contracts, the pipeline only validates that the runtime class is
compatible between the input and output; it does not perform schema coercion.

The below example shows
a common use case where data is read, then features are engineered and an ML model is trained. You
could then write this to MLflow for experiment tracking and model management:

``` python
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_instance_output.py"
```

:fontawesome-solid-code: Outputs:

``` md
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_instance_output_stdout.log"
```

Generic type annotations such as `list[str]` are not supported for instance
values. Instance contracts validate runtime classes and do not inspect the contents of
generic containers. An unsupported annotation fails when the transform is defined:

``` python
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_instance_output_generic_type_failure.py"
```

:fontawesome-solid-code: Outputs:

``` md
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_instance_output_generic_type_failure_stdout.log"
```

Wrap structured values in a named class when their internal types are important to the
pipeline contract.

Similarly to best practice with [context](context.md), you should avoid primative types such as
`int`, `datetime`, etc and prefer either wrapper types or classes to be explicit on input/outputs:

``` python
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_instance_good_practice.py"
```

:fontawesome-solid-code: Outputs:

``` md
--8<-- "docs_src/learn/pipelines/index/pipeline_connect_instance_good_practice_stdout.log"
```

!!! warning "Don't crash your driver node!"

    Instance values in most cases will be created or collected on the driver node in your
    spark cluster. If you are collecting a dataset to pandas/polars for example ensure you have enough
    memory on your driver node to accommodate the dataset.
