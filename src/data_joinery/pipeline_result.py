"""The values and input bindings observed during a pipeline invocation."""

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
class StepInvocation[OutputT]:
    """Record one step invocation's transform, inputs, and output.

    Attributes:
        step: Step that was invoked.
        transform: Transform used, including any replacement supplied to the run.
        inputs: Values bound to parameter names before input coercion.
        output: Validated output, including ``None`` for a writer step.
    """

    step: Step[OutputT]
    transform: Transform[..., OutputT]
    inputs: Mapping[str, BoundInput]
    output: OutputT


class PipelineResult(Mapping[str, Any]):
    """Record a pipeline invocation and provide access to step outputs.

    Mapping access by step name includes only outputs other than ``None``.
    ``step_invocations`` includes every invoked step in dependency order.

    Args:
        step_invocations: Invocation records in dependency order.

    Attributes:
        step_invocations: Records for every invoked step, including writers.
    """

    def __init__(self, step_invocations: tuple[StepInvocation[Any], ...]) -> None:
        self.step_invocations = step_invocations
        self._by_step_name = {
            invocation.step.name: invocation for invocation in step_invocations
        }
        self._outputs = {
            invocation.step.name: invocation.output
            for invocation in step_invocations
            if invocation.output is not None
        }

    def __getitem__(self, step_name: str) -> Any:
        """Get a non-None output by step name, or raise `KeyError`."""
        return self._outputs[step_name]

    def __iter__(self) -> Iterator[str]:
        """Iterate over step names with non-None outputs in invocation order."""
        return iter(self._outputs)

    def __len__(self) -> int:
        """Return the number of non-None outputs."""
        return len(self._outputs)

    @overload
    def get_step_invocation[T](self, step: Step[T]) -> StepInvocation[T]: ...

    @overload
    def get_step_invocation(self, step: str) -> StepInvocation[Any]: ...

    def get_step_invocation(self, step: Step[Any] | str) -> StepInvocation[Any]:
        """Get a step's invocation record, including steps that return `None`.

        Args:
            step: A step from this pipeline or its name. A step object must be
                the same object that was invoked, not just have the same name.

        Returns:
            The step invocation's recorded inputs and output.

        Raises:
            KeyError: If the step name is absent or the step was not invoked.
        """
        if isinstance(step, str):
            return self._by_step_name[step]
        invocation = self._by_step_name.get(step.name)
        if invocation is None or invocation.step is not step:
            raise KeyError(f"Step '{step.name}' is not in this pipeline result.")
        return invocation

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
            return self.get_step_invocation(step).output
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
        invocation = self.get_step_invocation(step)
        binding = invocation.inputs[parameter_name]
        if not isinstance(binding.value, value_type):
            raise TypeError(
                f"Input '{parameter_name}' of step '{invocation.step.name}' is "
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
        invocation = self.get_step_invocation(step)
        matches = [
            binding.value
            for binding in invocation.inputs.values()
            if isinstance(binding.value, value_type)
        ]
        if len(matches) != 1:
            raise LookupError(
                f"Expected exactly one input of type {value_type.__name__} "
                f"for step '{invocation.step.name}'; found {len(matches)}."
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
