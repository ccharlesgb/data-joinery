# Pipeline

::: data_joinery.Pipeline

## Pipeline results

`Pipeline.run()` returns a `PipelineResult`. Use a `Step` or a step name to
select the output you want. The result also acts as a mapping from step names
to non-`None` outputs.

| Method | Use |
| --- | --- |
| [`get_output`](#data_joinery.PipelineResult.get_output) | Read a step's output. Pass the expected runtime type when using a name. |
| [`get_input`](#data_joinery.PipelineResult.get_input) | Read a value bound to a step's input parameter, including writers. |
| [`get_one_input`](#data_joinery.PipelineResult.get_one_input) | Read the only input of a runtime type without naming its parameter. |
| [`get_step_run`](#data_joinery.PipelineResult.get_step_run) | Inspect the complete run record, including input sources. |

::: data_joinery.PipelineResult

`StepRun` records the transform used, its bound inputs, and its output.

::: data_joinery.StepRun

::: data_joinery.BoundInput
