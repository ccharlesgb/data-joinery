from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from math import hypot
from types import SimpleNamespace
from typing import Annotated, cast

import pytest
import rustworkx as rx
from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch, PathPatch

from data_joinery import Context, Pipeline, Project, Strict, transform
from data_joinery.contract import InstanceContract
from data_joinery.visualisation import (
    _BAND,
    _NECK,
    _PALETTE,
    _cards,
    _contract_label,
    _output_colours,
    _pale,
    _ribbon_contours,
    _same_colour_contract,
    _type_names,
    topological_layout,
)


@pytest.fixture(autouse=True)
def close_figures():
    plt.switch_backend("Agg")
    yield
    plt.close("all")


class Records: ...


class ChildRecords(Records): ...


class Features: ...


class Model: ...


@transform
def read() -> Records:
    return Records()


@transform
def prepare(records: Records) -> Features:
    return Features()


@transform
def fit(features: Features) -> Model:
    return Model()


@transform
def evaluate(features: Features, model: Model) -> None:
    return None


def test_layout_places_edges_left_to_right_and_separates_branches():
    pipeline = Pipeline()
    source = pipeline.add_step(read, "read")
    branches = [pipeline.add_step(prepare, f"prepare {i}") for i in range(8)]
    models = [pipeline.add_step(fit, f"fit {i}") for i in range(8)]
    sinks = [pipeline.add_step(evaluate, f"evaluate {i}") for i in range(8)]
    for branch, model, sink in zip(branches, models, sinks):
        pipeline.connect(source, branch)
        pipeline.connect(branch, model)
        pipeline.connect(branch, sink, param="features")
        pipeline.connect(model, sink, param="model")

    positions = topological_layout(pipeline._dag)
    assert len(positions) == 25
    for upstream, downstream, _ in pipeline._dag.weighted_edge_list():
        assert positions[upstream][0] < positions[downstream][0]
    for x in {point[0] for point in positions.values()}:
        ys = [y for px, y in positions.values() if px == x]
        assert len(ys) == len(set(ys))


def test_visualize_exposes_step_inputs_outputs_and_can_be_saved(tmp_path):
    pipeline = Pipeline()
    source = pipeline.add_step(read, "read source")
    branch = pipeline.add_step(prepare, "prepare features")
    model = pipeline.add_step(fit, "fit model")
    sink = pipeline.add_step(evaluate, "evaluate model")
    pipeline.connect(source, branch)
    pipeline.connect(branch, model)
    pipeline.connect(branch, sink, param="features")
    pipeline.connect(model, sink, param="model")

    figure = pipeline.visualize(show=False)
    labels = [text.get_text() for text in figure.axes[0].texts]
    assert {"read source", "prepare features", "fit model", "evaluate model"} <= set(
        labels
    )
    assert {"features", "model", "OUTPUT", "No Output"} <= set(labels)
    image = tmp_path / "pipeline.png"
    figure.savefig(image)
    assert image.stat().st_size > 1000


def test_empty_pipeline_visualization():
    figure = Pipeline().visualize(show=False)
    assert "No steps in this pipeline" in [
        text.get_text() for text in figure.axes[0].texts
    ]


def test_visualize_labels_side_effect_steps():
    @transform(side_effect=True)
    def publish() -> None:
        pass

    pipeline = Pipeline()
    pipeline.add_step(publish)

    figure = pipeline.visualize(show=False)
    labels = [text.get_text() for text in figure.axes[0].texts]

    assert "SIDE EFFECT" in labels


def _measure(text: str, size: float, bold: bool) -> float:
    return len(text) * size


def test_card_inputs_remain_separate_when_one_source_feeds_two_parameters():
    @transform
    def combine(first: Records, second: Records) -> Records:
        raise AssertionError("Rendering must not execute transforms")

    pipeline = Pipeline()
    source = pipeline.add_step(read)
    target = pipeline.add_step(combine)
    pipeline.connect(source, target, param="first")
    pipeline.connect(source, target, param="second")

    source_node, target_node = pipeline._dag.node_indices()
    positions = {source_node: (0, 0), target_node: (1, 0)}
    cards = _cards(pipeline._dag, positions, _measure)
    card = next(card for card in cards.values() if card.title == "combine")

    assert {row.parameter for row in card.inputs if row.y != card.output_y} == {
        "first",
        "second",
    }


def test_cards_place_output_to_right_of_inputs():
    pipeline = Pipeline()
    source = pipeline.add_step(read)
    target = pipeline.add_step(prepare)
    pipeline.connect(source, target)
    source_node, target_node = pipeline._dag.node_indices()
    positions = {source_node: (0, 0), target_node: (1, 0)}
    card = next(
        card
        for card in _cards(pipeline._dag, positions, _measure).values()
        if card.inputs
    )

    assert 0 < card.split < card.width


def test_cards_follow_supplied_vertical_positions():
    pipeline = Pipeline()
    pipeline.add_step(read, "first")
    pipeline.add_step(read, "second")
    first, second = pipeline._dag.node_indices()
    positions = {first: (0, -1), second: (0, 1)}

    cards = _cards(pipeline._dag, positions, _measure)
    # Both cards have a subtitle: 54-point header, 70-point body, 36-point gap.
    expected = {first: -160, second: 160}
    actual = {node: card.top - card.height / 2 for node, card in cards.items()}

    assert actual == expected


def test_output_colours_reuse_contract_identity():
    pipeline = Pipeline()
    pipeline.add_step(read, "first")
    pipeline.add_step(read, "second")
    pipeline.add_step(prepare)

    assert list(_output_colours(pipeline._dag).values()) == [
        _PALETTE[0],
        _PALETTE[0],
        _PALETTE[1],
    ]


def test_dataframe_colour_identity_ignores_coercion_mode():

    @dataclass
    class Orders:
        order_id: int

    assert _same_colour_contract(Strict(Orders), Project(Orders))


@pytest.mark.parametrize("difference", ["schema", "backend", "frame"])
def test_dataframe_colour_identity_distinguishes_contracts(difference):

    @dataclass
    class Orders:
        order_id: int

    @dataclass
    class Customers:
        customer_id: int

    original = Strict(Orders)
    different = {
        "schema": Strict(Customers),
        "backend": replace(original, backend_name="polars"),
        "frame": replace(original, dataframe_type=Records),
    }[difference]

    assert not _same_colour_contract(original, different)


def test_palette_cycles_without_collapsing_distinct_types():

    dag = rx.PyDAG()
    for index in range(len(_PALETTE) + 1):
        contract = InstanceContract(type(f"Value{index}", (), {}))
        dag.add_node(
            SimpleNamespace(
                transform=SimpleNamespace(
                    __transform_spec__=SimpleNamespace(output_contract=contract)
                )
            )
        )

    assert list(_output_colours(dag).values()) == [*_PALETTE, _PALETTE[0]]


@pytest.mark.parametrize(
    ("backend_name", "expected"),
    [
        ("polars", "Orders · polars DF"),
        ("pyspark", "Orders · pyspark DF"),
        (None, "Orders · DF"),
    ],
)
def test_dataframe_contract_label_includes_backend(backend_name, expected):
    @dataclass
    class Orders:
        order_id: int

    contract = replace(Strict(Orders), backend_name=backend_name)

    assert _contract_label(contract, {Orders: "Orders"}) == expected


def test_same_named_classes_have_distinct_labels():
    first = type("Records", (), {"__module__": "source_one"})
    second = type("Records", (), {"__module__": "source_two"})
    contracts = [InstanceContract(first), InstanceContract(second)]
    names = _type_names([first, second])

    assert [_contract_label(contract, names) for contract in contracts] == [
        "source_one.Records · Instance",
        "source_two.Records · Instance",
    ]


def test_ribbon_contours_stay_positive_and_taper_between_endpoints():
    upper, lower = _ribbon_contours((0, 0), (100, 0))
    widths = [top[1] - bottom[1] for top, bottom in zip(upper, lower)]

    assert (widths[0], min(widths), widths[-1]) == pytest.approx((_BAND, _NECK, _BAND))


def test_ribbon_endpoint_positions_match_anchors():
    upper, lower = _ribbon_contours((10, 20), (110, 80))
    actual = [upper[0], lower[0], upper[-1], lower[-1]]
    expected = [
        (10, 20 + _BAND / 2),
        (10, 20 - _BAND / 2),
        (110, 80 + _BAND / 2),
        (110, 80 - _BAND / 2),
    ]

    assert actual == expected


def test_connected_input_uses_producer_colour_and_declared_label():
    @transform
    def read_child() -> ChildRecords:
        raise AssertionError("Rendering must not execute transforms")

    pipeline = Pipeline()
    source = pipeline.add_step(read_child)
    target = pipeline.add_step(prepare)
    pipeline.connect(source, target)
    figure = pipeline.visualize(show=False)
    labels = {text.get_text(): text.get_color() for text in figure.axes[0].texts}
    assert labels["ChildRecords · Instance"] == labels["Records · Instance"]


@pytest.mark.parametrize("extension", ["svg", "png"])
def test_visualize_exports_new_design(tmp_path, extension):
    pipeline = Pipeline()
    pipeline.add_step(read)
    figure = pipeline.visualize(show=False)
    path = tmp_path / f"pipeline.{extension}"
    figure.savefig(path)
    assert path.stat().st_size > 1000


def test_unconsumed_output_has_schema_band():

    pipeline = Pipeline()
    pipeline.add_step(read)
    figure = pipeline.visualize(show=False)
    assert (*_pale(_PALETTE[0]), 1.0) in [
        patch.get_facecolor() for patch in figure.axes[0].patches
    ]


def test_fanout_ribbons_are_opaque_to_prevent_darkening():
    pipeline = Pipeline()
    source = pipeline.add_step(read)
    for index in range(2):
        target = pipeline.add_step(prepare, f"prepare {index}")
        pipeline.connect(source, target)
    figure = pipeline.visualize(show=False)
    assert {
        list(patch.get_facecolor())[3]
        for patch in figure.axes[0].patches
        if isinstance(patch, PathPatch)
    } == {1.0}


@pytest.mark.parametrize("height", [-300, 300])
def test_steep_ribbons_keep_visible_thickness(height):

    upper, lower = _ribbon_contours((0, 0), (100, height))
    middle = len(upper) // 2
    vertical_width = upper[middle][1] - lower[middle][1]
    slope = height / 100 * 1.5

    assert vertical_width / hypot(1, slope) == pytest.approx(_NECK)


def test_void_output_has_no_schema_ribbon():

    @transform
    def sink() -> None:
        raise AssertionError("Rendering must not execute transforms")

    pipeline = Pipeline()
    pipeline.add_step(sink)
    figure = pipeline.visualize(show=False)
    schema_colours = {(*_pale(colour), 1.0) for colour in _PALETTE}
    assert not schema_colours.intersection(
        patch.get_facecolor() for patch in figure.axes[0].patches
    )


@pytest.mark.parametrize(
    "annotation", [Annotated[Records, Context()], Annotated[object, Context(Records)]]
)
def test_context_parameter_appears_inside_a_standalone_grey_input(annotation):

    @dataclass
    class Settings:
        records: Records

    def read_context(records):
        raise AssertionError("Rendering must not execute transforms")

    read_context.__annotations__ = {
        "records": annotation,
        "return": Records,
    }
    pipeline = Pipeline(Settings)
    pipeline.add_step(transform(read_context))
    figure = pipeline.visualize(show=False)
    ax = figure.axes[0]
    band = next(
        patch
        for patch in ax.patches
        if isinstance(patch, FancyBboxPatch)
        and patch.get_height() == _BAND
        and len(set(patch.get_facecolor()[:3])) == 1
    )
    labels = [
        text.get_text()
        for text in ax.texts
        if band.get_x() < text.get_position()[0] < band.get_x() + band.get_width()
        and band.get_y() < text.get_position()[1] < band.get_y() + band.get_height()
    ]

    assert labels == ["records", "Records · Ctx"]


def test_context_inputs_do_not_add_ribbons_to_connected_steps():
    @dataclass
    class Settings:
        features: Features
        model: Model

    @transform
    def evaluate_with_context(
        records: Records,
        features: Annotated[Features, Context()],
        model: Annotated[Model, Context()],
    ) -> None:
        raise AssertionError("Rendering must not execute transforms")

    pipeline = Pipeline(Settings)
    source = pipeline.add_step(read)
    target = pipeline.add_step(evaluate_with_context)
    pipeline.connect(source, target)

    figure = pipeline.visualize(show=False)

    assert sum(isinstance(patch, PathPatch) for patch in figure.axes[0].patches) == 1


def test_skipped_stage_ribbon_avoids_intermediate_card():
    pipeline = Pipeline()
    source = pipeline.add_step(read)
    prepared = pipeline.add_step(prepare)
    fitted = pipeline.add_step(fit)
    evaluated = pipeline.add_step(evaluate)
    pipeline.connect(source, prepared)
    pipeline.connect(prepared, fitted)
    pipeline.connect(prepared, evaluated, param="features")
    pipeline.connect(fitted, evaluated, param="model")
    figure = pipeline.visualize(show=False)
    # The model card is the only card producing Model; use the drawn card
    # bounds so this checks the final measured layout, not approximate text.

    model_label = next(
        text for text in figure.axes[0].texts if text.get_text() == "Model · Instance"
    )
    x, y = model_label.get_position()
    card = next(
        patch
        for patch in figure.axes[0].patches
        if isinstance(patch, FancyBboxPatch)
        and patch.get_facecolor() == (1, 1, 1, 1)
        and patch.get_x() < x < patch.get_x() + patch.get_width()
        and patch.get_y() < y < patch.get_y() + patch.get_height()
    )
    crossing_vertices = [
        (px, py)
        for patch in figure.axes[0].patches
        if isinstance(patch, PathPatch)
        for px, py in cast(Iterable[tuple[float, float]], patch.get_path().vertices)
        if card.get_x() + 20 < px < card.get_x() + card.get_width() - 20
    ]
    assert all(
        not card.get_y() < py < card.get_y() + card.get_height()
        for _, py in crossing_vertices
    )
