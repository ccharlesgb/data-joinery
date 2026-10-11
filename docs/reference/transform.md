# Transform

Use `@transform` on a function before adding it to a pipeline. The decorated
function also validates its inputs and output when called directly.

Use `@side_effect` or `@transform(side_effect=True)` for a final step that writes or prints data.
It must declare `-> None`. Pass `include_side_effects=False` to `Pipeline.run()`
to skip these steps while running the rest of the pipeline.

::: data_joinery.transform.transform

::: data_joinery.transform.side_effect
