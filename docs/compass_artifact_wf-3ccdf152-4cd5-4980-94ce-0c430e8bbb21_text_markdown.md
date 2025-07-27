# Streamlining visualization workflows from Jupyter to GitHub wikis and Hugo sites

After extensive research into modern visualization export alternatives and workflow solutions, the landscape has evolved significantly with several promising approaches that deliver matplotlib-like simplicity while maintaining professional quality across all platforms. The new Kaleido v1.0 architecture and emerging tools like Quarto fundamentally change how we approach this challenge.

## Plotly export beyond kaleido complexity

The visualization export landscape experienced a major shift in 2024 when **Kaleido was completely re-architected**. The new version, built on the Choreographer library, is thousands of times smaller and significantly more reliable than its predecessor. However, for those seeking alternatives, **Playwright has emerged as the most robust solution**, offering excellent cross-platform support and reliability that surpasses traditional approaches.

For immediate implementation, here's the simplest Playwright-based export:

```python
import plotly.express as px
from playwright.sync_api import sync_playwright
import os

def export_plotly_simple(fig, filename="plot.png"):
    # Save to HTML first
    html_file = "temp_plot.html"
    fig.write_html(html_file)
    
    # Use Playwright to capture
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{os.path.abspath(html_file)}")
        page.screenshot(path=filename, full_page=True)
        browser.close()
    
    os.remove(html_file)
```

For those who want a unified API across visualization libraries, **chartpy** provides the cleanest solution. This library offers identical syntax for matplotlib, plotly, and bokeh, allowing seamless backend switching:

```python
from chartpy import Chart

# Create chart with matplotlib-like simplicity
chart = Chart()
chart.plot([1, 2, 3], [4, 5, 6])

# Export using any backend
chart.plot(engine='matplotlib')  # PNG export
chart.plot(engine='plotly')      # Interactive HTML
```

## GitHub wiki visualization best practices

GitHub wikis now offer **robust support for static visualizations** with some notable improvements. The platform fully supports PNG, JPEG, SVG, and GIF formats, with SVG support enhanced in 2022 to include proper sanitization. Most significantly, GitHub wikis now natively render Mermaid diagrams, mathematical expressions, and even GeoJSON maps.

For optimal compatibility, follow these guidelines:

**Recommended formats by use case:**
- **Static charts and plots**: PNG at 600-800px width for best readability
- **Scalable diagrams**: SVG with the `?sanitize=true` parameter
- **Flowcharts and diagrams**: Native Mermaid syntax in code blocks
- **Mathematical visualizations**: LaTeX expressions with `$...$` syntax

Image storage should utilize the wiki repository's own Git backend:

```bash
# Clone wiki repository
git clone https://github.com/user/repo.wiki.git
cd repo.wiki

# Create organized structure
mkdir -p images/charts images/screenshots

# Reference in wiki pages
![Chart Description](images/charts/analysis-01.png)
```

Size control requires HTML syntax since standard Markdown sizing isn't supported:

```html
<img src="images/charts/performance.png" width="600" alt="Performance Analysis">
```

## Hugo integration strategies

Hugo provides **exceptionally flexible visualization integration** through its asset pipeline and template system. The most effective approach uses page bundles to co-locate content with visualizations:

```
content/
├── posts/
│   ├── data-analysis/
│   │   ├── index.md
│   │   ├── chart1.png
│   │   ├── plot.svg
│   │   └── interactive.html
```

Create a universal visualization shortcode for consistent handling:

```go
{{/* layouts/shortcodes/figure-responsive.html */}}
{{ $src := .Get "src" }}
{{ with .Page.Resources.GetMatch $src }}
  {{ $small := .Resize "400x" }}
  {{ $medium := .Resize "800x" }}
  {{ $large := .Resize "1200x" }}
  <picture>
    <source media="(max-width: 400px)" srcset="{{ $small.RelPermalink }}">
    <source media="(max-width: 800px)" srcset="{{ $medium.RelPermalink }}">
    <img src="{{ $large.RelPermalink }}" alt="{{ $.Get "alt" }}" loading="lazy">
  </picture>
{{ end }}
```

For interactive visualizations, the JSON-based approach offers the best balance of performance and flexibility:

```python
# In Jupyter
fig.write_json("static/data/chart.json")

# In Hugo content
{{< plotly json="/data/chart.json" height="400px" >}}
```

## Complete workflow recommendations

After analyzing all available solutions, **two workflows stand out for their simplicity and effectiveness**:

### Workflow 1: Quarto-based (recommended for new projects)

Quarto represents the modern evolution of computational document publishing, offering true "write once, deploy everywhere" capabilities:

```bash
# Install Quarto
pip install jupyter matplotlib plotly nbformat

# Create Quarto document from notebook
quarto convert notebook.ipynb

# Render to multiple formats
quarto render notebook.qmd --to html  # For Hugo
quarto render notebook.qmd --to gfm   # For GitHub wiki
```

Configure Quarto for automatic handling:

```yaml
# _quarto.yml
project:
  output-dir: _output
  
format:
  html:
    theme: cosmo
    embed-resources: true
  gfm:
    fig-width: 8
    fig-height: 6
```

### Workflow 2: nb2hugo with automation (best for existing Hugo sites)

The nb2hugo package provides the most straightforward integration for existing Hugo workflows:

```python
# Install
pip install nb2hugo

# Add front matter to notebook's first markdown cell
# Title: My Analysis
# Date: 2025-01-27
# Tags: data-science, visualization
# <!--eofm-->

# Convert with single command
nb2hugo notebook.ipynb --site-dir hugo-site --section posts
```

Automate with GitHub Actions:

```yaml
name: Publish Notebooks
on:
  push:
    paths: ['notebooks/**/*.ipynb']

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Convert and Deploy
        run: |
          pip install nb2hugo jupyter
          for nb in notebooks/*.ipynb; do
            nb2hugo "$nb" --site-dir . --section posts
          done
      - name: Build Hugo
        uses: peaceiris/actions-hugo@v3
      - name: Deploy
        uses: peaceiris/actions-gh-pages@v3
```

## Practical implementation guide

For a complete solution that achieves matplotlib-like simplicity, combine these tools:

```python
# unified_viz_export.py
import plotly.express as px
from pathlib import Path
from playwright.sync_api import sync_playwright

class SimpleVizExporter:
    def __init__(self, output_dir="exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def export(self, fig, name, formats=['png', 'svg', 'html']):
        """Export Plotly figure to multiple formats with one call"""
        base_path = self.output_dir / name
        
        if 'html' in formats:
            fig.write_html(f"{base_path}.html")
        
        if 'png' in formats or 'svg' in formats:
            # Use Playwright for static exports
            temp_html = f"{base_path}_temp.html"
            fig.write_html(temp_html)
            
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(f"file://{Path(temp_html).absolute()}")
                
                if 'png' in formats:
                    page.screenshot(path=f"{base_path}.png", full_page=True)
                if 'svg' in formats:
                    # Plotly's native SVG export
                    fig.write_image(f"{base_path}.svg", format='svg')
                
                browser.close()
            Path(temp_html).unlink()
        
        return {fmt: f"{base_path}.{fmt}" for fmt in formats}

# Usage - matplotlib-like simplicity
exporter = SimpleVizExporter()
fig = px.scatter(x=[1,2,3], y=[4,5,6])
paths = exporter.export(fig, "analysis_plot")
```

This approach delivers on the promise of matplotlib-like simplicity while maintaining the power of modern visualization libraries. The combination of Playwright for reliable exports, Quarto or nb2hugo for workflow automation, and Hugo's flexible asset handling creates a robust pipeline that works seamlessly across all three platforms.