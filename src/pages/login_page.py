"""Page object for https://the-internet.herokuapp.com/login (sandbox only)."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from src.exceptions import LoginFailedError
from src.pages.base_page import BasePage, Locator
from src.pages.secure_area_page import SecureAreaPage


class LoginPage(BasePage):
    PATH = "/login"
    NAME = "login"

    USERNAME: Locator = (By.ID, "username")
    PASSWORD: Locator = (By.ID, "password")
    SUBMIT: Locator = (By.CSS_SELECTOR, "button[type='submit']")
    FLASH: Locator = (By.ID, "flash")

    def wait_until_loaded(self) -> None:
        self.visible(self.USERNAME)
        self.visible(self.SUBMIT)

    def login(self, username: str, password: str) -> SecureAreaPage:
        """Submit the form and return the secure-area page on success.

        Raises LoginFailedError with the site's own flash message when the
        credentials are rejected.
        """
        self.log.info("Logging in as %r", username)
        self.fill(self.USERNAME, username)
        self.fill(self.PASSWORD, password)
        # Submitting leaves this page (to /secure or back to /login with an
        # error), so wait for the new document before reading the banner.
        self.navigate(
            lambda: self.click(self.SUBMIT),
            "login submit",
            verify_page=False,
        )

        message = self.flash_message()
        if not self.is_success(message):
            raise LoginFailedError(message or "Login failed with no flash message")

        secure_area = SecureAreaPage(self.driver, self.settings)
        secure_area.wait_until_loaded()
        self.log.info("Login succeeded")
        return secure_area

    def flash_message(self) -> str:
        """The green/red banner text, with the close 'x' stripped off."""
        raw = self.text_of(self.FLASH)
        return raw.replace("×", "").strip()

    @staticmethod
    def is_success(message: str) -> bool:
        return "You logged into a secure area" in message
