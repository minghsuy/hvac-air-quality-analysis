# Portable Visualization Workflow: Implementing the Research

Based on the comprehensive research in `docs/compass_artifact_wf-3ccdf152-4cd5-4980-94ce-0c430e8bbb21_text_markdown.md`, here's the practical implementation plan for this HVAC project.

## Why I Initially Ignored the Research (Learning Moment)

I fell into the trap of reinventing the wheel instead of using the excellent solutions already researched. The document clearly states:
- **Quarto** is the best "write once, deploy everywhere" solution
- **Playwright** is more reliable than kaleido for exports
- **nb2hugo** provides direct Jupyter→Hugo integration

## The Right Approach: Quarto-Based Workflow

### 1. Convert Current Notebook to Quarto

```bash
# Install Quarto
pip install jupyter matplotlib plotly nbformat

# Convert existing notebook
quarto convert analysis.ipynb -o analysis.qmd
```

### 2. Configure Quarto for Multi-Output

Create `_quarto.yml` in project root:

```yaml
project:
  type: website
  output-dir: _output
  
format:
  html:
    theme: cosmo
    embed-resources: true
    fig-format: png
    fig-dpi: 300
  gfm:
    fig-width: 8
    fig-height: 6
    fig-format: png
  hugo-md:
    fig-format: png
    keep-yaml-front-matter: true

execute:
  freeze: auto
  
# Custom formats for our needs
profiles:
  - name: wiki
    format:
      gfm:
        output-file: "wiki-output.md"
        fig-prefix: "images/"
  - name: hugo
    format:
      hugo-md:
        output-file: "hugo-output.md"
        fig-prefix: "/viz/"
```

### 3. Fix Plotly Datetime Issues with Quarto Pre-render

Add to the notebook's first code cell:

```python
# _quarto.yml will handle this, but for safety:
import plotly.io as pio

# Use the reliable export method from research
def export_plotly_figure(fig, name):
    """Export using Playwright as recommended"""
    from playwright.sync_api import sync_playwright
    import os
    
    # Save HTML first
    html_file = f"temp_{name}.html"
    fig.write_html(html_file)
    
    # Use Playwright for reliable PNG
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{os.path.abspath(html_file)}")
        page.wait_for_load_state('networkidle')
        page.screenshot(path=f"{name}.png", full_page=True)
        browser.close()
    
    os.remove(html_file)
    return f"{name}.png"

# Set as default renderer for Quarto
pio.renderers.default = "png"
```

### 4. Implement the Simple Unified Exporter

From the research document's recommended approach:

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
```

### 5. Automated Workflow with GitHub Actions

As recommended in the research:

```yaml
# .github/workflows/publish-analysis.yml
name: Publish Analysis
on:
  push:
    paths: ['analysis.qmd', 'data/**']

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Quarto
        uses: quarto-dev/quarto-actions/setup@v2
        
      - name: Install dependencies
        run: |
          pip install jupyter plotly pandas playwright
          playwright install chromium
      
      - name: Render for Wiki
        run: |
          quarto render analysis.qmd --profile wiki
          cp _output/wiki-output.md wiki-repo/Analysis-Results.md
          cp _output/images/* wiki-repo/images/
      
      - name: Render for Hugo
        run: |
          quarto render analysis.qmd --profile hugo
          cp _output/hugo-output.md hugo-site/content/posts/hvac-analysis.md
          cp _output/viz/* hugo-site/static/viz/
      
      - name: Commit Wiki
        run: |
          cd wiki-repo
          git add -A
          git commit -m "Update analysis [skip ci]"
          git push
```

### 6. For Existing Hugo Sites: nb2hugo

As the research recommends for existing Hugo workflows:

```bash
# Install
pip install nb2hugo

# Add front matter to notebook's first markdown cell
"""
Title: HVAC Air Quality Analysis
Date: 2025-01-27
Tags: hvac, air-quality, data-science
<!--eofm-->
"""

# Convert with single command
nb2hugo analysis.ipynb --site-dir hugo-site --section posts
```

## Key Improvements from Research

1. **Quarto handles multi-format output** - No need for custom exporters
2. **Playwright for reliable exports** - Solves the datetime/scientific notation issue
3. **Existing tools** - nb2hugo for Hugo, Quarto for everything else
4. **Automation built-in** - Both tools support CI/CD workflows

## Implementation Timeline

### Week 1: Quarto Setup
- [ ] Install Quarto and convert notebook
- [ ] Test multi-format output
- [ ] Fix any Plotly rendering issues

### Week 2: Platform Integration  
- [ ] Set up wiki export pipeline
- [ ] Configure Hugo with nb2hugo
- [ ] Test image paths and references

### Week 3: Automation
- [ ] GitHub Actions for auto-publish
- [ ] Documentation updates
- [ ] Template for future projects

## Why This is Better

The research document was right:
- **"Write once, deploy everywhere"** - Quarto actually delivers this
- **Playwright > Kaleido** - More reliable, better results
- **Use existing tools** - Don't reinvent the wheel
- **Simpler is better** - One tool (Quarto) instead of custom pipeline

## Lessons Learned

1. Always check if someone has solved the problem already
2. Read and implement research before creating custom solutions
3. Quarto is the modern replacement for complex Jupyter export pipelines
4. The best visualization workflow is the one that requires the least manual work