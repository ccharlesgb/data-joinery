from __future__ import annotations

import pytest

from data_joinery import Pipeline, transform
from data_joinery.visualisation import topological_layout


class Records: ...


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
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

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
    assert {"features", "model", "OUT", "No output"} <= set(labels)
    image = tmp_path / "pipeline.png"
    figure.savefig(image)
    assert image.stat().st_size > 1000
    plt.close(figure)


def test_empty_pipeline_visualization():
    pytest.importorskip("matplotlib")
    from matplotlib import pyplot as plt

    figure = Pipeline().visualize(show=False)
    assert "No steps in this pipeline" in [
        text.get_text() for text in figure.axes[0].texts
    ]
    plt.close(figure)
