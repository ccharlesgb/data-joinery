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

- Public module-level functions, class methods, and classes must have Google-style docstrings.
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

### Tone of voice

- Documentation should be clear and only reference the framework's behaviour and not it's internal 
  implementation. UNLESS the page is in the `internals` section

- Try to keep wording simple so that even somebody not an expert in Python can still understand it.

## Skills

Skills in `src/data_joinery/.agents` describe how to use the library as it exists now.
They are task-oriented guidance, not a changelog or a complete API reference.

- Update a skill when a change makes its existing instructions or examples incorrect or
  incomplete, or changes the recommended way to perform a task covered by that skill.
- Add guidance for a new feature only when it helps users perform a task within the skill's
  scope. A new public symbol or feature does not automatically require a skill update.
- Do not update skills for internal refactors, implementation details, test-only changes, or
  export cleanup unless they affect the usage taught by a skill.
- Edit the relevant guidance in place to describe the current behavior. Do not append change
  summaries, migration history, lists of removed symbols, or unrelated API inventories.
- Update supporting documentation, examples, and tests when the revised guidance requires it.
  Leave skills unchanged when their guidance remains accurate and sufficient.
