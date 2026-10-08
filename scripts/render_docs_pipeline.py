"""Render the branch and join pipeline from the documentation as an SVG figure."""

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


def main() -> None:
    example = ROOT / "docs_src/learn/pipelines/index/pipeline_visualisation_polars.py"
    with redirect_stdout(StringIO()):
        pipeline = runpy.run_path(str(example))["order_pipeline"]
    figure = pipeline.visualize(show=False)
    output = ROOT / "docs/images/pipeline-data-flow.svg"
    figure.savefig(output, bbox_inches="tight", facecolor=figure.get_facecolor())
    preview = ROOT / "scratch/pipeline-visualisation/docs-pipeline.png"
    preview.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        preview, dpi=150, bbox_inches="tight", facecolor=figure.get_facecolor()
    )
    plt.close(figure)
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
