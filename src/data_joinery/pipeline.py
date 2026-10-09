from __future__ import annotations

import inspect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, overload

import rustworkx as rx

try:
    from matplotlib import pyplot as plt
except ModuleNotFoundError as error:
    if error.name != "matplotlib":
        raise
    plt = None
    _MATPLOTLIB_AVAILABLE = False
else:
    _MATPLOTLIB_AVAILABLE = True

from data_joinery.contract import (
    Contract,
    DataFrameContract,
    VoidContract,
    describe_contract,
)
from data_joinery.dependencies import inspect_context_type
from data_joinery.pipeline_result import (
    ContextSource,
    PipelineResult,
    StepRun,
    bound_inputs,
)
from data_joinery.transform import Transform
from data_joinery.visualisation import draw_pipeline


class PipelineExecutionError(RuntimeError):
    """A pipeline could not run or one of its steps failed."""


class PipelineCycleError(Exception):
    pass


class PipelineConnectionError(Exception):
    pass


class PipelineOverrideError(ValueError):
    """A replacement transform is unknown or incompatible with its step."""


@dataclass(eq=False, frozen=True)
class Step[OutputT]:
    """A named use of a transform in a pipeline.

    The same transform can be added as more than one step.

    Attributes:
        name: Name used to identify the step in its pipeline and result.
        transform: Transform called when the step runs.
    """

    name: str
    transform: Transform[..., OutputT]
    _pipeline: Pipeline[Any]

    def __rshift__[OtherT](self, other: Step[OtherT]) -> Step[OtherT]:
        """Connect this step to another and return the downstream step.

        This is shorthand for ``pipeline.connect(self, other)``. Use
        ``Pipeline.connect`` to choose an input parameter when needed.
        """
        if not isinstance(other, Step):
            raise TypeError(
                f"Can only connect Step instances using >>; got {type(other).__name__}."
            )
        self._pipeline.connect(self, other)
        return other


class Pipeline[ContextT]:
    """Connect transforms and run them in dependency order.

    Args:
        context_type: Optional context dataclass. Pass its class when
            transforms use the ``Context`` marker.
    """

    @overload
    def __init__(self: Pipeline[None]) -> None: ...

    @overload
    def __init__(self, context_type: type[ContextT]) -> None: ...

    def __init__(self, context_type: type[ContextT] | None = None):
        self._dag = rx.PyDAG(check_cycle=True)
        self._node_indices: dict[Step[Any], int] = {}
        self._steps_by_name: dict[str, Step[Any]] = {}
        self._context_type = context_type
        self._context_fields = (
            inspect_context_type(context_type) if context_type is not None else {}
        )

    @staticmethod
    def _validate_transform_parameters(transform: Transform) -> None:
        spec = transform.__transform_spec__
        parameter_names = set(transform.get_signature().parameters)
        supported_parameters = set(spec.input_contracts) | set(spec.context_parameters)
        unsupported_parameters = parameter_names - supported_parameters
        if unsupported_parameters:
            unsupported = min(unsupported_parameters)
            raise TypeError(
                f"Transform '{transform.default_name}' parameter '{unsupported}' has no "
                "supported contract. Annotate it with a runtime class, a DataFrame "
                "contract, or Context()."
            )

    def add_step[**P, OutputT](
        self, transform: Transform[P, OutputT], name: str | None = None
    ) -> Step[OutputT]:
        """Add a transform as a named step.

        Args:
            transform: Function decorated with ``@transform``.
            name: Step name. Defaults to the transform's function name.

        Returns:
            The new step.

        Raises:
            ValueError: If the name is already used or cannot be inferred.
            TypeError: If the transform has unsupported parameters or context
                dependencies that the pipeline cannot supply.
        """
        if not isinstance(transform, Transform):
            raise TypeError(
                "add_step() requires a function decorated with @transform; "
                f"got {type(transform).__name__}."
            )
        if name is None:
            name = transform.default_name
        if name is None:
            raise ValueError(
                "Cannot infer a name for this transform. Pass name='step_name' "
                "to add_step()."
            )
        if name in self._steps_by_name:
            raise ValueError(
                f"Step name '{name}' is already registered. Choose a unique name."
            )

        self._validate_transform_parameters(transform)
        self._validate_transform_context(transform)

        step = Step(
            name=name,
            transform=transform,
            _pipeline=self,
        )
        node_index = self._dag.add_node(step)
        self._node_indices[step] = node_index
        self._steps_by_name[name] = step
        return step

    def _validate_transform_context(self, transform: Transform) -> None:
        for parameter_name, (
            param_type,
            marker,
        ) in transform.__transform_spec__.context_parameters.items():
            dependency_type = marker.type or param_type
            if dependency_type not in self._context_fields:
                transform_name = transform.default_name or repr(transform)
                context_name = (
                    self._context_type.__name__
                    if self._context_type is not None
                    else "a context-free pipeline"
                )
                raise TypeError(
                    f"Transform '{transform_name}' parameter '{parameter_name}' requires "
                    f"context dependency {dependency_type.__name__}, but {context_name} "
                    "does not provide it. Add a field of that type to the context "
                    "dataclass or change the Context annotation."
                )

    def connect(
        self, upstream: Step, downstream: Step, *, param: str | None = None
    ) -> None:
        """Connect an output to a compatible input on another step.

        Args:
            upstream: Step that produces the value.
            downstream: Step that receives the value.
            param: Downstream parameter name. Required when more than one
                input can accept the output.

        Raises:
            PipelineConnectionError: If the steps or their contracts cannot
                be connected.
            PipelineCycleError: If the connection would create a cycle.
        """
        for role, step in (("upstream", upstream), ("downstream", downstream)):
            if not isinstance(step, Step):
                raise TypeError(
                    f"{role.capitalize()} must be a Step; got {type(step).__name__}."
                )
            if step._pipeline is not self:
                raise PipelineConnectionError(
                    f"{role.capitalize()} step '{step.name}' belongs to another "
                    "pipeline. Add it to this pipeline before connecting it."
                )

        downstream_spec = downstream.transform.__transform_spec__
        upstream_spec = upstream.transform.__transform_spec__

        upstream_contract = upstream_spec.output_contract
        if isinstance(upstream_contract, VoidContract):
            raise PipelineConnectionError(
                f"Upstream step '{upstream.name}' produces None. Declare an output "
                "contract on its transform or connect a step that produces a value."
            )

        compatible_specs: dict[str, Contract] = {}
        for param_name, input_contract in downstream_spec.input_contracts.items():
            if input_contract.accepts(upstream_contract):
                compatible_specs[param_name] = input_contract

        if len(compatible_specs) > 1:
            if param is None:
                names = ", ".join(sorted(compatible_specs))
                raise PipelineConnectionError(
                    f"Step '{upstream.name}' produces {describe_contract(upstream_contract)}, "
                    f"which matches multiple inputs on '{downstream.name}': {names}. "
                    "Pass param='input_name' to connect()."
                )
            if param not in compatible_specs:
                names = ", ".join(sorted(compatible_specs))
                raise PipelineConnectionError(
                    f"Input '{param}' on step '{downstream.name}' is not compatible "
                    f"with '{upstream.name}' ({describe_contract(upstream_contract)}). "
                    f"Choose one of: {names}."
                )
            downstream_parameter_name = param
        elif len(compatible_specs) == 1:
            compatible_parameter = next(iter(compatible_specs))
            if param is not None and param != compatible_parameter:
                raise PipelineConnectionError(
                    f"Input '{param}' on step '{downstream.name}' does not match "
                    f"the output of '{upstream.name}' ({describe_contract(upstream_contract)}). "
                    f"Connect to the compatible input '{compatible_parameter}'."
                )
            downstream_parameter_name = compatible_parameter
        else:
            inputs = [
                f"    '{name}': {describe_contract(contract)}"
                for name, contract in downstream_spec.input_contracts.items()
            ] or ["    none"]
            inputs_text = "\n".join(inputs)
            requested = f"\n  Requested input: '{param}'" if param else ""
            action = (
                "Add an annotated input parameter to the downstream transform."
                if not downstream_spec.input_contracts
                else (
                    "Change an input or output annotation so their DataFrame "
                    "backends, types, and schema models match."
                    if isinstance(upstream_contract, DataFrameContract)
                    else "Change an input or output annotation so the produced "
                    "value type matches an input."
                )
            )
            raise PipelineConnectionError(
                f"No compatible contract between steps '{upstream.name}' and "
                f"'{downstream.name}':\n"
                f"  Output of '{upstream.name}': {describe_contract(upstream_contract)}\n"
                f"  Inputs of '{downstream.name}':\n"
                f"{inputs_text}{requested}\n"
                f"{action}"
            )

        downstream_index = self._node_indices[downstream]
        for connected_upstream_index, _, connected_parameter_name in self._dag.in_edges(
            downstream_index
        ):
            if connected_parameter_name != downstream_parameter_name:
                continue
            if connected_upstream_index == self._node_indices[upstream]:
                return
            connected_upstream = self._dag[connected_upstream_index]
            raise PipelineConnectionError(
                f"Step '{connected_upstream.name}' is already connected to "
                f"'{downstream.name}' input '{downstream_parameter_name}'. "
                "Disconnect that input before connecting another step."
            )

        try:
            self._dag.add_edge(
                self._node_indices[upstream],
                downstream_index,
                downstream_parameter_name,
            )
        except rx.DAGWouldCycle:
            raise PipelineCycleError(
                f"Connecting step '{upstream.name}' to '{downstream.name}' would "
                "create a cycle. Remove a connection so the steps form a DAG."
            )

    def connect_many(
        self,
        upstream_steps: Sequence[Step],
        downstream: Step,
    ) -> None:
        """Connect several upstream steps to one downstream step.

        Each output must match one unambiguous downstream input.

        Args:
            upstream_steps: Nonempty sequence of steps that provide inputs.
            downstream: Step that receives the inputs.

        Raises:
            ValueError: If ``upstream_steps`` is empty.
            PipelineConnectionError: If an output cannot be connected.
            PipelineCycleError: If a connection would create a cycle.
        """
        if not upstream_steps:
            raise ValueError(
                "connect_many requires at least one upstream step. Pass a nonempty "
                "sequence of Step instances."
            )
        for upstream in upstream_steps:
            self.connect(upstream, downstream)

    def get_upstream_steps(self, step: Step) -> set[Step]:
        """Return the steps directly connected to ``step`` as inputs."""
        return set(self._dag.predecessors(self._node_indices[step]))

    def get_steps_in_execution_order(self) -> list[Step]:
        """Return all steps in an order that respects their connections."""
        node_indices = rx.topological_sort(self._dag)
        return [self._dag[node_index] for node_index in node_indices]

    def _validate_source_steps(self, overrides: Mapping[str, Transform]) -> None:
        for step, step_index in self._node_indices.items():
            if self._dag.in_degree(step_index) != 0:
                continue
            effective_transform = overrides.get(step.name, step.transform)
            signature = effective_transform.get_signature()
            required = [
                name
                for name in effective_transform.__transform_spec__.input_contracts
                if signature.parameters[name].default is inspect.Parameter.empty
            ]
            if required:
                raise PipelineExecutionError(
                    f"Pipeline step '{step.name}' requires upstream inputs: "
                    f"{', '.join(required)}. "
                    "Connect steps that produce these inputs."
                )

    def _validate_transform_override(self, step: Step, replacement: Transform) -> None:
        self._validate_transform_parameters(replacement)
        original = step.transform.__transform_spec__
        override = replacement.__transform_spec__

        if original.input_contracts.keys() != override.input_contracts.keys():
            expected = ", ".join(original.input_contracts) or "<none>"
            actual = ", ".join(override.input_contracts) or "<none>"
            raise PipelineOverrideError(
                f"transform override for step '{step.name}' has different input "
                f"parameters; expected: {expected}; got: {actual}"
            )

        for name, original_contract in original.input_contracts.items():
            if not override.input_contracts[name].accepts(original_contract):
                raise PipelineOverrideError(
                    f"Transform override for step '{step.name}' has an incompatible "
                    f"contract for input '{name}': expected "
                    f"{describe_contract(original_contract)}, got "
                    f"{describe_contract(override.input_contracts[name])}. "
                    "Declare a compatible input contract."
                )

        if original.output_contract != override.output_contract:
            raise PipelineOverrideError(
                f"Transform override for step '{step.name}' must declare the same "
                f"output contract: expected {describe_contract(original.output_contract)}, "
                f"got {describe_contract(override.output_contract)}. "
                "Change the replacement's return annotation."
            )

        original_context_types = {
            marker.type or param_type
            for param_type, marker in original.context_parameters.values()
        }
        override_context_types = {
            marker.type or param_type
            for param_type, marker in override.context_parameters.values()
        }
        added_context_types = override_context_types - original_context_types
        if added_context_types:
            added = ", ".join(
                sorted(context_type.__name__ for context_type in added_context_types)
            )
            raise PipelineOverrideError(
                f"transform override for step '{step.name}' introduces context "
                f"dependencies not required by the original transform: {added}. "
                "Remove these dependencies from the replacement."
            )

    def _resolve_transform_overrides(
        self, transform_overrides: Mapping[str, Transform] | None
    ) -> dict[str, Transform]:
        resolved: dict[str, Transform] = {}

        for name, replacement in (transform_overrides or {}).items():
            step = self._steps_by_name.get(name)
            if step is None:
                available = ", ".join(sorted(self._steps_by_name)) or "<none>"
                raise PipelineOverrideError(
                    f"transform override targets unknown step '{name}'; "
                    f"available steps: {available}"
                )
            if not isinstance(replacement, Transform):
                raise PipelineOverrideError(
                    f"transform override for step '{name}' must be decorated "
                    f"with @transform; got {type(replacement).__name__}."
                )

            self._validate_transform_override(step, replacement)
            resolved[name] = replacement

        return resolved

    @overload
    def run(
        self: Pipeline[None],
        context: None = None,
        *,
        transform_overrides: Mapping[str, Transform] | None = None,
    ) -> PipelineResult: ...

    @overload
    def run(
        self,
        context: ContextT,
        *,
        transform_overrides: Mapping[str, Transform] | None = None,
    ) -> PipelineResult: ...

    def run(
        self,
        context: ContextT | None = None,
        *,
        transform_overrides: Mapping[str, Transform] | None = None,
    ) -> PipelineResult:
        """Run each step and return its recorded inputs and outputs.

        Args:
            context: Instance of the context dataclass, when the pipeline
                was created with one.
            transform_overrides: Replacement transforms keyed by step name.
                Each replacement must have compatible input contracts and the
                same output contract.

        Returns:
            A result containing a run record for every step.

        Raises:
            TypeError: If the context is missing or has the wrong type.
            PipelineOverrideError: If a replacement is invalid.
            PipelineExecutionError: If a required input is unconnected or a
                step fails.
        """
        if self._context_type is None:
            if context is not None:
                raise TypeError(
                    "A context-free pipeline does not accept a context; "
                    f"got {type(context).__name__}. Call run() without one."
                )
        elif context is None:
            raise TypeError(
                f"Pipeline[{self._context_type.__name__}] requires a context. "
                f"Pass a {self._context_type.__name__} instance to run()."
            )
        elif not isinstance(context, self._context_type):
            raise TypeError(
                f"expected context of type {self._context_type.__name__}, "
                f"got {type(context).__name__}. Pass a "
                f"{self._context_type.__name__} instance to run()."
            )

        overrides = self._resolve_transform_overrides(transform_overrides)
        self._validate_source_steps(overrides)

        outputs: dict[str, Any] = {}
        step_runs: list[StepRun[Any]] = []

        for step in self.get_steps_in_execution_order():
            effective_transform = overrides.get(step.name, step.transform)
            spec = effective_transform.__transform_spec__
            arguments: dict[str, Any] = {}
            sources: dict[str, Step[Any] | ContextSource] = {}
            step_index = self._node_indices[step]

            for upstream_index, _, parameter_name in self._dag.in_edges(step_index):
                upstream_step = self._dag[upstream_index]
                arguments[parameter_name] = outputs[upstream_step.name]
                sources[parameter_name] = upstream_step
            for parameter_name, (
                param_type,
                marker,
            ) in spec.context_parameters.items():
                dependency_type = marker.type or param_type
                context_field = self._context_fields[dependency_type]
                arguments[parameter_name] = getattr(context, context_field)
                sources[parameter_name] = ContextSource(context_field)

            signature = effective_transform.get_signature()
            missing = {
                name
                for name in spec.input_contracts
                if name not in arguments
                and signature.parameters[name].default is inspect.Parameter.empty
            }
            if missing:
                names = ", ".join(sorted(missing))
                raise PipelineExecutionError(
                    f"Pipeline step '{step.name}' has unconnected inputs: {names}. "
                    "Connect an upstream step to each input."
                )

            try:
                bound = signature.bind(**arguments)
                bound.apply_defaults()
                result = effective_transform(**arguments)
            except Exception as error:
                if isinstance(error, PipelineExecutionError):
                    raise
                raise PipelineExecutionError(
                    f"Pipeline step '{step.name}' failed: "
                    f"{type(error).__name__}: {error}"
                ) from error

            if result is not None:
                outputs[step.name] = result

            step_runs.append(
                StepRun(
                    step=step,
                    transform=effective_transform,
                    inputs=bound_inputs(bound.arguments, sources),
                    output=result,
                )
            )

        return PipelineResult(tuple(step_runs))

    def visualize(self, *, show: bool = True):
        """Draw the pipeline and return its Matplotlib figure.

        Args:
            show: Whether to display the figure. Set to ``False`` to save or
                customize it without opening a window.

        Raises:
            ImportError: If the ``vis`` extra is not installed.
        """
        if not _MATPLOTLIB_AVAILABLE:
            raise ImportError(
                "Pipeline visualization requires matplotlib; "
                "install it with `pip install 'data-joinery[vis]'`."
            )

        assert plt is not None
        figure = draw_pipeline(self._dag)
        if show:
            plt.show()
        return figure
