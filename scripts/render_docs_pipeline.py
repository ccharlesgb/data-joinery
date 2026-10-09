"""Render the documentation pipelines as SVG figures."""

from __future__ import annotations

import os
import runpy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache" / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt


def render_pipeline(
    example: Path, pipeline_name: str, output: Path, preview: Path | None = None
) -> None:
    with redirect_stdout(StringIO()):
        pipeline = runpy.run_path(str(example))[pipeline_name]
    figure = pipeline.visualize(show=False)
    figure.savefig(output, bbox_inches="tight", facecolor=figure.get_facecolor())
    if preview is not None:
        preview.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(
            preview, dpi=150, bbox_inches="tight", facecolor=figure.get_facecolor()
        )
    plt.close(figure)
    print(f"Saved {output}")


def main() -> None:
    render_pipeline(
        ROOT / "docs_src/learn/pipelines/index/pipeline_visualisation_polars.py",
        "order_pipeline",
        ROOT / "docs/images/pipeline-data-flow.svg",
        ROOT / "scratch/pipeline-visualisation/docs-pipeline.png",
    )
    render_pipeline(
        ROOT / "docs_src/index/minimum_example_polars.py",
        "order_metrics",
        ROOT / "docs/images/homepage-pipeline.svg",
    )


if __name__ == "__main__":
    main()
