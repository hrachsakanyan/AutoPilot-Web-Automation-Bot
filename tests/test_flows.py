"""Browser tests against the sandbox site.

Marked `web` because they need Chrome and network access:
    pytest -m "not web"   # unit tests only
"""

from __future__ import annotations

import pytest

from src.config import DEMO_PASSWORD, DEMO_USERNAME
from src.exceptions import LoginFailedError
from src.pages import DynamicControlsPage, LoginPage, TablesPage

pytestmark = pytest.mark.web


class TestLogin:
    def test_valid_credentials_reach_secure_area(self, driver, settings):
        secure_area = LoginPage(driver, settings).open().login(DEMO_USERNAME, DEMO_PASSWORD)
        assert "Secure Area" in secure_area.heading()
        assert secure_area.current_url.endswith("/secure")
        secure_area.logout()

    def test_invalid_password_raises_with_site_message(self, driver, settings):
        page = LoginPage(driver, settings).open()
        with pytest.raises(LoginFailedError, match="password is invalid"):
            page.login(DEMO_USERNAME, "definitely-wrong")

    def test_unknown_user_raises(self, driver, settings):
        page = LoginPage(driver, settings).open()
        with pytest.raises(LoginFailedError, match="username is invalid"):
            page.login("ghost", DEMO_PASSWORD)

    def test_logout_returns_to_login_form(self, driver, settings):
        secure_area = LoginPage(driver, settings).open().login(DEMO_USERNAME, DEMO_PASSWORD)
        secure_area.logout()
        assert driver.current_url.endswith("/login")


class TestDynamicControls:
    def test_checkbox_is_removed_after_wait(self, driver, settings):
        page = DynamicControlsPage(driver, settings).open()
        message = page.remove_checkbox()
        assert "gone" in message.lower()
        assert not page.is_present(page.CHECKBOX, timeout=0.5)

    def test_input_becomes_enabled_and_accepts_text(self, driver, settings):
        page = DynamicControlsPage(driver, settings).open()
        assert not page.is_input_enabled()

        message = page.enable_input()
        assert page.is_input_enabled()
        assert message == "" or "enabled" in message.lower()
        assert page.type_into_input("hello") == "hello"

    def test_both_controls_in_one_page_load(self, driver, settings):
        """The flow main.py runs: both controls, same page load."""
        result = DynamicControlsPage(driver, settings).open().run_flow("AutoPilot")
        assert result.checkbox_removed
        assert result.input_enabled
        assert result.typed_text == "AutoPilot"


class TestTables:
    def test_extracts_expected_shape(self, driver, settings):
        page = TablesPage(driver, settings).open()
        rows = page.rows()
        assert len(rows) == 4
        assert "Last Name" in page.headers()
        assert all(row["Email"].count("@") == 1 for row in rows)

    def test_sorting_orders_the_column(self, driver, settings):
        page = TablesPage(driver, settings).open()
        page.sort_by("Last Name")
        last_names = page.column("Last Name")
        assert last_names == sorted(last_names)
