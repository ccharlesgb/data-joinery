# Changelog

Notable changes to Data Joinery are documented here. This changelog follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-10-23

### Added

- Add experimental [JoineryModel](https://ccharlesgb.github.io/data-joinery/learn/schemas/joinery_model/) for defining schemas with column names available as class attributes.
- Export `SchemaCoercionError` from `data_joinery`.

### Changed

- Route pipeline connections so arrows leave and enter steps horizontally.

## [0.4.0] - 2026-10-13

### Added

- Connect pipeline steps with `>>` or `<<`, including lists of steps for branches and joins.

### Changed

- `Schema.coerce_dataframe()` now defaults to `strict` instead of `project`. Pass `mode="project"` to keep the previous behavior of removing extra fields.
- Support installation and use with PySpark 4.0.
- Show progress and completion messages for CLI `run` and `visualize` commands.

## [0.3.1] - 2026-10-11

### Added

- Run and visualize pipelines with the `data-joinery` command. CLI options support context values, skipping side effects, and saving visualizations as PNG or SVG.

## [0.3.0] - 2026-10-11

### Added

- Accept Polars `LazyFrame` in schema creation, coercion, and transforms while preserving lazy execution.
- Mark terminal transforms with `@side_effect` and skip them with `Pipeline.run(include_side_effects=False)`.
- Log pipeline and step progress, timings, and output types.

### Changed

- Rename result inspection API `StepRun`, `step_runs`, and `get_step_run()` to `StepInvocation`, `step_invocations`, and `get_step_invocation()`.

## [0.2.0] - 2026-10-09

### Added

- Inspect step outputs and bound inputs through the new `PipelineResult` returned by `Pipeline.run()`, including inputs to steps that return `None`.

### Changed

- `Pipeline.run()` now returns a `PipelineResult` rather than a plain dictionary. The result still supports mapping access to non-`None` outputs by step name.

## [0.1.2] - 2026-10-08

### Added

- Allow source steps to use default values for unconnected input parameters.

### Changed

- Show input and output types and labeled connections in `Pipeline.visualize()`, and return a Matplotlib figure that can be saved.
- Give more specific validation and schema error messages, with guidance on how to fix invalid pipelines and transforms.

## [0.1.1] - 2026-09-29

### Changed

- Make PySpark an optional dependency; install the `pyspark` extra for Spark support. The minimum supported PySpark version is 4.1.

### Removed

- Remove the top-level `Dbt` and `SparkContext` imports. Supply dependencies through a context dataclass and `Context()` annotations.

### Fixed

- Reject unexpected nested fields when applying `ProjectTopLevel` to a PySpark DataFrame.

## [0.1.0] - 2026-09-29

### Added

- First release as `data-joinery`, renamed from `spark-joinery`. Update package dependencies and Python imports to the new name.
- Define schema-validated transformations and connect them into pipelines. Supports PySpark DataFrames, optional Polars DataFrames, dataclass and Pydantic schemas, context dependencies, and schema coercion modes.

[Unreleased]: https://github.com/ccharlesgb/data-joinery/compare/0.5.0...HEAD
[0.5.0]: https://github.com/ccharlesgb/data-joinery/compare/0.4.0...0.5.0
[0.4.0]: https://github.com/ccharlesgb/data-joinery/compare/0.3.1...0.4.0
[0.3.1]: https://github.com/ccharlesgb/data-joinery/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/ccharlesgb/data-joinery/compare/0.2.0...0.3.0
[0.2.0]: https://github.com/ccharlesgb/data-joinery/compare/0.1.2...0.2.0
[0.1.2]: https://github.com/ccharlesgb/data-joinery/compare/0.1.1...0.1.2
[0.1.1]: https://github.com/ccharlesgb/data-joinery/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/ccharlesgb/data-joinery/releases/tag/0.1.0
