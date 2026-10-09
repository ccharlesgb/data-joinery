# Adding a dataframe backend

A backend connects one dataframe class and one native schema class to Data Joinery. The
`DataFrameBackend[Frame, NativeSchema]` protocol makes those types part of the interface:
`create_dataframe` and `coerce_dataframe` return `Frame`, while `compile_schema` returns
`NativeSchema`. Register one backend instance with `register_backend`.

## What to implement

| Member | What it does |
| --- | --- |
| `name` | Gives the backend a unique name. |
| `dataframe_type` | Identifies the frame class accepted and returned by this backend. |
| `schema_type` | Identifies the native schema class returned by `compile_schema`. |
| `compile_schema(schema)` | Maps each `ModelSchema` field and annotation to a native schema. Handle nested and backend-specific field types here. |
| `create_dataframe(rows, schema, **kwargs)` | Checks the model rows, builds a frame with the compiled schema, and handles backend-specific options. Reject unknown options. |
| `coerce_dataframe(frame, schema, mode)` | Checks or reshapes a frame according to the requested mode. Return the same frame class or raise `SchemaCoercionError` for schema mismatches. |

The four coercion modes have distinct promises:

| Mode | Required behavior |
| --- | --- |
| `strict` | Check field names and types without removing or casting fields. Extra and missing fields fail. |
| `project_top_level` | Remove extra top-level fields. Check nested fields and types without changing them. |
| `project` | Remove extra fields, including nested fields. Check types without casting. |
| `project_cast` | Project fields and cast types where the native library allows it. Report casts that cannot be made. |

Every mode rejects missing fields. See [Coercing Schemas](../learn/schemas/coercion.md)
for the user-facing behavior. Use `SchemaCoercionError` and `SchemaDifference` to describe
missing, additional, and mismatched fields.

## A small example

This toy frame holds only column names, so its native schema is a tuple of names. It
shows the registration and method shapes; a real backend must also handle values,
field types, and nested fields.

``` python
--8<-- "docs_src/internals/backends.py"
```

:fontawesome-solid-code: Outputs:

``` text
--8<-- "docs_src/internals/backends_stdout.log"
```

`dataframe_type` and `schema_type` each take a single class. Subclasses are recognized
when finding a backend; when creating a frame or native schema, the returned object
must also match the class requested by the caller. Registration rejects duplicate
names and overlapping frame or schema classes across backends, so each type has one
clear owner.

## Connecting it to the rest of the library

Register the backend before using its frame or schema class. `Schema.native_schema()`
finds it by `schema_type`; `Schema.create_dataframe()` and frame coercion find it by
`dataframe_type`. Transform annotations use the same lookup.

Put the backend's native type mapping, row conversion, schema comparison, projection,
and casting rules in its implementation. The built-in Polars and PySpark backends are
complete examples in `src/data_joinery/backends/`. Add tests under `tests/backends/`
for registration, all four modes, nested fields, bad rows, bad options, and unsupported
casts. Run `just check` and `just docs-build` before shipping it.
