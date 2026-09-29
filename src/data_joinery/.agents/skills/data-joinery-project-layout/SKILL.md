---
name: data-joinery-project-layout
description: Structure or extend Python data-joinery pipeline projects using clear boundaries for context, schemas, transforms, pipeline wiring, execution, and tests. Use when creating a data-joinery project or deciding where new pipeline code belongs.
---

# Data Joinery Project Layout

Organize data-joinery projects so pipeline definitions remain declarative, transforms remain independently testable, and runtime configuration is explicit.

## Respect Existing Projects

Before changing an existing project, inspect its current layout, configuration, naming, imports, tests, and working-tree state.

Treat the layout below as a greenfield default, not a migration mandate.

- Preserve established conventions when they already provide clear ownership.
- Make the smallest change that satisfies the request.
- Add code to the existing equivalent module instead of creating duplicate abstractions.
- Do not rename, relocate, or reorganize existing files merely to match this layout.
- Do not overwrite project configuration, dependency choices, scripts, generated data, or unrelated user changes.
- Keep compatibility with the project’s current Python version, build system, dataframe technologies, and test approach.
- Propose broad restructuring separately unless the user explicitly requests it.

When local project instructions conflict with this skill, follow the local instructions.

## Recommended Greenfield Layout

Use a standard Python `src` layout:

```text
<project>/
├── pyproject.toml
├── data/                         # Optional local fixtures or example inputs
├── __output/                     # Optional generated local output
├── src/
│   └── <package_name>/
│       ├── __init__.py
│       ├── __main__.py
│       ├── context.py
│       ├── schemas.py
│       ├── transform.py
│       └── pipeline.py
└── tests/
    ├── test_transform.py
    └── test_pipeline.py          # Add when end-to-end graph behavior needs coverage
The directory and distribution names may use hyphens, while the importable Python package uses underscores.
Only create optional directories and test modules when the project needs them.
Module Responsibilities
context.py
Define runtime dependencies supplied to the pipeline rather than produced by another transform.
Typical context values include:
- Spark or other execution sessions
- Input and output paths
- Run dates
- Environment-specific settings
- External clients
Represent the complete pipeline context with a frozen dataclass. Extend an appropriate data-joinery context class when the installed API provides one.
Use distinct marker types for semantically different values that share the same primitive representation:
class OrdersPath(str):
    """Path containing source orders."""


class OutputPath(str):
    """Destination for pipeline output."""


@dataclass(frozen=True)
class PipelineContext(SparkContext):
    orders_path: OrdersPath
    output_path: OutputPath
Marker types let data-joinery resolve dependencies by meaning rather than treating every string, date, or path as interchangeable.
schemas.py
Define the logical records exchanged by transforms.
Prefer focused dataclasses whose fields describe the expected columns and Python value types. Create separate schemas for materially different stages, such as source records, enriched records, features, predictions, or metrics.
Schema inheritance is appropriate when an output genuinely extends an input record. Do not force inheritance when the records represent different concepts.
Keep transformation logic and runtime configuration out of this module.
transform.py
Define the pipeline’s executable units with @transform.
Each transform should:
- Perform one coherent read, transformation, model, write, or reporting operation.
- Declare context dependencies with Annotated[..., Context()].
- Declare dataframe contracts using the data-joinery schema annotations appropriate to the installed version, such as Project, ProjectCast, or Strict.
- Return values for downstream steps instead of reaching into the pipeline graph.
- Avoid constructing or running the pipeline itself.
- Be callable directly in focused tests.
Keep related constants near the transforms that use them unless the project already has an established configuration module.
Split transform.py into a transforms/ package only when its size or distinct domains make that separation useful. Do not introduce the package preemptively.
pipeline.py
Own graph construction, not business logic.
Expose a function such as:
def build_pipeline() -> Pipeline[PipelineContext]:
    ...
Inside it:
1. Construct the pipeline with its context type.
2. Register transforms with add_step.
3. Connect producer and consumer steps.
4. Specify a target parameter when dependency inference would be ambiguous.
5. Return the unexecuted pipeline.
Assign each registered step to a variable that describes its result. This makes graph wiring readable.
Use explicit step names when they are needed for stable output lookup, transform overrides, or compatibility with existing callers. Otherwise follow the project’s current convention.
Keep filesystem defaults close to pipeline construction only when they are example-project defaults. Production paths and run-specific values normally belong in the context supplied at runtime.
__main__.py
Provide the executable entry point for local or packaged execution.
It may:
- Create runtime services such as a Spark session.
- Build concrete context values.
- Call build_pipeline().
- Run the pipeline.
- Display or otherwise handle selected outputs.
- Shut down resources reliably.
Keep transforms and graph construction out of this module. Use try/finally or a suitable context manager when a runtime resource must always be closed.
__init__.py
Keep package initialization lightweight. A package docstring or deliberately chosen public exports are sufficient.
Do not start sessions, read data, or execute a pipeline during import.
tests/
Test transforms directly wherever possible. Construct small schema-valid inputs and assert observable output values, columns, or side effects.
Use temporary paths for read/write tests so test runs do not alter repository data or generated output.
Add a pipeline-level test when it provides value beyond transform tests, including:
- Verifying graph wiring
- Exercising fan-in or branching
- Checking named pipeline outputs
- Testing transform overrides
- Confirming interoperability between dataframe or model types
Reuse existing fixtures and assertion libraries rather than introducing a parallel testing style.
pyproject.toml
Configure the project as a normal src-layout Python package and declare only the dependencies it owns.
When the project is part of a workspace, first determine whether dependencies and development tools are managed by the workspace root. Do not duplicate or move that configuration without a concrete need.
Ensure the build configuration points to src/<package_name> when the project is independently buildable.
Data and Output Directories
Use data/ for small, intentional fixtures or runnable-example inputs. Do not assume production datasets belong in the repository.
Use a clearly identified output directory such as __output/ only for local generated artifacts. Follow the repository’s existing ignore and cleanup policy, and never overwrite existing data merely to demonstrate the layout.
Adding a Pipeline Feature
When extending a project:
1. Inspect the existing modules and identify their actual responsibilities.
2. Add or update schema types when the data contract changes.
3. Add required runtime values and marker types to the existing context.
4. Implement the smallest independently testable transform.
5. Register and connect it in the existing pipeline builder.
6. Update the entry point only if runtime construction or output handling changes.
7. Add focused tests using the project’s established style.
8. Run the narrowest relevant tests and the repository’s configured checks.
Do not create every recommended file for a small change. Use the project’s current structure unless a missing boundary is causing a concrete problem.