"""Central configuration for AutoPilot.

Everything tunable lives here so the page objects stay free of magic
numbers and hard-coded paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

# --------------------------------------------------------------------------
# Target site
# --------------------------------------------------------------------------
# the-internet.herokuapp.com is published by Sauce Labs as a practice
# playground for automation. Nothing here touches a real account.
BASE_URL = "https://the-internet.herokuapp.com"

# Hard allow-list. Any navigation to a host outside this set raises
# UnsafeTargetError, so the bot cannot be pointed at a site that forbids
# automation just by changing a CLI flag.
ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "the-internet.herokuapp.com",
        "localhost",
        "127.0.0.1",
    }
)

# Public demo credentials printed on the login page itself.
DEMO_USERNAME = "tomsmith"
DEMO_PASSWORD = "SuperSecretPassword!"

# "auto" starts the first installed browser whose driver version matches the
# browser exactly — a mismatched pair silently breaks clicks and typing.
SUPPORTED_BROWSERS = ("auto", "chrome", "edge", "firefox")
BROWSER_PREFERENCE = ("chrome", "edge", "firefox")


@dataclass(slots=True)
class Settings:
    """Runtime knobs, normally built from CLI arguments in main.py."""

    base_url: str = BASE_URL
    browser: str = "auto"
    headless: bool = False
    timeout: float = 10.0            # default explicit-wait budget, seconds
    poll: float = 0.25               # WebDriverWait poll interval, seconds
    retries: int = 2                 # extra attempts for flaky flows
    retry_delay: float = 1.0
    window_size: tuple[int, int] = (1440, 900)
    screenshot_dir: Path = field(default=SCREENSHOT_DIR)
    output_dir: Path = field(default=OUTPUT_DIR)
    log_dir: Path = field(default=LOG_DIR)

    def __post_init__(self) -> None:
        self.browser = self.browser.lower()
        if self.browser not in SUPPORTED_BROWSERS:
            raise ValueError(
                f"Unsupported browser {self.browser!r}; "
                f"choose one of {', '.join(SUPPORTED_BROWSERS)}"
            )
        for directory in (self.screenshot_dir, self.output_dir, self.log_dir):
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def attempts(self) -> int:
        """Total tries = first attempt + configured retries."""
        return self.retries + 1
