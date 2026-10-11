# Pipeline

::: data_joinery.Pipeline

## Steps

::: data_joinery.Step

## Context

::: data_joinery.Context

## Pipeline results

`Pipeline.run()` returns a `PipelineResult`. Use a `Step` or a step name to
select the output you want. The result also acts as a mapping from step names
to non-`None` outputs.

| Method | Use |
| --- | --- |
| [`get_output`](#data_joinery.PipelineResult.get_output) | Read a step's output. Pass the expected runtime type when using a name. |
| [`get_input`](#data_joinery.PipelineResult.get_input) | Read a value bound to a step's input parameter, including writers. |
| [`get_one_input`](#data_joinery.PipelineResult.get_one_input) | Read the only input of a runtime type without naming its parameter. |
| [`get_step_invocation`](#data_joinery.PipelineResult.get_step_invocation) | Inspect an invocation's inputs, output, and input sources. |

::: data_joinery.PipelineResult

`StepInvocation` records the transform called for a step, its bound inputs,
and its returned output. A lazy DataFrame can defer data processing until a
later operation.

::: data_joinery.StepInvocation

::: data_joinery.BoundInput

`BoundInput.source` identifies the upstream `Step`, a context field, or a
parameter default.

::: data_joinery.ContextSource

::: data_joinery.DefaultSource

## Logging

`Pipeline.run()` logs invocation summaries at INFO and step details at DEBUG
through the `data_joinery` logger. Configure this logger in your application
to choose the level, format, and destination. A step's logged duration measures
the transform call, which may return a lazy DataFrame before its data is
processed. Logs include step names, transform names, context field names, call
durations, and return types, but not input, context, or output values.

## Errors

::: data_joinery.PipelineExecutionError

::: data_joinery.PipelineOverrideError
