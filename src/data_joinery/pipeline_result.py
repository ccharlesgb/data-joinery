"""The values and input bindings observed during a pipeline run."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast, overload

if TYPE_CHECKING:
    from .pipeline import Step
    from .transform import Transform


@dataclass(frozen=True)
class ContextSource:
    """Identify the context field that supplied an input.

    Attributes:
        field: Name of the context field.
    """

    field: str


@dataclass(frozen=True)
class DefaultSource:
    """Identify an input supplied by a transform parameter default."""


@dataclass(frozen=True)
class BoundInput:
    """Record an input value and where it came from.

    Attributes:
        value: Value passed to the transform before input coercion.
        source: Upstream step, context field, or parameter default.
    """

    value: object
    source: Step[Any] | ContextSource | DefaultSource


@dataclass(frozen=True)
class StepRun[OutputT]:
    """Record one step's transform, inputs, and output.

    Attributes:
        step: Step that ran.
        transform: Transform used, including any replacement supplied at run time.
        inputs: Values bound to parameter names before input coercion.
        output: Validated output, including ``None`` for a writer step.
    """

    step: Step[OutputT]
    transform: Transform[..., OutputT]
    inputs: Mapping[str, BoundInput]
    output: OutputT


class PipelineResult(Mapping[str, Any]):
    """Record a pipeline run and provide access to its step outputs.

    Mapping access by step name includes only outputs other than ``None``.
    ``step_runs`` includes every step in execution order.

    Args:
        step_runs: Run records in execution order.

    Attributes:
        step_runs: Run records for every step, including steps with no output.
    """

    def __init__(self, step_runs: tuple[StepRun[Any], ...]) -> None:
        self.step_runs = step_runs
        self._by_step_name = {step_run.step.name: step_run for step_run in step_runs}
        self._outputs = {
            step_run.step.name: step_run.output
            for step_run in step_runs
            if step_run.output is not None
        }

    def __getitem__(self, step_name: str) -> Any:
        """Get a non-None output by step name, or raise `KeyError`."""
        return self._outputs[step_name]

    def __iter__(self) -> Iterator[str]:
        """Iterate over step names with non-None outputs in execution order."""
        return iter(self._outputs)

    def __len__(self) -> int:
        """Return the number of non-None outputs."""
        return len(self._outputs)

    @overload
    def get_step_run[T](self, step: Step[T]) -> StepRun[T]: ...

    @overload
    def get_step_run(self, step: str) -> StepRun[Any]: ...

    def get_step_run(self, step: Step[Any] | str) -> StepRun[Any]:
        """Get a step's run record, including steps that return `None`.

        Args:
            step: A step from this pipeline or its name. A step object must be
                the same object that was run, not just have the same name.

        Returns:
            The step's recorded inputs and output.

        Raises:
            KeyError: If the step name is absent or the step object was not run.
        """
        if isinstance(step, str):
            return self._by_step_name[step]
        step_run = self._by_step_name.get(step.name)
        if step_run is None or step_run.step is not step:
            raise KeyError(f"Step '{step.name}' is not in this pipeline result.")
        return step_run

    @overload
    def get_output[T](self, step: Step[T]) -> T: ...

    @overload
    def get_output[T](self, step: str, value_type: type[T]) -> T: ...

    def get_output(
        self, step: Step[Any] | str, value_type: type[Any] | None = None
    ) -> Any:
        """Get a step's output.

        A `Step` keeps its declared output type. When using a step name, pass
        the expected runtime type.

        Args:
            step: A step from this pipeline or its name.
            value_type: Required runtime type when `step` is a name.

        Returns:
            The step's output, including `None` for a step that returns it.

        Raises:
            KeyError: If the step is absent.
            TypeError: If the type is missing for a name, supplied for a `Step`,
                or does not match the named output.
        """
        if not isinstance(step, str):
            if value_type is not None:
                raise TypeError("Pass value_type only when looking up a step by name.")
            return self.get_step_run(step).output
        if value_type is None:
            raise TypeError("Looking up an output by step name requires value_type.")
        value = self._by_step_name[step].output
        if not isinstance(value, value_type):
            raise TypeError(
                f"Output of step '{step}' is {type(value).__name__}, "
                f"expected {value_type.__name__}."
            )
        return value

    def get_input[T](
        self, step: Step[Any] | str, parameter_name: str, value_type: type[T]
    ) -> T:
        """Get a value bound to a step's input parameter before input coercion.

        Args:
            step: A step from this pipeline or its name.
            parameter_name: Name of the transform parameter.
            value_type: Required runtime type of the bound value.

        Returns:
            The recorded input value.

        Raises:
            KeyError: If the step or parameter is absent.
            TypeError: If the value is not an instance of `value_type`.
        """
        step_run = self.get_step_run(step)
        binding = step_run.inputs[parameter_name]
        if not isinstance(binding.value, value_type):
            raise TypeError(
                f"Input '{parameter_name}' of step '{step_run.step.name}' is "
                f"{type(binding.value).__name__}, expected {value_type.__name__}."
            )
        return cast(T, binding.value)

    def get_one_input[T](self, step: Step[Any] | str, value_type: type[T]) -> T:
        """Get the only recorded input of a runtime type before input coercion.

        All bound inputs are considered, including context values and defaults.
        Use `get_input` with a parameter name if more than one value matches.

        Args:
            step: A step from this pipeline or its name.
            value_type: Runtime type to match with `isinstance`.

        Returns:
            The single matching input value.

        Raises:
            KeyError: If the step is absent.
            LookupError: If zero or multiple inputs match `value_type`.
        """
        step_run = self.get_step_run(step)
        matches = [
            binding.value
            for binding in step_run.inputs.values()
            if isinstance(binding.value, value_type)
        ]
        if len(matches) != 1:
            raise LookupError(
                f"Expected exactly one input of type {value_type.__name__} "
                f"for step '{step_run.step.name}'; found {len(matches)}."
            )
        return cast(T, matches[0])


def bound_inputs(
    values: Mapping[str, object],
    sources: Mapping[str, Step[Any] | ContextSource],
) -> Mapping[str, BoundInput]:
    """Freeze input bindings, marking parameters supplied by defaults."""
    return MappingProxyType(
        {
            parameter_name: BoundInput(
                value, sources.get(parameter_name, DefaultSource())
            )
            for parameter_name, value in values.items()
        }
    )
