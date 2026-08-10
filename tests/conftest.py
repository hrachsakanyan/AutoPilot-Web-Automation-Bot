"""Pytest fixtures — one headless browser shared by the whole test session."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import Settings  # noqa: E402
from src.utils import build_driver, quit_driver  # noqa: E402


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--headed", action="store_true", help="show the browser window")
    parser.addoption("--browser", default="auto", help="auto, chrome, edge or firefox")


@pytest.fixture(scope="session")
def settings(request: pytest.FixtureRequest) -> Settings:
    return Settings(
        browser=request.config.getoption("--browser"),
        headless=not request.config.getoption("--headed"),
        timeout=15.0,
        retries=1,
    )


@pytest.fixture(scope="session")
def driver(settings: Settings):
    """A single browser for the session — starting Chrome per test is slow."""
    web_driver = build_driver(settings)
    yield web_driver
    quit_driver(web_driver)


@pytest.fixture(autouse=True)
def _screenshot_on_failure(request: pytest.FixtureRequest):
    """Capture the screen whenever a browser test fails."""
    yield
    report = getattr(request.node, "rep_call", None)
    if report is None or not report.failed:
        return
    if "driver" not in request.fixturenames:
        return
    from src.utils import take_screenshot

    take_screenshot(
        request.getfixturevalue("driver"),
        f"FAILED-{request.node.name}",
        request.getfixturevalue("settings"),
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Expose each phase's report to fixtures as item.rep_<phase>."""
    outcome = yield
    setattr(item, f"rep_{call.when}", outcome.get_result())
