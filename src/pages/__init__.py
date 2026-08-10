"""Page objects — one class per page, locators kept out of the flow code."""

from src.pages.base_page import BasePage, Locator
from src.pages.dynamic_controls_page import DynamicControlsPage, DynamicControlsResult
from src.pages.login_page import LoginPage
from src.pages.secure_area_page import SecureAreaPage
from src.pages.tables_page import TablesPage

__all__ = [
    "BasePage",
    "Locator",
    "DynamicControlsPage",
    "DynamicControlsResult",
    "LoginPage",
    "SecureAreaPage",
    "TablesPage",
]
