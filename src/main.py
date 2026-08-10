"""AutoPilot entry point.

Drives three flows against the-internet.herokuapp.com, a public sandbox
published for automation practice:

  login  - data-driven logins from a CSV (valid + invalid rows)
  form   - dynamic controls: remove a checkbox, enable a field, type
  table  - extract a data table and save it to output/table_data.csv

Usage:
    python -m src.main --flow all
    python -m src.main --flow table --headless
    python -m src.main --flow login --users data/users.csv --retries 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow both `python -m src.main` (preferred) and `python src/main.py`.
if __package__ in (None, ""):  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from selenium.common.exceptions import WebDriverException  # noqa: E402
from selenium.webdriver.remote.webdriver import WebDriver  # noqa: E402

from src.config import (  # noqa: E402
    DATA_DIR,
    DEMO_PASSWORD,
    DEMO_USERNAME,
    SUPPORTED_BROWSERS,
    Settings,
)
from src.exceptions import AutoPilotError, LoginFailedError  # noqa: E402
from src.pages import DynamicControlsPage, LoginPage, TablesPage  # noqa: E402
from src.utils import (  # noqa: E402
    build_driver,
    get_logger,
    quit_driver,
    read_csv,
    retry,
    take_screenshot,
    write_csv,
)

log = get_logger("main")

FLOWS = ("login", "form", "table")


# --------------------------------------------------------------------------
# Flows
# --------------------------------------------------------------------------
def run_login_flow(
    driver: WebDriver, settings: Settings, users_csv: Path | None
) -> list[dict[str, str]]:
    """Log in once per CSV row and check each result against `expect`.

    CSV columns: username, password, expect (success|failure), note
    Falls back to the two public demo rows when no CSV is given.
    """
    if users_csv and users_csv.exists():
        users = read_csv(users_csv)
    else:
        if users_csv:
            log.warning("%s not found — using built-in demo credentials", users_csv)
        users = [
            {"username": DEMO_USERNAME, "password": DEMO_PASSWORD, "expect": "success"},
            {"username": DEMO_USERNAME, "password": "wrong-password", "expect": "failure"},
        ]

    login_page = LoginPage(driver, settings)
    results: list[dict[str, str]] = []

    for index, user in enumerate(users, start=1):
        username = user.get("username", "").strip()
        password = user.get("password", "").strip()
        expected = (user.get("expect") or "success").strip().lower()

        log.info("--- login case %d/%d: %r (expect %s)", index, len(users), username, expected)
        login_page.open()

        outcome, message = "success", ""
        try:
            secure_area = login_page.login(username, password)
            message = secure_area.subheading()
            secure_area.screenshot(f"login-{index}-success")
            secure_area.logout()
        except LoginFailedError as exc:
            outcome, message = "failure", str(exc)
            login_page.screenshot(f"login-{index}-failure")

        matched = outcome == expected
        log.info(
            "Case %d: got %s, expected %s -> %s",
            index,
            outcome,
            expected,
            "OK" if matched else "MISMATCH",
        )
        results.append(
            {
                "case": str(index),
                "username": username,
                "expected": expected,
                "outcome": outcome,
                "matched": "yes" if matched else "no",
                "message": message,
            }
        )

    write_csv(settings.output_dir / "login_results.csv", results)
    return results


def run_form_flow(driver: WebDriver, settings: Settings) -> dict[str, str]:
    """Exercise the dynamic controls page: waits, not sleeps."""
    page = DynamicControlsPage(driver, settings)
    page.open()
    page.screenshot("dynamic-controls-before")

    result = page.run_flow(text="AutoPilot was here")

    page.screenshot("dynamic-controls-after")
    log.info(
        "Checkbox removed=%s (%r); input enabled=%s (%r); typed=%r",
        result.checkbox_removed,
        result.checkbox_message,
        result.input_enabled,
        result.input_message,
        result.typed_text,
    )
    return {
        "checkbox_removed": str(result.checkbox_removed),
        "checkbox_message": result.checkbox_message,
        "input_enabled": str(result.input_enabled),
        "input_message": result.input_message,
        "typed_text": result.typed_text,
    }


def run_table_flow(driver: WebDriver, settings: Settings) -> list[dict[str, str]]:
    """Extract the sortable data table and persist it as CSV."""
    page = TablesPage(driver, settings)
    page.open()

    page.sort_by("Last Name")
    rows = page.rows()
    page.screenshot("table-sorted-by-last-name")

    output = write_csv(settings.output_dir / "table_data.csv", rows, headers=page.headers())
    log.info("Table saved to %s", output)

    for row in rows:
        log.info(
            "  %-10s %-10s %s",
            row.get("Last Name", ""),
            row.get("First Name", ""),
            row.get("Email", ""),
        )
    return rows


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def run(settings: Settings, flow: str, users_csv: Path | None) -> int:
    """Start a browser, run the requested flow(s), always shut down cleanly."""
    driver: WebDriver | None = None
    exit_code = 0

    # Retry the whole session: a cold Heroku dyno can time out on the first hit.
    launch = retry(
        attempts=settings.attempts,
        delay=settings.retry_delay,
        exceptions=(WebDriverException, AutoPilotError),
    )(_run_flows)

    try:
        driver = build_driver(settings)
        launch(driver, settings, flow, users_csv)
        log.info("AutoPilot finished: flow=%s", flow)
    except AutoPilotError as exc:
        log.error("%s: %s", exc.__class__.__name__, exc)
        exit_code = 1
    except WebDriverException as exc:
        log.error("Browser error: %s", getattr(exc, "msg", exc))
        exit_code = 1
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        exit_code = 130
    finally:
        if driver is not None and exit_code == 1:
            take_screenshot(driver, "failure", settings)
        quit_driver(driver)

    return exit_code


def _run_flows(
    driver: WebDriver, settings: Settings, flow: str, users_csv: Path | None
) -> None:
    if flow in ("login", "all"):
        run_login_flow(driver, settings, users_csv)
    if flow in ("form", "all"):
        run_form_flow(driver, settings)
    if flow in ("table", "all"):
        run_table_flow(driver, settings)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="autopilot",
        description="Educational Selenium automation against a permitted practice site.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--flow", choices=(*FLOWS, "all"), default="all", help="which flow to run")
    parser.add_argument(
        "--browser",
        choices=SUPPORTED_BROWSERS,
        default="auto",
        help="'auto' picks an installed browser whose driver version matches it",
    )
    parser.add_argument("--headless", action="store_true", help="run without a visible window")
    parser.add_argument("--timeout", type=float, default=10.0, help="explicit wait budget (s)")
    parser.add_argument("--retries", type=int, default=2, help="extra attempts per run")
    parser.add_argument(
        "--users",
        type=Path,
        default=DATA_DIR / "users.csv",
        help="CSV of login cases for the data-driven flow",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = Settings(
        browser=args.browser,
        headless=args.headless,
        timeout=args.timeout,
        retries=args.retries,
    )
    return run(settings, args.flow, args.users)


if __name__ == "__main__":
    raise SystemExit(main())
