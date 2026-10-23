# Package structure review

Reviewed on 2026-10-22 against `refactor-package-layout` at `6463938`.
Only remaining recommendations are listed below. These are proposals, not agreed
implementation work.

## Recommended follow-ups

### Public imports and compatibility

The backend guide already documents canonical protocol and registry imports, and
backend-independent registry tests are in place. The remaining work is to clarify
other supported imports.

- [ ] Document preferred imports for application code and backend authors.
  Application code generally uses the package root. Backend examples also use
  `schemas.coercion` and `schemas.model_schema`; explain which are supported
  extension interfaces.
- [ ] Decide and document the pipeline exception policy. The root exports
  `PipelineExecutionError` and `PipelineOverrideError`, while
  `PipelineConnectionError` and `PipelineCycleError` remain in
  [pipeline.py](src/data_joinery/pipeline.py). These are documented failures of
  public connection methods, so users need clear imports for catching them.
- [ ] Document compatibility for module moves. `backends.base` and legacy Spark
  helpers in [type_inspection.py](src/data_joinery/type_inspection.py) still
  forward imports; the former root `dependencies`, `model_schema`, and
  `schema_types` modules have been removed. Explain supported paths and required
  migrations.

Intentional re-exports are live API and should remain unless a separate API change
removes them.

### Public API docstrings

Several public definitions still lack the Google-style docstrings required by
`AGENTS.md`.

- [ ] Document the annotation helpers in
  [type_inspection.py](src/data_joinery/type_inspection.py).
- [ ] Document `ModelField`, `ModelSchema`, `ModelSchema.from_model()`, and model
  inspection helpers in
  [schemas/model_schema.py](src/data_joinery/schemas/model_schema.py).
- [ ] Document `SchemaDifference`, `SchemaDiff`, and `SchemaCoercionError` in
  [schemas/coercion.py](src/data_joinery/schemas/coercion.py), including their
  diagnostic attributes.
- [ ] Complete missing public class and method docstrings in
  [contract.py](src/data_joinery/contract.py) and
  [transform.py](src/data_joinery/transform.py), and document the connection
  exceptions in `pipeline.py`.

## Optional refactors

### Backend coercion

Each backend already separates operations from native type conversion.
[backends/spark/backend.py](src/data_joinery/backends/spark/backend.py) still
combines casting rules, schema comparison, projection, nullability handling, and
protocol implementation.

- [ ] If navigation or maintenance becomes difficult, extract native coercion
  within the Spark package and have the backend delegate to it.

Keep schema traversal, cast compatibility, and expression construction specific
to each backend. The smaller Polars module does not need an extraction simply to
match Spark's layout. Share coercion policy only where it clearly reduces
maintenance work.

### Pipeline construction and execution

[pipeline.py](src/data_joinery/pipeline.py) still owns step operators, graph
connections, context and override validation, execution, and logging.
[pipeline_result.py](src/data_joinery/pipeline_result.py) already separates results
and recorded inputs.

- [ ] If further execution features make this difficult to maintain, extract a
  runner for invoking steps and collecting results, with `Pipeline.run()`
  delegating to it.
- [ ] Preserve step identity, connection semantics, override rules, side effects,
  result inspection, logging, and execution error context.

A `pipeline/` package is only useful if that extraction establishes clear
responsibilities. Moving the existing class into a directory or spreading it
across mixins would not address the concern.

## Priority and verification

Clarify public imports and complete docstrings first. The current layout does not
need another broad reorganization. Keep `contract.py` separate from schema
internals, retain backend ownership of native type conversion, and leave small
helper and integration modules in place unless a concrete maintenance problem
justifies moving them.

For implementation work, use `uv` and existing `just` recipes. Run `just check`
and `just docs-build`; for package moves, also build and inspect the wheel with
`uv build`. Keep tests aligned with source paths, verify affected import
boundaries, and update runnable examples and packaged skills when their documented
API changes.
