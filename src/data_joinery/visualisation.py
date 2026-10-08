"""Layout and draw pipeline data flow."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from textwrap import shorten
from typing import TYPE_CHECKING

import rustworkx as rx

from data_joinery.contract import DataFrameContract, InstanceContract, VoidContract

if TYPE_CHECKING:
    from matplotlib.figure import Figure


@dataclass(frozen=True)
class _Vertex:
    layer: int
    node: int | None
    edge: tuple[int, int, str] | None = None


def topological_layout(dag: rx.PyDAG) -> dict[int, tuple[float, float]]:
    """Place steps in layers and order branches to reduce crossing lines."""
    generations = [list(group) for group in rx.topological_generations(dag)]
    layer = {index: depth for depth, group in enumerate(generations) for index in group}
    columns: list[list[_Vertex]] = [
        [_Vertex(depth, index) for index in group]
        for depth, group in enumerate(generations)
    ]
    paths: list[list[_Vertex]] = []
    for source, target, parameter in dag.weighted_edge_list():
        path = [columns[layer[source]][generations[layer[source]].index(source)]]
        for depth in range(layer[source] + 1, layer[target]):
            dummy = _Vertex(depth, None, (source, target, parameter))
            columns[depth].append(dummy)
            path.append(dummy)
        path.append(columns[layer[target]][generations[layer[target]].index(target)])
        paths.append(path)

    neighbours: dict[_Vertex, list[_Vertex]] = defaultdict(list)
    for path in paths:
        for left, right in pairwise(path):
            neighbours[left].append(right)
            neighbours[right].append(left)

    # Reorder each column using adjacent columns. Stable ties retain insertion order.
    for _ in range(6):
        for depths in (range(1, len(columns)), range(len(columns) - 2, -1, -1)):
            for depth in depths:
                adjacent = depth - 1 if depths.start == 1 else depth + 1
                adjacent_positions = {
                    vertex: i for i, vertex in enumerate(columns[adjacent])
                }
                previous_order = {vertex: i for i, vertex in enumerate(columns[depth])}
                columns[depth].sort(
                    key=lambda vertex: (
                        sum(
                            adjacent_positions[n]
                            for n in neighbours[vertex]
                            if n in adjacent_positions
                        )
                        / max(
                            1, sum(n in adjacent_positions for n in neighbours[vertex])
                        ),
                        previous_order[vertex],
                    )
                )

    positions: dict[_Vertex, tuple[float, float]] = {}
    for depth, column in enumerate(columns):
        count = len(column)
        for row, vertex in enumerate(column):
            positions[vertex] = (float(depth), (count - 1) / 2 - row)
    return {
        vertex.node: position
        for vertex, position in positions.items()
        if vertex.node is not None
    }


def _contract_label(contract: object) -> tuple[str, str]:
    if isinstance(contract, DataFrameContract):
        return (
            f"{contract.schema.model.__name__} · {contract.backend_name or 'DataFrame'}",
            "frame",
        )
    if isinstance(contract, InstanceContract):
        return contract.value_type.__name__, "value"
    if isinstance(contract, VoidContract):
        return "No output", "void"
    return "DataFrame", "frame"


def draw_pipeline(dag: rx.PyDAG) -> Figure:
    """Return a figure with labeled steps, data types, and input connections."""
    from matplotlib import pyplot as plt
    from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

    nodes = list(dag.node_indices())
    if not nodes:
        fig, ax = plt.subplots(figsize=(7, 3))
        fig.patch.set_facecolor("#f7f9fc")
        ax.set_facecolor("#f7f9fc")
        ax.text(
            0.5,
            0.5,
            "No steps in this pipeline",
            ha="center",
            va="center",
            color="#56677b",
            transform=ax.transAxes,
        )
        ax.axis("off")
        return fig

    pos = topological_layout(dag)
    edges = list(dag.weighted_edge_list())
    input_edges: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for source, target, parameter in edges:
        input_edges[target].append((source, parameter))
    for target, incoming in input_edges.items():
        incoming.sort(key=lambda pair: (-pos[pair[0]][1], pair[1]))

    width = 3.9
    gap_x = 2.3
    max_depth = max(x for x, _ in pos.values())
    left = {i: pos[i][0] * (width + gap_x) for i in nodes}
    height = {
        i: 1.48
        + 0.35 * len(input_edges[i])
        + (0.35 if dag[i].transform.__transform_spec__.context_parameters else 0)
        for i in nodes
    }
    row_pitch = max(height.values(), default=2) + 0.6
    center_y = {i: pos[i][1] * row_pitch for i in nodes}
    top = {i: center_y[i] + height[i] / 2 for i in nodes}
    bottom = {i: center_y[i] - height[i] / 2 for i in nodes}
    palette = {"frame": "#27887f", "value": "#7767a6", "void": "#8a98a7"}

    # Scale with the graph, so saved figures remain readable even for wide pipelines.
    ys = [value for i in nodes for value in (top[i], bottom[i])]
    ymin, ymax = min(ys) - 1.0, max(ys) + 1.7
    xmax = max_depth * (width + gap_x) + width + 0.9
    fig, ax = plt.subplots(figsize=(max(8, xmax * 0.85), max(4, (ymax - ymin) * 0.85)))
    fig.patch.set_facecolor("#f7f9fc")
    ax.set_facecolor("#f7f9fc")
    ax.set_xlim(-0.55, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    # Edges are drawn first so their ends sit beneath the cards and port dots.
    for source, target, parameter in edges:
        source_contract = dag[source].transform.__transform_spec__.output_contract
        _, kind = _contract_label(source_contract)
        slot = next(
            i
            for i, pair in enumerate(input_edges[target])
            if pair == (source, parameter)
        )
        sy = bottom[source] + 0.32
        ty = top[target] - 0.82 - slot * 0.35
        sx = left[source] + width
        tx = left[target]
        color = palette[kind]
        arrow = FancyArrowPatch(
            (sx, sy),
            (tx, ty),
            connectionstyle=f"arc3,rad={0.12 if sy <= ty else -0.12}",
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.7,
            color=color,
            alpha=0.76,
            zorder=1,
        )
        ax.add_patch(arrow)

    for i in nodes:
        step = dag[i]
        spec = step.transform.__transform_spec__
        output, kind = _contract_label(spec.output_contract)
        x, y = left[i], top[i]
        ax.add_patch(
            FancyBboxPatch(
                (x + 0.035, bottom[i] - 0.055),
                width,
                height[i],
                boxstyle="round,pad=0.02,rounding_size=0.14",
                linewidth=0,
                facecolor="#dfe6ee",
                alpha=0.65,
                zorder=2,
            )
        )
        ax.add_patch(
            FancyBboxPatch(
                (x, bottom[i]),
                width,
                height[i],
                boxstyle="round,pad=0.02,rounding_size=0.14",
                linewidth=0.9,
                edgecolor="#d6dfe8",
                facecolor="white",
                zorder=3,
            )
        )
        ax.add_patch(
            FancyBboxPatch(
                (x, y - 0.10),
                0.065,
                -height[i] + 0.20,
                boxstyle="round,pad=0,rounding_size=0.03",
                linewidth=0,
                facecolor=palette[kind],
                zorder=4,
            )
        )
        ax.text(
            x + 0.27,
            y - 0.31,
            shorten(step.name, width=34, placeholder="…"),
            fontsize=12,
            fontweight="bold",
            color="#1e3043",
            va="center",
            zorder=5,
        )
        transform_name = step.transform.default_name or type(step.transform).__name__
        ax.text(
            x + 0.27,
            y - 0.62,
            shorten(transform_name, width=42, placeholder="…"),
            fontsize=8.5,
            color="#697b8c",
            va="center",
            zorder=5,
        )
        for slot, (source, parameter) in enumerate(input_edges[i]):
            py = y - 0.82 - slot * 0.35
            input_type, input_kind = _contract_label(spec.input_contracts[parameter])
            ax.add_patch(Circle((x, py), 0.06, color=palette[input_kind], zorder=6))
            ax.text(
                x + 0.27,
                py,
                shorten(parameter, width=19, placeholder="…"),
                fontsize=9,
                color="#35485b",
                va="center",
                zorder=5,
            )
            ax.text(
                x + width - 0.22,
                py,
                shorten(input_type, width=21, placeholder="…"),
                fontsize=8.2,
                color="#748597",
                ha="right",
                va="center",
                zorder=5,
            )
        if not input_edges[i] and not spec.context_parameters:
            ax.text(
                x + 0.27,
                y - 0.90,
                "SOURCE",
                fontsize=8,
                fontweight="bold",
                color="#789187",
                va="center",
                zorder=5,
            )
        if spec.context_parameters:
            context_names = ", ".join(spec.context_parameters)
            ax.text(
                x + 0.27,
                bottom[i] + 0.57,
                "Context: " + shorten(context_names, width=38, placeholder="…"),
                fontsize=8,
                color="#8a718a",
                va="center",
                zorder=5,
            )
        ax.text(
            x + 0.27,
            bottom[i] + 0.26,
            "OUT",
            fontsize=7.5,
            fontweight="bold",
            color="#8292a2",
            va="center",
            zorder=5,
        )
        ax.text(
            x + 0.72,
            bottom[i] + 0.26,
            shorten(output, width=37, placeholder="…"),
            fontsize=9,
            color=palette[kind],
            va="center",
            zorder=5,
        )
        if kind != "void":
            ax.add_patch(
                Circle(
                    (x + width, bottom[i] + 0.32), 0.065, color=palette[kind], zorder=6
                )
            )

    ax.text(
        -0.02,
        ymax - 0.40,
        "PIPELINE  /  DATA FLOW",
        fontsize=11,
        fontweight="bold",
        color="#253d51",
        va="center",
    )
    ax.text(
        xmax - 0.25,
        ymax - 0.40,
        f"{len(nodes)} {'STEP' if len(nodes) == 1 else 'STEPS'}   ·   "
        f"{len(edges)} {'CONNECTION' if len(edges) == 1 else 'CONNECTIONS'}",
        fontsize=9,
        color="#708293",
        ha="right",
        va="center",
    )
    fig.tight_layout(pad=0.3)
    return fig
