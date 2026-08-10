"""Page object for the post-login secure area."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from src.pages.base_page import BasePage, Locator


class SecureAreaPage(BasePage):
    PATH = "/secure"
    NAME = "secure-area"

    HEADING: Locator = (By.CSS_SELECTOR, "h2")
    SUBHEADING: Locator = (By.CSS_SELECTOR, "h4.subheader")
    LOGOUT: Locator = (By.CSS_SELECTOR, "a[href='/logout']")
    FLASH: Locator = (By.ID, "flash")

    def wait_until_loaded(self) -> None:
        self.visible(self.HEADING)
        self.visible(self.LOGOUT)

    def heading(self) -> str:
        return self.text_of(self.HEADING)

    def subheading(self) -> str:
        return self.text_of(self.SUBHEADING)

    def logout(self) -> None:
        """Log out and wait until we are actually back on /login."""
        self.log.info("Logging out")
        self.navigate(lambda: self.click(self.LOGOUT), "logout", verify_page=False)
        self.wait().until(
            lambda drv: drv.current_url.rstrip("/").endswith("/login"),
            "logout did not redirect back to /login",
        )
