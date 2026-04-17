#!/usr/bin/env python3
"""Open docs/reports/findings.html in headless Chromium, screenshot each chart,
and verify both have non-trivial render area (i.e. plotly actually rendered).

Use after regenerating the HTML to catch load-order bugs before commit.

Usage:  uv run python scripts/analysis/screenshot_report.py
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = REPO_ROOT / "docs" / "reports" / "findings.html"
SHOT_DIR = REPO_ROOT / "reports" / "screenshots"  # ephemeral, stays at repo root (gitignored)

# Minimum pixel area a chart div must fill to be considered "rendered". An
# unrendered plotly div collapses to near-zero height.
MIN_CHART_AREA = 100_000  # e.g. 800 × 125


def main() -> int:
    if not HTML_PATH.exists():
        print(f"missing: {HTML_PATH}", file=sys.stderr)
        return 1

    SHOT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto(HTML_PATH.as_uri())
        page.wait_for_load_state("networkidle", timeout=15000)

        chart_divs = page.locator(".plotly-graph-div").all()
        if len(chart_divs) < 2:
            print(f"FAIL: found {len(chart_divs)} plotly div(s), expected 2", file=sys.stderr)
            browser.close()
            return 1

        ok = True
        for i, div in enumerate(chart_divs, start=1):
            box = div.bounding_box()
            if box is None:
                print(f"FAIL: chart {i} has no bounding box", file=sys.stderr)
                ok = False
                continue
            area = int(box["width"] * box["height"])
            shot = SHOT_DIR / f"chart_{i}.png"
            div.screenshot(path=str(shot))
            status = "ok" if area >= MIN_CHART_AREA else "FAIL"
            print(
                f"chart {i}: {int(box['width'])}×{int(box['height'])} = {area:,} px² [{status}]  {shot.name}"
            )
            if area < MIN_CHART_AREA:
                ok = False

        # Full-page screenshot for the record
        full = SHOT_DIR / "full_page.png"
        page.screenshot(path=str(full), full_page=True)
        print(f"full page: {full.name}")

        browser.close()
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
