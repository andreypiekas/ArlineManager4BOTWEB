"""Regression: read route labels from the real game's DOM structure in simulation."""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from fleet import _ROUTE_AUDIT_JS, audit_routes
from route_registry import RouteRegistry


def _read_game_rows(labels: list[str]) -> list[dict]:
    if not shutil.which("node"):
        pytest.skip("Node.js is required to execute embedded game DOM JavaScript")
    # Synthetic DOM following the route layout already documented in src/seats.py:
    # routeMainList<id>, fleet_details.php?id=<id>, .col-10 .s-text.
    mock = r"""
const labels = __LABELS__;
const rows = labels.map((route, i) => {
  const id = String(1000 + i);
  const link = {
    textContent: "XP-" + id + " - A380-800",
    getAttribute: name => name === "onclick" ? "Ajax('fleet_details.php?id=" + id + "', 'detailsAction')" : null
  };
  const routeEl = {textContent: route, getAttribute: () => null};
  return {
    id: "routeMainList" + id,
    querySelector: selector => {
      if (selector === "a[onclick*='fleet_details.php']" || selector === "a") return link;
      if (selector === ".col-10 .s-text") return routeEl;
      return null;
    },
    querySelectorAll: () => [link],
    getAttribute: () => null
  };
});
const document = {
  querySelectorAll: selector => selector.includes("routeMainList") ? rows : []
};
globalThis.document = document;
"""
    code = mock.replace("__LABELS__", json.dumps(labels)) + (
        "\nconsole.log(JSON.stringify((new Function(" +
        json.dumps(_ROUTE_AUDIT_JS) + "))()));\n"
    )
    run = subprocess.run(
        ["node", "-"], input=code, capture_output=True, text=True, check=False
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def test_20_aircraft_routes_are_identified_from_col10_s_text(tmp_path):
    # The old reader would return 20/0/20; the game-verified markup now
    # identifies all 20 independently of attribute data-dep/data-arr.
    labels = ["LEMD - EPRZ", "EPRZ - LEMD"] + ["SBGR - EIDW"] * 18
    rows = _read_game_rows(labels)
    assert len(rows) == 20
    assert rows[0]["aircraft_id"] == "1000"
    assert rows[0]["origin_code"] == "LEMD"
    assert rows[0]["destination_code"] == "EPRZ"
    assert rows[1]["origin_code"] == "EPRZ"
    assert rows[1]["destination_code"] == "LEMD"

    class FakeBot:
        def js(self, _script):
            return rows

    registry = RouteRegistry(tmp_path / "routes_registry.json")
    audit_routes(FakeBot(), registry)
    report = registry.snapshot(allow_duplicates=False)
    assert report["last_scan"] == {
        "at": report["last_scan"]["at"],
        "visible": 20, "identified": 20, "missing_airports": 0,
    }
    assert report["total"] == 20
    assert report["duplicate_routes"] == 2
    assert report["affected_aircraft"] == 20


def test_unknown_route_text_remains_unidentified_and_does_not_create_duplicate():
    rows = _read_game_rows(["In maintenance", ""])
    assert len(rows) == 2
    assert all(not r.get("origin_code") and not r.get("destination_code") for r in rows)


def test_icao_and_iata_3_or_4_letter_route_labels():
    rows = _read_game_rows(["DUB - GRU", "EGLL → SBGR", "DUB—GRU"])
    assert [(r["origin_code"], r["destination_code"]) for r in rows] == [
        ("DUB", "GRU"), ("EGLL", "SBGR"), ("DUB", "GRU")
    ]
