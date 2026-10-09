# Repository instructions

## Development

- Use `uv` for Python dependency and command execution.
- Use `just` recipes where available.

## Tests

- Prefer one meaningful assertion per test. Split distinct behaviors into separate tests instead
  of stacking assertions about each attribute of a result.
- Build an expected object and compare the complete value when equality is meaningful:
  `expected = Object(...)` followed by `assert actual == expected`.
- Compare whole DataFrames with the backend's test helper:
  `polars.testing.assert_frame_equal(actual, expected)` for Polars and
  `pyspark.testing.assertDataFrameEqual(actual, expected)` for PySpark. Construct an expected
  DataFrame instead of checking its rows, columns, and count separately.
- Keep separate assertions when they verify genuinely different behavior or when whole-object
  equality is unsuitable. Do not combine unrelated checks into a tuple merely to reduce the
  assertion count.

## Documentation

- Documentation is generated using `zensical`
- The just command to build docs is `just docs-build`
- The documentation relies on `docs_src` for runnable code snippets which `just docs-examples` updates for you
- When including a snippet the format should be:

    ``` python
    --8<-- "docs_src/my_snippet.py"
    ```

    :fontawesome-solid-code: Outputs:

    ``` python
    --8<-- "docs_src/my_snippet_stdout.log"
    ```

- The snippet should always exit 0. If the snippet is designed to show a failure 
it should wrap the failing line in a `try/except` like this:

``` python
try:
    boom()
except Exception:
    print(traceback.format_exc(limit=1))
```

- If the snippet is an example of writing a test then the filename should 
begin with `test_` and the documentation script will run it with pytest.

## Tone of voice

- Documentation should be clear and only reference the framework's behaviour and not it's internal 
  implementation. UNLESS the page is in the `internals` section

- Try to keep wording simple so that even somebody not an expert in Python can still understand it.
