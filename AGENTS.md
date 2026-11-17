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
- Before adding or revising a documentation page, read comparable pages and their
  runnable examples. Start in the same section and look elsewhere in the docs if
  another page teaches a more similar task.
- Follow the conventions those pages share for structure, terminology, and how
  examples present code and output. During review, compare the edited section
  with a comparable page. Keep differences that help readers follow the lesson.
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

### Page focus

- Give each page or section one main teaching point. Keep the explanation
  focused on what readers need to understand or do to apply it.
- An example can use concepts taught elsewhere without explaining them again.
  Explain a supporting choice only when readers need to understand it to follow
  the example or make a decision the section asks them to make.
- During review, try removing each aside. If readers can still follow the
  example and apply the lesson correctly, leave it out. Link to an existing
  explanation when readers are likely to need it.

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
