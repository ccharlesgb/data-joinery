"""Layout and draw pipeline data flow."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from itertools import pairwise
from math import hypot
from typing import TYPE_CHECKING

import rustworkx as rx

from data_joinery.contract import DataFrameContract, InstanceContract, VoidContract

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backends.backend_agg import RendererAgg
    from matplotlib.figure import Figure


# Layout dimensions and font sizes are in typographic points.
_LAYOUT_SWEEPS = 6
_POINTS_PER_INCH = 72
_EMPTY_FIGURE_SIZE = (7, 3)
_FIGURE_MARGIN = 18
_FIGURE_TOP_MARGIN = 62
_MIN_CONTENT_WIDTH = 370
_DIAGRAM_TITLE_OFFSET = 23
_GAP = 70.0
_ROW_GAP = 36

_CARD_MIN_WIDTH = 160
_CARD_PADDING = 16
_HEADER_HEIGHT = 40
_HEADER_WITH_SUBTITLE_HEIGHT = 54
_TITLE_OFFSET = 20
_SUBTITLE_OFFSET = 37
_INPUT_WIDTH_PADDING = 40
_OUTPUT_WIDTH_PADDING = 44
_INPUT_ROW_HEIGHT = 48
_BODY_PADDING = 22
_FIRST_ROW_OFFSET = 44
_SECTION_LABEL_OFFSET = 12
_DIVIDER_TOP_PADDING = 8
_DIVIDER_BOTTOM_PADDING = 10
_INPUT_LABEL_PADDING = 20
_OUTPUT_LABEL_PADDING = 22
_PARAMETER_LABEL_OFFSET = 7
_CONTRACT_LABEL_OFFSET = 5
_CARD_CORNER_RADIUS = 7
_BORDER_WIDTH = 0.7

_TITLE_FONT_SIZE = 12
_CONTRACT_FONT_SIZE = 10
_DETAIL_FONT_SIZE = 8
_SMALL_FONT_SIZE = 7
_DIAGRAM_TITLE_FONT_SIZE = 11

_BADGE_TITLE_SPACE = 86
_BADGE_RIGHT_OFFSET = 90
_BADGE_TOP_OFFSET = 27
_BADGE_WIDTH = 74
_BADGE_HEIGHT = 14
_BADGE_CORNER_RADIUS = 3
_BADGE_TEXT_RIGHT_OFFSET = 84

_BAND = 30.0
_NECK = 5.0
_BAND_DIVIDER_GAP = 10
_RIBBON_CARD_OVERLAP = 18
_RIBBON_SAMPLES = 120
_RIBBON_MAX_TAPER = 38.0
_RIBBON_TAPER_FRACTION = 0.4
_PALE_WHITE_WEIGHT = 0.84
_PALE_COLOUR_WEIGHT = 0.16
_RGB_CHANNEL_MAX = 255

_CARD_ZORDER = 2
_RIBBON_ZORDER = 3
_DECORATION_ZORDER = 4
_LABEL_ZORDER = 5

# Colours are assigned in node order and deliberately cycle for large diagrams.
_PALETTE = ("#087f78", "#ba5718", "#7050b0", "#326ba8", "#a34270", "#657b2d")
_CONTEXT_COLOUR = "#505050"


@dataclass(frozen=True)
class _Vertex:
    layer: int
    node: int | None
    edge: tuple[int, int, str] | None = None


def topological_layout(dag: rx.PyDiGraph) -> dict[int, tuple[float, float]]:
    """Place steps in layers and order branches to reduce crossing lines."""
    return {
        vertex.node: position
        for vertex, position in _layout_vertices(dag).items()
        if vertex.node is not None
    }


def _layout_vertices(dag: rx.PyDAG) -> dict[_Vertex, tuple[float, float]]:
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
    for _ in range(_LAYOUT_SWEEPS):
        for depths in (range(1, len(columns)), range(len(columns) - 2, -1, -1)):
            for depth in depths:
                adjacent = depth - 1 if depths.start == 1 else depth + 1
                adjacent_positions = {
                    vertex: i for i, vertex in enumerate(columns[adjacent])
                }
                columns[depth].sort(
                    key=lambda vertex: (
                        sum(
                            adjacent_positions[n]
                            for n in neighbours[vertex]
                            if n in adjacent_positions
                        )
                        / max(
                            1, sum(n in adjacent_positions for n in neighbours[vertex])
                        )
                    )
                )

    positions: dict[_Vertex, tuple[float, float]] = {}
    for depth, column in enumerate(columns):
        count = len(column)
        for row, vertex in enumerate(column):
            positions[vertex] = (float(depth), (count - 1) / 2 - row)
    return positions


def _same_colour_contract(left: object, right: object) -> bool:
    if isinstance(left, DataFrameContract) and isinstance(right, DataFrameContract):
        return (
            left.schema == right.schema
            and left.backend_name == right.backend_name
            and left.dataframe_type is right.dataframe_type
        )
    if isinstance(left, InstanceContract) and isinstance(right, InstanceContract):
        return left.value_type is right.value_type
    return type(left) is type(right)


def _contract_type(contract: object) -> type | None:
    if isinstance(contract, DataFrameContract):
        return contract.schema.model
    if isinstance(contract, InstanceContract):
        return contract.value_type
    return None


def _contract_label(contract: object, names: dict[type, str]) -> str:
    value_type = _contract_type(contract)
    name = names[value_type] if value_type else ""
    if isinstance(contract, DataFrameContract):
        frame = f"{contract.backend_name} DF" if contract.backend_name else "DF"
        return f"{name} · {frame}"
    if isinstance(contract, InstanceContract):
        return f"{name} · Instance"
    if isinstance(contract, VoidContract):
        return "No Output"
    return "Unvalidated · DF"


def _type_names(value_types: Sequence[type]) -> dict[type, str]:
    groups: dict[str, list[type]] = defaultdict(list)
    for cls in value_types:
        if cls not in groups[cls.__name__]:
            groups[cls.__name__].append(cls)
    names = {}
    for short, classes in groups.items():
        for index, cls in enumerate(classes):
            name = (
                short if len(classes) == 1 else f"{cls.__module__}.{cls.__qualname__}"
            )
            if name in names.values():
                name += f" [{index + 1}]"
            names[cls] = name
    return names


def _output_colours(dag: rx.PyDAG) -> dict[int, str]:
    registry: list[object] = []
    colours = {}
    for node in dag.node_indices():
        contract = dag[node].transform.__transform_spec__.output_contract
        if isinstance(contract, VoidContract):
            continue
        match = next(
            (
                i
                for i, known in enumerate(registry)
                if _same_colour_contract(contract, known)
            ),
            len(registry),
        )
        if match == len(registry):
            registry.append(contract)
        colours[node] = _PALETTE[match % len(_PALETTE)]
    return colours


@dataclass(frozen=True)
class _Input:
    source: int | None
    parameter: str
    label: str
    y: float


@dataclass(frozen=True)
class _Card:
    node: int
    x: float
    top: float
    width: float
    height: float
    split: float
    title: str
    subtitle: str
    side_effect: bool
    inputs: tuple[_Input, ...]
    output: str
    output_y: float
    has_output: bool

    @property
    def right(self) -> float:
        """Return the right edge of the card."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """Return the bottom edge of the card."""
        return self.top - self.height


def _cards(
    dag: rx.PyDAG,
    positions: Mapping[int, tuple[float, float]],
    measure: Callable[[str, float, bool], float],
) -> dict[int, _Card]:
    value_types: list[type] = []
    for node in dag.node_indices():
        spec = dag[node].transform.__transform_spec__
        value_types.extend(
            value_type
            for contract in (spec.output_contract, *spec.input_contracts.values())
            if (value_type := _contract_type(contract)) is not None
        )
        value_types.extend(
            marker.type or param_type
            for param_type, marker in spec.context_parameters.values()
        )
    names = _type_names(value_types)
    incoming: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for source, target, parameter in dag.weighted_edge_list():
        incoming[target].append((source, parameter))
    sizes = {}
    for node in dag.node_indices():
        step = dag[node]
        spec = step.transform.__transform_spec__
        edges = sorted(
            incoming[node], key=lambda pair: (-positions[pair[0]][1], pair[1])
        )
        inputs: list[tuple[int | None, str, str]] = [
            (source, param, _contract_label(spec.input_contracts[param], names))
            for source, param in edges
        ]
        inputs.extend(
            (None, param, f"{names[marker.type or param_type]} · Ctx")
            for param, (param_type, marker) in spec.context_parameters.items()
        )
        output = _contract_label(spec.output_contract, names)
        subtitle = step.transform.default_name or type(step.transform).__name__
        subtitle = subtitle if subtitle != step.name else ""
        input_width = max(
            (
                max(
                    measure(label, _CONTRACT_FONT_SIZE, True),
                    measure(param, _DETAIL_FONT_SIZE, False),
                )
                + _INPUT_WIDTH_PADDING
                for _, param, label in inputs
            ),
            default=0,
        )
        output_width = (
            measure(output, _CONTRACT_FONT_SIZE, True) + _OUTPUT_WIDTH_PADDING
        )
        header_width = (
            max(
                measure(step.name, _TITLE_FONT_SIZE, True)
                + (_BADGE_TITLE_SPACE if step.transform.side_effect else 0),
                measure(subtitle, _DETAIL_FONT_SIZE, False),
            )
            + 2 * _CARD_PADDING
        )
        width = max(_CARD_MIN_WIDTH, input_width + output_width, header_width)
        split = input_width + (width - input_width - output_width) / 2 if inputs else 0
        header = _HEADER_WITH_SUBTITLE_HEIGHT if subtitle else _HEADER_HEIGHT
        body = max(1, len(inputs)) * _INPUT_ROW_HEIGHT + _BODY_PADDING
        sizes[node] = (
            width,
            header + body,
            split,
            header,
            inputs,
            output,
            subtitle,
        )
    pitch = max(size[1] for size in sizes.values()) + _ROW_GAP
    column_widths: dict[int, float] = defaultdict(float)
    for node, size in sizes.items():
        depth = int(positions[node][0])
        column_widths[depth] = max(column_widths[depth], size[0])
    column_x = {}
    x = 0
    for depth in sorted(column_widths):
        column_x[depth] = x
        x += column_widths[depth] + _GAP
    result = {}
    for node, size in sizes.items():
        width, height, split, header, inputs, output, subtitle = size
        top = positions[node][1] * pitch + height / 2
        rows = tuple(
            _Input(
                source,
                param,
                label,
                top - header - _FIRST_ROW_OFFSET - slot * _INPUT_ROW_HEIGHT,
            )
            for slot, (source, param, label) in enumerate(inputs)
        )
        output_y = (
            sum(row.y for row in rows) / len(rows)
            if rows
            else top - header - _FIRST_ROW_OFFSET
        )
        result[node] = _Card(
            node,
            column_x[int(positions[node][0])],
            top,
            width,
            height,
            split,
            dag[node].name,
            subtitle,
            dag[node].transform.side_effect,
            rows,
            output,
            output_y,
            not isinstance(
                dag[node].transform.__transform_spec__.output_contract, VoidContract
            ),
        )
    return result


def _smoothstep(fraction: float) -> float:
    fraction = max(0.0, min(1.0, fraction))
    return fraction * fraction * (3 - 2 * fraction)


def _ribbon_contours(
    start: tuple[float, float],
    end: tuple[float, float],
    samples: int = _RIBBON_SAMPLES,
    start_width: float = _BAND,
    end_width: float = _BAND,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    # Monotone x and vertical offsets keep the two contours from folding over
    # on steep branches. Both centreline and width have horizontal end tangents.
    sx, sy = start
    tx, ty = end
    length = tx - sx
    taper = min(_RIBBON_MAX_TAPER, length * _RIBBON_TAPER_FRACTION)
    upper, lower = [], []
    for index in range(samples + 1):
        t = index / samples
        x = sx + length * t
        y = sy + (ty - sy) * _smoothstep(t)
        start_blend = 1 - _smoothstep((x - sx) / taper)
        end_blend = 1 - _smoothstep((tx - x) / taper)
        half = (
            _NECK
            + (start_width - _NECK) * start_blend
            + (end_width - _NECK) * end_blend
        ) / 2
        slope = (ty - sy) / length * 6 * t * (1 - t)
        half += _NECK / 2 * (hypot(1, slope) - 1) * (1 - max(start_blend, end_blend))
        upper.append((x, y + half))
        lower.append((x, y - half))
    return upper, lower


def _pale(colour: str) -> tuple[float, float, float]:
    # Preblend once: overlapping branches keep exactly the same pale fill.
    red, green, blue = (
        _PALE_WHITE_WEIGHT
        + _PALE_COLOUR_WEIGHT * int(colour[i : i + 2], 16) / _RGB_CHANNEL_MAX
        for i in (1, 3, 5)
    )
    return red, green, blue


def _measure_text(
    renderer: RendererAgg, dpi: float, text: str, size: float, bold: bool
) -> float:
    """Return the rendered text width in typographic points."""
    from matplotlib.font_manager import FontProperties

    font = FontProperties(size=size, weight="bold" if bold else "normal")
    return (
        renderer.get_text_width_height_descent(text, font, False)[0]
        * _POINTS_PER_INCH
        / dpi
    )


def _draw_label(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    size: float = _CONTRACT_FONT_SIZE,
    colour: str = "#253d51",
    bold: bool = False,
    **kwargs,
) -> None:
    """Draw a vertically centred label above the diagram shapes."""
    ax.text(
        x,
        y,
        text,
        fontsize=size,
        color=colour,
        fontweight="bold" if bold else "normal",
        va="center",
        zorder=_LABEL_ZORDER,
        **kwargs,
    )


def _draw_band(ax: Axes, x: float, y: float, width: float, colour: str) -> None:
    """Draw a rounded band behind an input or output label."""
    from matplotlib.patches import FancyBboxPatch

    ax.add_patch(
        FancyBboxPatch(
            (x, y - _BAND / 2),
            width,
            _BAND,
            boxstyle=f"round,pad=0,rounding_size={_BAND / 2}",
            linewidth=0,
            facecolor=_pale(colour),
            zorder=_RIBBON_ZORDER,
        )
    )


def _draw_card_backgrounds(
    ax: Axes, cards: Mapping[int, _Card], colours: Mapping[int, str]
) -> None:
    """Draw card backgrounds and input/output bands."""
    from matplotlib.patches import FancyBboxPatch

    for card in cards.values():
        ax.add_patch(
            FancyBboxPatch(
                (card.x, card.bottom),
                card.width,
                card.height,
                boxstyle=f"round,pad=0,rounding_size={_CARD_CORNER_RADIUS}",
                linewidth=_BORDER_WIDTH,
                edgecolor="#d8e0e8",
                facecolor="white",
                zorder=_CARD_ZORDER,
            )
        )
        if card.has_output:
            _draw_band(
                ax,
                card.x + card.split + _BAND_DIVIDER_GAP,
                card.output_y,
                card.width - card.split - _BAND_DIVIDER_GAP,
                colours[card.node],
            )
        for row in card.inputs:
            inset = _BAND_DIVIDER_GAP if row.source is None else 0
            _draw_band(
                ax,
                card.x + inset,
                row.y,
                card.split - _BAND_DIVIDER_GAP - inset,
                _CONTEXT_COLOUR if row.source is None else colours[row.source],
            )


def _draw_connecting_ribbons(
    ax: Axes,
    cards: Mapping[int, _Card],
    colours: Mapping[int, str],
    vertices_by_layer: Mapping[_Vertex, tuple[float, float]],
    pitch: float,
) -> None:
    """Connect cards through the reserved routing slots."""
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path

    for card in cards.values():
        for row in card.inputs:
            if row.source is None:
                continue
            source = cards[row.source]
            points = [(source.right - _RIBBON_CARD_OVERLAP, source.output_y)]
            # Reuse the existing layout's reserved dummy slots for skipped
            # generations. This needs no new obstacle-avoidance algorithm.
            for vertex, (_, y) in vertices_by_layer.items():
                if vertex.edge == (row.source, card.node, row.parameter):
                    column = [
                        cards[v.node]
                        for v in vertices_by_layer
                        if v.layer == vertex.layer and v.node is not None
                    ]
                    points.extend(
                        [
                            (min(c.x for c in column), y * pitch),
                            (max(c.right for c in column), y * pitch),
                        ]
                    )
            points.append((card.x + _RIBBON_CARD_OVERLAP, row.y))
            upper, lower = [], []
            for index, (start, end) in enumerate(pairwise(points)):
                top, bottom = _ribbon_contours(
                    start,
                    end,
                    start_width=_BAND if index == 0 else _NECK,
                    end_width=_BAND if index == len(points) - 2 else _NECK,
                )
                upper.extend(top)
                lower.extend(bottom)
            vertices = upper + list(reversed(lower)) + [upper[0]]
            path = Path(vertices, closed=True)
            ax.add_patch(
                PathPatch(
                    path,
                    facecolor=_pale(colours[row.source]),
                    edgecolor="none",
                    zorder=_RIBBON_ZORDER,
                )
            )


def _draw_card_details(
    ax: Axes, cards: Mapping[int, _Card], colours: Mapping[int, str]
) -> None:
    """Draw card labels, dividers, and side-effect badges."""
    from matplotlib.patches import FancyBboxPatch

    for card in cards.values():
        header = _HEADER_WITH_SUBTITLE_HEIGHT if card.subtitle else _HEADER_HEIGHT
        _draw_label(
            ax,
            card.x + _CARD_PADDING,
            card.top - _TITLE_OFFSET,
            card.title,
            _TITLE_FONT_SIZE,
            bold=True,
        )
        if card.subtitle:
            _draw_label(
                ax,
                card.x + _CARD_PADDING,
                card.top - _SUBTITLE_OFFSET,
                card.subtitle,
                _DETAIL_FONT_SIZE,
                "#617185",
            )
        ax.plot(
            [card.x, card.right],
            [card.top - header] * 2,
            color="#e4e9ef",
            lw=_BORDER_WIDTH,
            zorder=_DECORATION_ZORDER,
        )
        if card.inputs:
            ax.plot(
                [card.x + card.split] * 2,
                [
                    card.top - header - _DIVIDER_TOP_PADDING,
                    card.bottom + _DIVIDER_BOTTOM_PADDING,
                ],
                color="#e4e9ef",
                lw=_BORDER_WIDTH,
                zorder=_DECORATION_ZORDER,
            )
            _draw_label(
                ax,
                card.x + _CARD_PADDING,
                card.top - header - _SECTION_LABEL_OFFSET,
                "INPUTS" if len(card.inputs) > 1 else "INPUT",
                _SMALL_FONT_SIZE,
                "#617185",
                True,
            )
        _draw_label(
            ax,
            card.x + card.split + _CARD_PADDING,
            card.top - header - _SECTION_LABEL_OFFSET,
            "OUTPUT",
            _SMALL_FONT_SIZE,
            "#617185",
            True,
        )
        for row in card.inputs:
            _draw_label(
                ax,
                card.x + _INPUT_LABEL_PADDING,
                row.y + _PARAMETER_LABEL_OFFSET,
                row.parameter,
                _SMALL_FONT_SIZE,
                "#617185",
            )
            _draw_label(
                ax,
                card.x + _INPUT_LABEL_PADDING,
                row.y - _CONTRACT_LABEL_OFFSET,
                row.label,
                _CONTRACT_FONT_SIZE,
                _CONTEXT_COLOUR if row.source is None else colours[row.source],
                True,
            )
        _draw_label(
            ax,
            card.x + card.split + _OUTPUT_LABEL_PADDING,
            card.output_y,
            card.output,
            _CONTRACT_FONT_SIZE,
            colours.get(card.node, "#617185"),
            card.has_output,
        )
        if card.side_effect:
            ax.add_patch(
                FancyBboxPatch(
                    (
                        card.right - _BADGE_RIGHT_OFFSET,
                        card.top - _BADGE_TOP_OFFSET,
                    ),
                    _BADGE_WIDTH,
                    _BADGE_HEIGHT,
                    boxstyle=f"round,pad=0,rounding_size={_BADGE_CORNER_RADIUS}",
                    linewidth=0,
                    facecolor="#fff0d9",
                    zorder=_DECORATION_ZORDER,
                )
            )
            _draw_label(
                ax,
                card.right - _BADGE_TEXT_RIGHT_OFFSET,
                card.top - _TITLE_OFFSET,
                "SIDE EFFECT",
                _SMALL_FONT_SIZE,
                "#a6631c",
                True,
            )


def draw_pipeline(dag: rx.PyDAG) -> Figure:
    """Return a figure showing named inputs and outputs joined by schema ribbons.

    Args:
        dag: Pipeline graph containing transform steps and named input edges.

    Returns:
        A Matplotlib figure without executing any pipeline steps.
    """
    from matplotlib import pyplot as plt
    from matplotlib.backends.backend_agg import RendererAgg

    fig, ax = plt.subplots(figsize=_EMPTY_FIGURE_SIZE)
    fig.patch.set_facecolor("#f6f8fb")
    ax.set_facecolor("#f6f8fb")
    ax.axis("off")
    if not dag.num_nodes():
        ax.text(
            0.5,
            0.5,
            "No steps in this pipeline",
            ha="center",
            va="center",
            color="#56677b",
            transform=ax.transAxes,
        )
        return fig

    renderer = RendererAgg(1, 1, fig.dpi)

    vertices_by_layer = _layout_vertices(dag)
    positions = {
        vertex.node: position
        for vertex, position in vertices_by_layer.items()
        if vertex.node is not None
    }
    cards = _cards(dag, positions, partial(_measure_text, renderer, fig.dpi))
    colours = _output_colours(dag)
    pitch = max(card.height for card in cards.values()) + _ROW_GAP
    route_ys = [
        y * pitch for vertex, (_, y) in vertices_by_layer.items() if vertex.edge
    ]
    xmin = -_FIGURE_MARGIN
    xmax = (
        max(_MIN_CONTENT_WIDTH, max(card.right for card in cards.values()))
        + _FIGURE_MARGIN
    )
    ymin = min([card.bottom for card in cards.values()] + route_ys) - _FIGURE_MARGIN
    ymax = max([card.top for card in cards.values()] + route_ys) + _FIGURE_TOP_MARGIN
    # One coordinate unit is one typographic point, including during measurement.
    fig.set_size_inches(
        (xmax - xmin) / _POINTS_PER_INCH, (ymax - ymin) / _POINTS_PER_INCH
    )
    ax.set_position((0, 0, 1, 1))
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")

    # Draw all bands before ribbons so their shared layer overlaps consistently.
    _draw_card_backgrounds(ax, cards, colours)
    _draw_connecting_ribbons(ax, cards, colours, vertices_by_layer, pitch)
    _draw_card_details(ax, cards, colours)

    _draw_label(
        ax,
        0,
        ymax - _DIAGRAM_TITLE_OFFSET,
        "PIPELINE  /  DATA FLOW",
        _DIAGRAM_TITLE_FONT_SIZE,
        bold=True,
    )
    count, edges = dag.num_nodes(), dag.num_edges()
    _draw_label(
        ax,
        xmax - _FIGURE_MARGIN,
        ymax - _DIAGRAM_TITLE_OFFSET,
        f"{count} {'STEP' if count == 1 else 'STEPS'}   ·   {edges} {'CONNECTION' if edges == 1 else 'CONNECTIONS'}",
        _DETAIL_FONT_SIZE,
        "#708293",
        ha="right",
    )
    return fig
