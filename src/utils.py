"""Shared helpers: logging, driver factory, retries, screenshots, CSV I/O."""

from __future__ import annotations

import csv
import functools
import logging
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence, TypeVar
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver

from src.config import ALLOWED_HOSTS, BROWSER_PREFERENCE, LOG_DIR, Settings
from src.exceptions import DriverSetupError, UnsafeTargetError

T = TypeVar("T")

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-18s | %(message)s"
_configured = False


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
def configure_logging(level: int = logging.INFO, log_dir: Path = LOG_DIR) -> None:
    """Attach a console handler and a file handler exactly once."""
    global _configured
    if _configured:
        return

    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("autopilot")
    root.setLevel(level)
    root.propagate = False

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt="%H:%M:%S"))
    root.addHandler(console)

    file_handler = logging.FileHandler(log_dir / "autopilot.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(file_handler)

    # Selenium's own logging is noisy at INFO; keep it for warnings only.
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("WDM").setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(f"autopilot.{name}")


log = get_logger("utils")


# --------------------------------------------------------------------------
# Safety guard
# --------------------------------------------------------------------------
def assert_allowed(url: str) -> str:
    """Reject any URL whose host is not on the allow-list.

    Every navigation in this project funnels through here, which is what
    keeps an "educational automation" project educational.
    """
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise UnsafeTargetError(
            f"Refusing to automate {host or url!r}. "
            f"Allowed hosts: {', '.join(sorted(ALLOWED_HOSTS))}. "
            "Only drive sites that explicitly permit automation."
        )
    return url


# --------------------------------------------------------------------------
# Retry
# --------------------------------------------------------------------------
def retry(
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (WebDriverException,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry a flaky call with exponential backoff.

    Used for whole flows (a page can fail to load once) rather than for
    single element lookups — those are handled by explicit waits.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_error: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: PERF203 - retry is the point
                    last_error = exc
                    if attempt == attempts:
                        break
                    log.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                        func.__name__,
                        attempt,
                        attempts,
                        exc.__class__.__name__,
                        current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            assert last_error is not None
            log.error("%s failed after %d attempts", func.__name__, attempts)
            raise last_error

        return wrapper

    return decorator


# --------------------------------------------------------------------------
# Driver factory
# --------------------------------------------------------------------------
def _chrome_options(settings: Settings) -> ChromeOptions:
    options = ChromeOptions()
    if settings.headless:
        options.add_argument("--headless=new")
    width, height = settings.window_size
    options.add_argument(f"--window-size={width},{height}")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-search-engine-choice-screen")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return options


def _edge_options(settings: Settings) -> EdgeOptions:
    options = EdgeOptions()
    if settings.headless:
        options.add_argument("--headless=new")
    width, height = settings.window_size
    options.add_argument(f"--window-size={width},{height}")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    return options


def _firefox_options(settings: Settings) -> FirefoxOptions:
    options = FirefoxOptions()
    if settings.headless:
        options.add_argument("-headless")
    width, height = settings.window_size
    options.add_argument(f"--width={width}")
    options.add_argument(f"--height={height}")
    return options


# Where each browser normally lives, used only to skip candidates that are
# obviously not installed before paying the cost of starting them.
_BROWSER_BINARIES: dict[str, tuple[str, ...]] = {
    "chrome": (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "google-chrome",
        "chrome",
    ),
    "edge": (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "microsoft-edge",
        "msedge",
    ),
    "firefox": (
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        "/Applications/Firefox.app/Contents/MacOS/firefox",
        "firefox",
    ),
}


def is_installed(browser: str) -> bool:
    return any(
        Path(candidate).exists() or shutil.which(candidate)
        for candidate in _BROWSER_BINARIES.get(browser, ())
    )


def version_pair(driver: WebDriver) -> tuple[str, str | None]:
    """(browser version, driver version) — driver version None if unknown.

    A Chromium driver whose version does not match its browser exactly can
    start up fine and then silently stop delivering clicks and keystrokes,
    so this is worth checking rather than assuming.
    """
    caps = driver.capabilities
    browser_version = str(caps.get("browserVersion", "?"))
    for key, field in (("chrome", "chromedriverVersion"), ("msedge", "msedgedriverVersion")):
        section = caps.get(key)
        if isinstance(section, dict) and section.get(field):
            # e.g. "150.0.7871.124 (9261fd0a...)" -> "150.0.7871.124"
            return browser_version, str(section[field]).split(" ", 1)[0]
    # geckodriver versions are unrelated to Firefox versions; nothing to compare.
    return browser_version, None


def build_driver(settings: Settings) -> WebDriver:
    """Start a browser and hand back a ready driver."""
    log.info(
        "Starting %s (headless=%s, timeout=%ss)",
        settings.browser,
        settings.headless,
        settings.timeout,
    )
    driver = (
        _build_auto(settings)
        if settings.browser == "auto"
        else _start_browser(settings.browser, settings)
    )

    driver.set_page_load_timeout(max(settings.timeout * 3, 30))
    if not settings.headless:
        driver.set_window_size(*settings.window_size)

    browser_version, driver_version = version_pair(driver)
    log.info(
        "Browser ready: %s %s (driver %s)",
        driver.capabilities.get("browserName", "?"),
        browser_version,
        driver_version or "n/a",
    )
    return driver


def _build_auto(settings: Settings) -> WebDriver:
    """Pick the first installed browser whose driver version matches it."""
    candidates = [name for name in BROWSER_PREFERENCE if is_installed(name)]
    if not candidates:
        log.warning("No known browser found on disk; trying chrome anyway")
        candidates = ["chrome"]

    for name in candidates:
        try:
            driver = _start_browser(name, settings)
        except DriverSetupError as exc:
            log.warning("Skipping %s: %s", name, exc)
            continue

        browser_version, driver_version = version_pair(driver)
        if driver_version is None or driver_version == browser_version:
            return driver

        log.warning(
            "Skipping %s: browser is %s but its driver is %s. "
            "Mismatched Chromium drivers can stop delivering clicks and "
            "keystrokes after the first page change.",
            name,
            browser_version,
            driver_version,
        )
        quit_driver(driver)

    # Nothing matched perfectly — use the preferred browser and say so.
    fallback = candidates[0]
    log.warning("No exactly-matched driver found; falling back to %s", fallback)
    return _start_browser(fallback, settings)


def _start_browser(browser: str, settings: Settings) -> WebDriver:
    """Start one browser.

    Selenium 4.6+ ships Selenium Manager, which fetches the matching driver
    itself. webdriver-manager is the fallback when that cannot run (older
    Selenium, restricted network, pre-seeded cache).
    """
    try:
        return _start_with_selenium_manager(browser, settings)
    except WebDriverException as first_error:
        log.warning(
            "Selenium Manager could not start %s: %s",
            browser,
            getattr(first_error, "msg", first_error),
        )
        return _start_with_webdriver_manager(browser, settings, first_error)


def _start_with_selenium_manager(browser: str, settings: Settings) -> WebDriver:
    if browser == "chrome":
        return webdriver.Chrome(options=_chrome_options(settings))
    if browser == "edge":
        return webdriver.Edge(options=_edge_options(settings))
    return webdriver.Firefox(options=_firefox_options(settings))


def _start_with_webdriver_manager(
    browser: str, settings: Settings, first_error: Exception
) -> WebDriver:
    """Second attempt at starting a browser, via webdriver-manager."""
    try:
        if browser == "chrome":
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager

            service = ChromeService(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=_chrome_options(settings))

        if browser == "edge":
            from selenium.webdriver.edge.service import Service as EdgeService
            from webdriver_manager.microsoft import EdgeChromiumDriverManager

            service = EdgeService(EdgeChromiumDriverManager().install())
            return webdriver.Edge(service=service, options=_edge_options(settings))

        from selenium.webdriver.firefox.service import Service as FirefoxService
        from webdriver_manager.firefox import GeckoDriverManager

        service = FirefoxService(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=_firefox_options(settings))
    except Exception as exc:  # noqa: BLE001 - report both failures together
        raise DriverSetupError(
            f"Could not start {browser}. "
            f"Selenium Manager said: {first_error}. "
            f"webdriver-manager said: {exc}. "
            "Check that the browser is installed and reachable."
        ) from exc


def quit_driver(driver: WebDriver | None) -> None:
    """Shut the browser down without ever masking the original error."""
    if driver is None:
        return
    try:
        driver.quit()
        log.info("Browser closed cleanly")
    except WebDriverException as exc:
        log.warning("Browser did not close cleanly: %s", exc.__class__.__name__)


# --------------------------------------------------------------------------
# Screenshots
# --------------------------------------------------------------------------
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-") or "shot"


def take_screenshot(driver: WebDriver, name: str, settings: Settings) -> Path:
    """Save a timestamped PNG and return its path."""
    settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = settings.screenshot_dir / f"{stamp}_{slugify(name)}.png"
    try:
        driver.save_screenshot(str(path))
        log.info("Screenshot -> %s", path.relative_to(settings.screenshot_dir.parent))
    except WebDriverException as exc:
        log.warning("Screenshot %r failed: %s", name, exc.__class__.__name__)
    return path


# --------------------------------------------------------------------------
# CSV helpers
# --------------------------------------------------------------------------
def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV into a list of dicts, skipping blank lines."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for row in csv.DictReader(handle) if any(v.strip() for v in row.values())]
    log.info("Loaded %d row(s) from %s", len(rows), path.name)
    return rows


def write_csv(path: Path, rows: Sequence[dict[str, Any]], headers: Iterable[str] | None = None) -> Path:
    """Write dict rows to CSV; returns the path for logging/asserting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    field_names = list(headers) if headers else list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d row(s) -> %s", len(rows), path.name)
    return path
