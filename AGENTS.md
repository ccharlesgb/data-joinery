# Repository instructions

## Development

- Use `uv` for Python dependency and command execution.
- Use `just` recipes where available.

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