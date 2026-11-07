"""Verify the separate route workspace and the JavaScript delivered to the browser."""
from __future__ import annotations

import shutil
import subprocess
from html.parser import HTMLParser

import pytest

from conftest import ROOT


class PageScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script_depth = 0
        self.code = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if props.get("id"):
            assert props["id"] not in self.ids, f"Duplicated HTML ID {props['id']}"
            self.ids.add(props["id"])
        if tag == "script" and "src" not in props:
            self.script_depth += 1

    def handle_endtag(self, tag):
        if tag == "script" and self.script_depth:
            self.script_depth -= 1

    def handle_data(self, data):
        if self.script_depth:
            self.code.append(data)


def test_route_dashboard_has_complete_controls():
    page = PageScripts()
    page.feed((ROOT / "assets/web/index.html").read_text(encoding="utf-8"))
    needed = {
        "routesView", "routesTable", "routeSearch", "routeRefresh",
        "routeSummary", "routeDuplicates", "routeHistory", "routeManual",
        "routeManualResult",
    }
    assert needed <= page.ids


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not available")
def test_browser_javascript_parses_on_node():
    page = PageScripts()
    page.feed((ROOT / "assets/web/index.html").read_text(encoding="utf-8"))
    result = subprocess.run(
        ["node", "--check", "-"],
        input="\n".join(page.code), text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
