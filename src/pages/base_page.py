"""BasePage — every page object inherits its waiting and interaction helpers.

Rule of the project: no `time.sleep`, no implicit waits. Every read or
click goes through an explicit wait with a clear failure message.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Sequence

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Settings
from src.exceptions import ElementNotReadyError
from src.utils import assert_allowed, get_logger, take_screenshot

Locator = tuple[str, str]

# Transient failures worth one more immediate attempt: the DOM was
# re-rendered, or an animation was still covering the target.
_TRANSIENT = (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
)


class BasePage:
    """Common behaviour for all pages."""

    PATH: str = "/"
    NAME: str = "base"

    def __init__(self, driver: WebDriver, settings: Settings) -> None:
        self.driver = driver
        self.settings = settings
        self.log = get_logger(type(self).__name__)

    # -- navigation --------------------------------------------------------
    @property
    def url(self) -> str:
        return f"{self.settings.base_url.rstrip('/')}{self.PATH}"

    def open(self) -> "BasePage":
        """Navigate to this page and wait until it is really the page on screen."""
        assert_allowed(self.url)
        self.log.info("Opening %s", self.url)
        self.navigate(lambda: self.driver.get(self.url), f"navigation to {self.url}")
        return self

    def navigate(
        self,
        action: Callable[[], None],
        description: str = "navigation",
        verify_page: bool = True,
    ) -> None:
        """Run an action that loads a new page, then wait for that page.

        `driver.get()` and `element.click()` can both return while the old
        document is still on screen — most visibly when navigating to the
        URL the browser is already on. Anything typed or clicked in that
        window is silently thrown away when the new document commits.
        Waiting for the old <html> to go stale removes the race.

        Pass verify_page=False when the action lands on a *different* page
        than this object represents (e.g. submitting a login form).
        """
        old_root = self._document_root()
        action()
        if old_root is not None:
            self._until(
                EC.staleness_of(old_root),
                f"{description} never replaced the previous page",
            )
        self.wait_document_complete()
        if verify_page:
            self.wait_until_loaded()

    def _document_root(self):
        """The current <html> element, or None if there is no document yet."""
        try:
            return self.driver.find_element(By.TAG_NAME, "html")
        except (NoSuchElementException, WebDriverException):
            return None

    def wait_document_complete(self) -> None:
        """Wait for the load event — i.e. page scripts have run and bound."""
        self._until(
            lambda drv: drv.execute_script("return document.readyState") == "complete",
            "document never reached readyState 'complete'",
        )

    def wait_until_loaded(self) -> None:
        """Hook: override with a locator that proves this page rendered."""

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    # -- waits -------------------------------------------------------------
    def wait(self, timeout: float | None = None) -> WebDriverWait:
        return WebDriverWait(
            self.driver,
            timeout if timeout is not None else self.settings.timeout,
            poll_frequency=self.settings.poll,
            ignored_exceptions=(StaleElementReferenceException,),
        )

    def _until(self, condition, description: str, timeout: float | None = None):
        try:
            return self.wait(timeout).until(condition)
        except TimeoutException as exc:
            waited = timeout if timeout is not None else self.settings.timeout
            raise ElementNotReadyError(
                f"{description} after {waited:g}s on {self.current_url}"
            ) from exc

    def visible(self, locator: Locator, timeout: float | None = None) -> WebElement:
        return self._until(
            EC.visibility_of_element_located(locator),
            f"{locator} never became visible",
            timeout,
        )

    def present(self, locator: Locator, timeout: float | None = None) -> WebElement:
        return self._until(
            EC.presence_of_element_located(locator),
            f"{locator} never appeared in the DOM",
            timeout,
        )

    def clickable(self, locator: Locator, timeout: float | None = None) -> WebElement:
        return self._until(
            EC.element_to_be_clickable(locator),
            f"{locator} never became clickable",
            timeout,
        )

    def all_visible(self, locator: Locator, timeout: float | None = None) -> list[WebElement]:
        return self._until(
            EC.visibility_of_all_elements_located(locator),
            f"no visible elements matched {locator}",
            timeout,
        )

    def wait_gone(self, locator: Locator, timeout: float | None = None) -> bool:
        return self._until(
            EC.invisibility_of_element_located(locator),
            f"{locator} was still visible",
            timeout,
        )

    def wait_enabled(self, locator: Locator, timeout: float | None = None) -> WebElement:
        """Wait for an element that exists but starts out disabled."""
        self._until(
            lambda drv: drv.find_element(*locator).is_enabled(),
            f"{locator} never became enabled",
            timeout,
        )
        return self.driver.find_element(*locator)

    def is_present(self, locator: Locator, timeout: float = 1.0) -> bool:
        """Cheap existence check — never raises, used for branching."""
        try:
            self.wait(timeout).until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    # -- interactions ------------------------------------------------------
    def click(self, locator: Locator, timeout: float | None = None) -> None:
        """Click with one immediate retry for stale/intercepted elements."""
        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                element = self.clickable(locator, timeout)
                self.scroll_into_view(element)
                element.click()
                self.log.debug("Clicked %s", locator)
                return
            except _TRANSIENT as exc:
                last_error = exc
                self.log.debug(
                    "Click on %s hit %s (attempt %d) — retrying",
                    locator,
                    exc.__class__.__name__,
                    attempt,
                )
                time.sleep(self.settings.poll)
        raise ElementNotReadyError(
            f"Could not click {locator} on {self.current_url}: {last_error}"
        ) from last_error

    def fill(self, locator: Locator, value: str, timeout: float | None = None) -> None:
        """Clear a field and type into it."""
        element = self.visible(locator, timeout)
        element.clear()
        element.send_keys(value)
        self.log.debug("Filled %s", locator)

    def text_of(self, locator: Locator, timeout: float | None = None) -> str:
        return self.visible(locator, timeout).text.strip()

    def scroll_into_view(self, element: WebElement) -> None:
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
            element,
        )

    # -- misc --------------------------------------------------------------
    def screenshot(self, name: str | None = None) -> Path:
        return take_screenshot(self.driver, name or self.NAME, self.settings)

    def texts(self, elements: Sequence[WebElement]) -> list[str]:
        return [element.text.strip() for element in elements]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} url={self.url!r}>"
