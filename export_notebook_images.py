#!/usr/bin/env python3
"""
Export all Plotly figures from analysis notebook to images for wiki.
"""

import json
from pathlib import Path
import plotly.graph_objects as go
import plotly.io as pio

# Set up paths
NOTEBOOK_PATH = Path("analysis.ipynb")
WIKI_IMAGES_DIR = Path("wiki-repo/images")

# Create wiki images directory
WIKI_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Configure plotly for static image export
# Note: Requires kaleido package: pip install kaleido
pio.kaleido.scope.default_width = 1200
pio.kaleido.scope.default_height = 600


def extract_plotly_figures_from_notebook(notebook_path):
    """Extract all Plotly figures from a Jupyter notebook."""

    with open(notebook_path, "r") as f:
        notebook = json.load(f)

    figures = []
    figure_count = 0

    for cell_num, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code" and "outputs" in cell:
            for output in cell["outputs"]:
                # Check for plotly figure in output
                if "data" in output and "application/vnd.plotly.v1+json" in output["data"]:
                    figure_data = output["data"]["application/vnd.plotly.v1+json"]

                    # Reconstruct the figure
                    fig = go.Figure(figure_data)

                    # Determine figure name based on title or position
                    if fig.layout.title and fig.layout.title.text:
                        # Clean title for filename
                        title = fig.layout.title.text
                        filename = title.lower().replace(" ", "_").replace(":", "").replace("!", "")
                        filename = "".join(c for c in filename if c.isalnum() or c in "_-")
                    else:
                        filename = f"figure_{figure_count}"

                    figures.append(
                        {
                            "fig": fig,
                            "filename": filename,
                            "cell_num": cell_num,
                            "title": fig.layout.title.text
                            if fig.layout.title
                            else f"Figure {figure_count}",
                        }
                    )
                    figure_count += 1

    return figures


def main():
    """Export all figures from notebook to wiki images."""

    print("Extracting Plotly figures from notebook...")
    figures = extract_plotly_figures_from_notebook(NOTEBOOK_PATH)

    print(f"Found {len(figures)} Plotly figures")

    # Export each figure
    for i, fig_info in enumerate(figures):
        fig = fig_info["fig"]
        filename = fig_info["filename"]

        # Save as PNG
        png_path = WIKI_IMAGES_DIR / f"{filename}.png"
        fig.write_image(str(png_path))
        print(f"Exported: {png_path}")

        # Also save as interactive HTML for reference
        html_path = WIKI_IMAGES_DIR / f"{filename}.html"
        fig.write_html(str(html_path))

    # Create an index file
    index_path = WIKI_IMAGES_DIR / "index.md"
    with open(index_path, "w") as f:
        f.write("# Exported Figures\n\n")
        for fig_info in figures:
            f.write(f"## {fig_info['title']}\n")
            f.write(f"- Cell: {fig_info['cell_num']}\n")
            f.write(f"- Image: ![{fig_info['title']}](images/{fig_info['filename']}.png)\n")
            f.write(f"- [Interactive HTML](images/{fig_info['filename']}.html)\n\n")

    print(f"\nExported {len(figures)} figures to {WIKI_IMAGES_DIR}")
    print(f"Index created at {index_path}")


if __name__ == "__main__":
    main()
