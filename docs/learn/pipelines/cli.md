# Run pipelines from the command line

!!! example

    CLI is experimental

Use a `Job` to run your pipeline from the command line. You can pass in values
such as a report date or environment, skip side effects, and draw the pipeline
without running it.

## Define a job

Create a `Job` from your pipeline and use `@job.context()` to define the function
that prepares its [context](context.md). In this example, the function takes a
date from the command line and supplies it to the report pipeline:

``` python
--8<-- "docs_src/learn/pipelines/cli/cli_job.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/pipelines/cli/cli_job_stdout.log"
```

Job uses [Typer](https://typer.tiangolo.com/) to read command line inputs.
Use `typer.Argument` for a value supplied by position, like the report date above,
or `typer.Option` for a named option, like `--environment` in the example below.

The examples on this page use Typer's `CliRunner` to show command output.
For your own script, replace that block with:

``` python
if __name__ == "__main__":
    job()
```

If your pipeline has no context, create the Job without adding a context function.

## Run the job

Save your job in `reports.py`, then pass the report date after `run`:

``` shell
python reports.py run 2026-10-11
```

You can also run it with the `data-joinery` command:

``` shell
data-joinery run reports.py 2026-10-11
```

Add `--help` to see the inputs your job accepts:

``` shell
python reports.py run --help
data-joinery run reports.py --help
```

## Run without side effects

To make the report without printing it, pass `--skip-side-effects`:

``` shell
python reports.py run 2026-10-11 --skip-side-effects
```

This skips `print_report` because it is marked with `@side_effect`. The context
function and other steps still run. See [Side effects](side_effects.md) for more
about choosing which steps to mark.

## Draw the pipeline

Install `data-joinery[vis]` to draw your pipeline. The `visualize` command opens a
window showing its steps, without running them or creating the context:

``` shell
python reports.py visualize
```

Use `--output` to save an SVG or PNG instead:

``` shell
data-joinery visualize reports.py --output report.svg
data-joinery visualize reports.py --output report.png
```

You don't need to supply the report date to draw the pipeline.

## Set up and clean up resources

Some pipelines need a temporary directory, a database connection, or a Spark
session. Use `@contextmanager` to keep setup and cleanup together in your context
function. Put `@job.context()` above it, as shown here:

``` python
--8<-- "docs_src/learn/pipelines/cli/cli_managed.py"
```

:fontawesome-solid-code: Outputs:

``` python
--8<-- "docs_src/learn/pipelines/cli/cli_managed_stdout.log"
```

This example creates a temporary workspace before running the pipeline and
removes it afterwards, even if a step fails. The `yield` supplies the context to
the pipeline; cleanup goes after it or in a `finally` block.

It also adds an `--environment` option. The `Environment` enum limits the choices
to `preprod` and `prod`, with `preprod` as the default. Save this job as
`managed_reports.py`, replacing the `CliRunner` block as above, then run:

``` shell
python managed_reports.py run --environment prod
```

For Spark, create the session inside the context function and release it in
`finally`. Only stop a session your job owns; a session supplied by your platform
may need to stay running. Keep resource setup out of the code that builds the
graph, so help and visualization can work without starting those resources.

## Choose a file or module

The `data-joinery` command looks for `job` or a `build_job()` function in the file
you give it. If you leave out the file, it uses `main.py`. You can also give a
Python module name, or add `:name` to choose a particular job or builder:

``` shell
data-joinery run
data-joinery run reports.py 2026-10-11
data-joinery run my_project.reports:build_job 2026-10-11
```

Put the file or module before the job's inputs. When passing a positional value
such as a date, include the file name so the command knows which is which.
