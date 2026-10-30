# Runnable documentation examples

The directory for each page's examples mirrors its path under `docs/`, without the
`.md` extension. For example, `docs/learn/pipelines/index.md` uses examples from
`docs_src/learn/pipelines/index/`, and `docs/learn/schemas/coercion.md` uses
`docs_src/learn/schemas/coercion/`. Keep input files and generated output logs beside
their scripts. Every Python example must be included on its corresponding page.

Each Python file is a complete example. Run one with
`uv run --extra all python docs_src/path/to/example_spark.py`; files named `test_*.py`
run with `uv run --extra all pytest docs_src/path/to/test_example_spark.py`.

Use the registered backend names in filenames: `example_spark.py` and
`example_polars.py`. For examples that work with both backends, each tab in the Markdown
page includes its script and generated output. Keep backend-specific examples as a
single suffixed script and explain their scope in the page. Examples with no DataFrame
backend, or examples that mix backends, need no backend suffix.

`just docs-examples` runs every script, writes its `*_stdout.log`, and checks that every
snippet exists, belongs to its page's directory, and both variants appear on the same
page. It also checks that every Python example is included in a page. The logs are generated files.
`just docs-build` and `just docs-serve` run the examples before building the site, so a
clean checkout has all required output snippets.

Examples that demonstrate an error should catch it and print the traceback so the script
still exits successfully. Tests should pass. The runner treats any failing test as an error.
