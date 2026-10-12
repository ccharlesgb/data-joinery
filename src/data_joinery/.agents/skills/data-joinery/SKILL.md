---
name: data-joinery
description: Orient work that uses Data Joinery and route schema, transformation, pipeline, query-plan inspection, or project-layout tasks to the focused skills.
---

# Data Joinery

Data Joinery is a schema-first framework for testable DataFrame transformations. It supports
PySpark and Polars and can be used in three independent layers:

1. `Schema(Model)` turns a dataclass or Pydantic model into a backend schema, creates fixture
   DataFrames, and coerces existing DataFrames.
2. `@transform` gives DataFrame parameters and return values runtime schema contracts.
3. `Pipeline` connects transforms into a validated directed graph and injects typed context.

For Polars, both `pl.LazyFrame` and `pl.DataFrame` are supported. Prefer `pl.LazyFrame` so
operations can remain lazy until the result is needed; use `pl.DataFrame` when eager data is
appropriate.

Use only the lowest layer the task needs. A caller can use schemas without decorated transforms,
and decorated transforms without a pipeline.

## Route the task

- For defining models, backend type mappings, fixture DataFrames, or coercing a frame, use
  `data-joinery-schemas`.
- For declaring contracts, implementing a transform, or unit testing one transform, use
  `data-joinery-transformations`.
- For connecting steps, injecting context, marking or skipping side effects, visualizing a graph,
  inspecting run results, using per-run overrides, or testing a complete pipeline, use
  `data-joinery-pipelines`.
- For inspecting or comparing PySpark or Polars query execution plans from pipeline outputs, use
  `data-joinery-plan-inspection`.
- For deciding where code belongs in a new or existing application repository, use
  `data-joinery-project-layout`.

Use every focused skill that applies when a task crosses layers. For example, a new end-to-end
pipeline normally needs the schema, transformation, and pipeline skills. The project-layout skill
owns file and module organization; do not repeat its structural conventions in the API-focused
skills.

## Core vocabulary

- A **model** is a dataclass or Pydantic model describing logical fields independently of the
  DataFrame backend.
- A **schema** is `Schema(Model)`, which compiles the model for a selected backend.
- A **contract** is metadata such as `Strict(Model)` or `Project(Model)` on an `Annotated`
  DataFrame type.
- A **transform** is a function decorated with `@transform` or `@side_effect`; contracts are
  enforced when it runs.
- A **side-effect transform** uses `@side_effect` to mark a terminal action that a pipeline can
  skip. It still runs when called directly.
- A **step** is one named use of a transform in a pipeline. The same transform can be added more
  than once as distinct steps.
- **Context** is typed runtime configuration or a dependency injected into transforms marked with
  `Context()`.

Prefer models and wrapper classes whose names describe domain meaning. This is especially useful
for ordinary values passed through a pipeline because instance contracts validate runtime classes,
not the contents of generic containers.

Pipeline syntax is currently experimental. Keep pipeline-specific code localized so callers and
tests do not depend on graph internals unnecessarily.
