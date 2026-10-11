# Side effects

A pipeline often ends by saving data, recording metrics, or printing a report.
These actions are side effects. Sometimes you want to inspect what the earlier
steps produce without running those final steps.

Use `@side_effect` to mark a transform that you want to skip in those runs.
It is shorthand for `@transform(side_effect=True)`. A side-effect transform
must declare `-> None`, so it is always the last step on its branch of the
pipeline.

## Running without side effects

You might want to run a pipeline without it's side effects to inspect the
intermediate results. Or if you a running in an environment where you don't
have write permissions, you might want to skip the steps that write to disk. Pass
`include_side_effects=False` to run the other steps without calling the marked
ones:

``` python
--8<-- "docs_src/learn/pipelines/side_effects.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/pipelines/side_effects_stdout.log"
```

In the first run, the pipeline creates the report but skips `print_report`.
The second run prints the report as normal.
