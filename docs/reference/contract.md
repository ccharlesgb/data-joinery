# Contracts

Use these helpers in `Annotated` DataFrame parameters and return types to
choose how a transform checks a schema. Each helper takes a dataclass or
Pydantic model.

::: data_joinery.contract.Strict

::: data_joinery.contract.ProjectTopLevel

::: data_joinery.contract.Project

::: data_joinery.contract.ProjectCast

`Project` is also the default mode for `Schema.coerce_dataframe()`.

## No output

::: data_joinery.contract.VoidContract
