"""Regression: simulation must not depart aircraft, and route scan is read-only."""
from bot import Bot
from fleet import audit_routes
from route_registry import RouteRegistry


class FakeButton:
    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def get_attribute(self, key):
        return ""


class FakeDepartBot:
    dry_run = True

    class Config:
        def get_bool(self, section, name, default=False):
            return default

    config = Config()

    def __init__(self):
        self.opened = False
        self.closed = False
        self.clicked = 0

    def open_popup(self, *args):
        self.opened = True

    def close_popup(self):
        self.closed = True

    def _sel(self, key):
        return key

    def _find(self, *args, **kwargs):
        return FakeButton()

    def pause(self):
        raise AssertionError("Simulation must not pause for a click")

    def click_element(self, *args):
        self.clicked += 1
        raise AssertionError("Simulation must not trigger Depart All")


def test_dry_run_never_clicks_depart_all():
    fake = FakeDepartBot()
    Bot._depart_all(fake)
    assert fake.opened and fake.closed
    assert fake.clicked == 0


class FakeReadBot:
    def __init__(self, rows):
        self.rows = rows
        self.dry_run = True

    def js(self, script):
        return self.rows


def test_route_scan_reports_missing_airports_even_in_simulation(tmp_path):
    registry = RouteRegistry(tmp_path / "routes_registry.json")
    audit_routes(FakeReadBot([{
        "aircraft_id": "12", "registration": "XP-12", "model": "A320",
        "origin_id": "", "destination_id": "", "origin_code": "", "destination_code": "",
        "in_flight": False,
    }]), registry)
    snapshot = registry.snapshot()
    assert snapshot["relations"][0]["status"] == "rota_nao_identificada"
    assert snapshot["last_scan"]["visible"] == 1
    assert snapshot["last_scan"]["identified"] == 0
    assert snapshot["last_scan"]["missing_airports"] == 1


def test_route_scan_identifies_airports_in_simulation(tmp_path):
    registry = RouteRegistry(tmp_path / "routes_registry.json")
    audit_routes(FakeReadBot([{
        "aircraft_id": "12", "registration": "XP-12", "model": "A320",
        "origin_code": "DUB", "destination_code": "GRU", "in_flight": False,
    }]), registry)
    snapshot = registry.snapshot()
    assert snapshot["relations"][0]["origin"]["code"] == "DUB"
    assert snapshot["relations"][0]["destination"]["code"] == "GRU"
    assert snapshot["last_scan"]["identified"] == 1
    assert snapshot["last_scan"]["missing_airports"] == 0
