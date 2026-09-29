# Repository instructions

## Development

- Use `uv` for Python dependency and command execution.
- Use `just` recipes where available.

## Documentation

- Documentation is generated using `zensical`
- The just command to build docs is `just docs-build`
- The documentation relies on `docs_src` for runnable code snippets which `just docs-examples` updates for you
- When including a snipper the format should be:

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