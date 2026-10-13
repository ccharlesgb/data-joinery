# Run pipelines from the command line

!!! example

    CLI is experimental

The `data-joinery` command runs a pipeline defined in a Python file. It can also
draw the pipeline, so you can check its steps without running them.

## Define a pipeline

Create a `pipeline` object or a `build_pipeline()` function that returns one.
The CLI loads that pipeline when you run a command. This example builds a report
for a date supplied at run time:

``` python
--8<-- "docs_src/learn/pipelines/cli_from_kwargs.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/learn/pipelines/cli_from_kwargs_stdout.log"
```

The pipeline has a `PipelineContext` dataclass because `make_report` needs a
run date. The `Context()` marker supplies that value to the transform. See
[Context](context.md) for more about passing values to steps.

## Run it with a date

Pass the path to the Python file and a value for `run_date`:

``` shell
data-joinery run docs_src/learn/pipelines/cli_from_kwargs.py --context run_date=2026-10-11
```

The command prints `Report for 2026-10-11`. Each `--context NAME=VALUE` becomes
a string keyword argument to `PipelineContext.from_kwargs()`. In this example,
`from_kwargs` converts the string to a `RunDate`. Add another `--context` option
for each additional value your context needs. A context class must define
`from_kwargs` to accept values from the command line.

If your pipeline has no context, leave out `--context`. When a context needs no
command line values, the CLI calls `from_kwargs()` if it exists, or creates the
context dataclass with no arguments.

## Run without side effects

The example marks `print_report` with `@side_effect`. To run `make_report`
without printing the report, pass `--skip-side-effects`:

``` shell
data-joinery run docs_src/learn/pipelines/cli_from_kwargs.py --context run_date=2026-10-11 --skip-side-effects
```

The report is still made, but `print_report` is skipped. Other steps that are
not marked as side effects continue to run. See [Side effects](side_effects.md)
for when to mark a step this way.

## Draw the pipeline

Install `data-joinery[vis]` to use `visualize`. This command opens a Matplotlib
window showing the pipeline's steps:

``` shell
data-joinery visualize docs_src/learn/pipelines/cli_from_kwargs.py
```

You can save the drawing as an SVG or PNG file instead of opening a window:

``` shell
data-joinery visualize docs_src/learn/pipelines/cli_from_kwargs.py --output report.svg
data-joinery visualize docs_src/learn/pipelines/cli_from_kwargs.py --output report.png
```

## Choose a pipeline file or module

If you leave out the path, the CLI looks for `pipeline` or `build_pipeline()` in
`main.py`. For another file or module, pass its path or import name. Add `:name`
when the pipeline has a different name:

``` shell
data-joinery run
data-joinery run pipelines/orders.py:orders_pipeline
data-joinery run my_project.orders:build_pipeline
```
