# Pipeline Tests

!!! example

    Pipeline syntax is experimental

End-to-end pipeline tests allow you to confirm that the entire pipeline and transformation set
executes correctly for a given set of inputs. Sometimes you can configure a pipeline to read from
local files instead of buckets and lakehouse tables but in the cases of streaming or if your input is from Unity
Catalog you might not want to setup a local metastore to test your pipeline.

## Anatomy of a Pipeline Test

``` python
from my_project.pipeline import OrderPipelineContext, build_pipeline
from my_project.schemas import InputData

def test_pipeline_end_to_end(spark: SparkSession):
    @transform
    def read_data(
        spark: Annotated[SparkSession, Context()]
    ) -> Annotated[DataFrame, Project(InputData)]:
        rows = [
            InputData("foo", 1),
            InputData("bar", 2),
            InputData("baz", 3),
        ]

        schema = Schema(InputData)
        return schema.create_dataframe(rows, DataFrame, session=spark)

    outputs = build_pipeline().run(
        OrderPipelineContext(spark=spark, storage=test_storage),
        transform_overrides={"read_data": read_data},
    )

    # assert outputs["step_key"] == expected
```

Steps that are unsuitable for a test environment can be replaced for
a single run with transform overrides. Overrides are addressed by step name which is either
inferred from the `__name__` attribute of the transform or explicitly provided via the `name` argument:

``` python
def build_pipeline() -> Pipeline[OrderPipelineContext]:
    pipeline = Pipeline(OrderPipelineContext)
    read = pipeline.add_step(read_orders) # Given inferred name="read_orders"
    calculate = pipeline.add_step(calculate_totals, name="calculate")
    write = pipeline.add_step(write_totals, name="write")
    read >> calculate >> write
    return pipeline
```

For steps you intend to override it is best practice to give them explicit names when they are intended to be overridden.

## Replacing readers and writers

Pass overrides to `Pipeline.run()` as a mapping from step name to another transformation. Overrides
apply only to that run. This example replaces the read/writes for a pipeline to mock inputs and
allow the output to be inspected after the pipeline has run:

``` python
--8<-- "docs_src/learn/pipelines/testing/test_pipeline_read_write_overrides.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/pipelines/testing/test_pipeline_read_write_overrides_stdout.log"
```

The production reader and writer are not called. An override may remove context dependencies but
cannot introduce dependencies absent from the original transformation. The pipeline still receives
its complete declared context, keeping its public interface stable. Contract parameters must remain
compatible, and the override must declare the same output contract as the production transformation.

## Replacing a model

Use cases for overrides are not limited to I/O, sometimes you may have a ML model training step which is difficult
to generate an example dataset that allows it to train successfully, you can override this ML model with a dummy
model to test the steps before and after:

``` python
--8<-- "docs_src/learn/pipelines/testing/test_pipeline_model_override.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/pipelines/testing/test_pipeline_model_override_stdout.log"
```

An override must declare the same output contract as the production transformation. The dummy
training transformation therefore declares `Model`, but its runtime value can still be a
`DummyModel` instance.

## Context or an override?

Use [`Context()`](context.md) when the implementation is suitable for a test and only its values need
to change. Paths, dates, thresholds, and other configuration usually belong in the pipeline's context
dataclass.

Use an override when the implementation itself should not run, such as:

- a streaming sink that should be replaced with a memory sink
- a reader that depends on unavailable external infrastructure
- an expensive model-training implementation
- a writer with effects that the test needs to capture
