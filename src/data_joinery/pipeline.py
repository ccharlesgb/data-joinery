from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, overload

import rustworkx as rx

try:
    from matplotlib import pyplot as plt
    from rustworkx.visualization import mpl_draw
except ModuleNotFoundError as error:
    if error.name != "matplotlib":
        raise
    plt = None
    mpl_draw = None
    _MATPLOTLIB_AVAILABLE = False
else:
    _MATPLOTLIB_AVAILABLE = True

from data_joinery.contract import Contract, VoidContract
from data_joinery.dependencies import inspect_context_type
from data_joinery.transform import Transform
from data_joinery.visualisation import topological_layout


class PipelineExecutionError(RuntimeError):
    pass


class PipelineCycleError(Exception):
    pass


class PipelineConnectionError(Exception):
    pass


class PipelineOverrideError(ValueError):
    pass


@dataclass(eq=False, frozen=True)
class Step:
    """
    Represents a single step in a pipeline, encapsulating a transform and its connections.
    It's purpose is to allow you to use a transformation more than once within the same pipeline.
    """

    name: str
    transform: Transform
    _pipeline: Pipeline[Any]

    def __rshift__(self, other: Step) -> Step:
        if not isinstance(other, Step):
            raise TypeError("Can only connect Step instances using >>")
        self._pipeline.connect(self, other)
        return other


class Pipeline[ContextT]:
    @overload
    def __init__(self: Pipeline[None]) -> None: ...

    @overload
    def __init__(self, context_type: type[ContextT]) -> None: ...

    def __init__(self, context_type: type[ContextT] | None = None):
        self._dag = rx.PyDAG(check_cycle=True)
        self._node_indices: dict[Step, int] = {}
        self._steps_by_name: dict[str, Step] = {}
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
                "pipeline steps only support contract and Context-annotated "
                f"parameters; unsupported parameter '{unsupported}'"
            )

    def add_step(self, transform: Transform, name: str | None = None) -> Step:
        """Adds a new step to the pipeline.

        Args:
            transform: The transform to add as a step in the pipeline.
            name: The name of the step. If None, the name will be inferred from the transform.

        Returns:
            The newly created Step instance.

        Raises:
            ValueError: If the step name is already registered or cannot be inferred.
            TypeError: If the transform has unsupported parameters or lacks required inputs.
        """
        if name is None:
            name = transform.default_name
        if name is None:
            raise ValueError(
                f"Step name of '{transform}' could not be inferred. Pass name=<desired_name>"
            )
        if name in self._steps_by_name:
            raise ValueError(f"step name '{name}' is already registered")

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
        for (
            param_type,
            marker,
        ) in transform.__transform_spec__.context_parameters.values():
            dependency_type = marker.type or param_type
            if dependency_type not in self._context_fields:
                transform_name = transform.default_name or repr(transform)
                context_name = (
                    self._context_type.__name__
                    if self._context_type is not None
                    else "a context-free pipeline"
                )
                raise TypeError(
                    f"transform '{transform_name}' requires context dependency "
                    f"{dependency_type.__name__}, but {context_name} does not provide it"
                )

    def connect(
        self, upstream: Step, downstream: Step, *, param: str | None = None
    ) -> None:
        downstream_spec = downstream.transform.__transform_spec__
        upstream_spec = upstream.transform.__transform_spec__

        upstream_contract = upstream_spec.output_contract
        if isinstance(upstream_contract, VoidContract):
            raise PipelineConnectionError(
                f"upstream step '{upstream.name}' does not produce an output"
            )

        compatible_specs: dict[str, Contract] = {}
        for param_name, input_contract in downstream_spec.input_contracts.items():
            if input_contract.accepts(upstream_contract):
                compatible_specs[param_name] = input_contract

        if len(compatible_specs) > 1:
            if param is None:
                raise PipelineConnectionError(
                    f"Multiple compatible input contracts found for upstream step '{upstream.name}' "
                    f"and downstream step '{downstream.name}', but no parameter was specified"
                )
            else:
                downstream_parameter_name = param
        elif len(compatible_specs) == 1:
            compatible_parameter = next(iter(compatible_specs))
            if param is not None and param != compatible_parameter:
                raise PipelineConnectionError(
                    f"Specified parameter '{param}' does not match the compatible input contract '{compatible_parameter}'"
                )
            downstream_parameter_name = compatible_parameter
        else:
            raise PipelineConnectionError(
                f"No compatible contract between steps '{upstream.name}' and '{downstream.name}'"
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
                f"'{downstream.name}'"
            )

        try:
            self._dag.add_edge(
                self._node_indices[upstream],
                downstream_index,
                downstream_parameter_name,
            )
        except rx.DAGWouldCycle:
            raise PipelineCycleError(
                f"Connecting upstream step '{upstream.name}' to downstream step '{downstream.name}' would create a cycle"
            )

    def connect_many(
        self,
        upstream_steps: Sequence[Step],
        downstream: Step,
    ) -> None:
        if not upstream_steps:
            raise ValueError("connect_many requires at least one upstream step")
        for upstream in upstream_steps:
            self.connect(upstream, downstream)

    def get_upstream_steps(self, step: Step) -> set[Step]:
        return set(self._dag.predecessors(self._node_indices[step]))

    def get_steps_in_execution_order(self) -> list[Step]:
        node_indices = rx.topological_sort(self._dag)
        return [self._dag[node_index] for node_index in node_indices]

    def _validate_source_steps(self) -> None:
        for step, step_index in self._node_indices.items():
            if (
                self._dag.in_degree(step_index) == 0
                and step.transform.__transform_spec__.input_contracts
            ):
                raise PipelineExecutionError(
                    f"first pipeline step '{step.name}' requires upstream inputs"
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
                    f"transform override for step '{step.name}' has an incompatible "
                    f"contract for input parameter '{name}'"
                )

        if original.output_contract != override.output_contract:
            raise PipelineOverrideError(
                f"transform override for step '{step.name}' must declare the same "
                "output contract"
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
                f"dependencies not required by the original transform: {added}"
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
                    "with @transform"
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
    ) -> dict[str, Any]: ...

    @overload
    def run(
        self,
        context: ContextT,
        *,
        transform_overrides: Mapping[str, Transform] | None = None,
    ) -> dict[str, Any]: ...

    def run(
        self,
        context: ContextT | None = None,
        *,
        transform_overrides: Mapping[str, Transform] | None = None,
    ) -> dict[str, Any]:
        if self._context_type is None:
            if context is not None:
                raise TypeError("a context-free pipeline does not accept a context")
        elif context is None:
            raise TypeError(
                f"Pipeline[{self._context_type.__name__}] requires a context"
            )
        elif not isinstance(context, self._context_type):
            raise TypeError(
                f"expected context of type {self._context_type.__name__}, "
                f"got {type(context).__name__}"
            )

        overrides = self._resolve_transform_overrides(transform_overrides)
        self._validate_source_steps()

        outputs: dict[str, Any] = {}

        for step in self.get_steps_in_execution_order():
            effective_transform = overrides.get(step.name, step.transform)
            spec = effective_transform.__transform_spec__
            arguments: dict[str, Any] = {}
            step_index = self._node_indices[step]

            for upstream_index, _, parameter_name in self._dag.in_edges(step_index):
                upstream_step = self._dag[upstream_index]
                arguments[parameter_name] = outputs[upstream_step.name]
            for parameter_name, (
                param_type,
                marker,
            ) in spec.context_parameters.items():
                dependency_type = marker.type or param_type
                context_field = self._context_fields[dependency_type]
                arguments[parameter_name] = getattr(context, context_field)

            try:
                result = effective_transform(**arguments)
            except Exception as error:
                if isinstance(error, PipelineExecutionError):
                    raise
                raise PipelineExecutionError(
                    f"Pipeline step '{step.name}' failed"
                ) from error

            if result is not None:
                outputs[step.name] = result

        return outputs

    def visualize(self) -> None:
        if not _MATPLOTLIB_AVAILABLE:
            raise ImportError(
                "Pipeline visualization requires matplotlib; "
                "install it with `pip install 'data-joinery[vis]'`."
            )

        assert mpl_draw is not None
        assert plt is not None
        mpl_draw(
            self._dag,
            pos=topological_layout(self._dag),
            with_labels=True,
            labels=lambda node: node.name,
            edge_labels=lambda edge: edge,
            node_shape="s",
            node_size=500,
            font_size=8,
        )
        plt.show()
