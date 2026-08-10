"""Page object for /dynamic_controls — the explicit-wait showcase.

Both controls on this page finish their work ~2s after the click, behind
a spinner. Any `time.sleep`-based script is either slow or flaky here;
waiting on the actual end state is neither.
"""

from __future__ import annotations

from dataclasses import dataclass

from selenium.webdriver.common.by import By

from src.pages.base_page import BasePage, Locator


@dataclass(slots=True)
class DynamicControlsResult:
    """What the flow observed, so main.py can report it without re-querying."""

    checkbox_removed: bool
    checkbox_message: str
    input_enabled: bool
    input_message: str
    typed_text: str


class DynamicControlsPage(BasePage):
    PATH = "/dynamic_controls"
    NAME = "dynamic-controls"

    # -- checkbox half of the page --
    CHECKBOX: Locator = (By.CSS_SELECTOR, "#checkbox input[type='checkbox']")
    CHECKBOX_BUTTON: Locator = (By.CSS_SELECTOR, "#checkbox-example button")
    # The spinners are here for completeness; see the note on the flows below
    # for why nothing waits on them.
    CHECKBOX_LOADING: Locator = (By.CSS_SELECTOR, "#checkbox-example #loading")
    CHECKBOX_MESSAGE: Locator = (By.CSS_SELECTOR, "#checkbox-example #message")

    # -- text input half of the page --
    TEXT_INPUT: Locator = (By.CSS_SELECTOR, "#input-example input[type='text']")
    INPUT_BUTTON: Locator = (By.CSS_SELECTOR, "#input-example button")
    INPUT_LOADING: Locator = (By.CSS_SELECTOR, "#input-example #loading")
    INPUT_MESSAGE: Locator = (By.CSS_SELECTOR, "#input-example #message")

    def wait_until_loaded(self) -> None:
        self.visible(self.CHECKBOX_BUTTON)
        self.visible(self.INPUT_BUTTON)

    # -- flows -------------------------------------------------------------
    # Both controls take ~2-3s behind a spinner. Wait on the *end state*, not
    # on the spinner: this page's input spinner is never hidden again once
    # shown, so "wait for the spinner to go away" would hang forever even
    # though the control is ready.
    def remove_checkbox(self) -> str:
        """Click 'Remove' and wait for the checkbox to actually disappear."""
        self.log.info("Removing the checkbox")
        self.click(self.CHECKBOX_BUTTON)
        self.wait_gone(self.CHECKBOX, timeout=self.settings.timeout * 2)
        message = self.text_of(self.CHECKBOX_MESSAGE)
        self.log.info("Checkbox gone — site says %r", message)
        return message

    def enable_input(self) -> str:
        """Click 'Enable' and wait until the field is genuinely editable."""
        self.log.info("Enabling the text input")
        self.click(self.INPUT_BUTTON)
        self.wait_enabled(self.TEXT_INPUT, timeout=self.settings.timeout * 2)
        message = self.message_for_input()
        self.log.info("Input enabled — site says %r", message)
        return message

    def message_for_input(self) -> str:
        """The 'It's enabled!' banner, or '' if the site did not render one."""
        if not self.is_present(self.INPUT_MESSAGE, timeout=1.0):
            return ""
        return self.present(self.INPUT_MESSAGE).text.strip()

    def type_into_input(self, text: str) -> str:
        """Type into the (now enabled) field and read the value back."""
        self.fill(self.TEXT_INPUT, text)
        return self.visible(self.TEXT_INPUT).get_attribute("value") or ""

    def is_input_enabled(self) -> bool:
        return self.present(self.TEXT_INPUT).is_enabled()

    def run_flow(self, text: str = "AutoPilot was here") -> DynamicControlsResult:
        """The full demo: remove the checkbox, enable the input, type."""
        checkbox_message = self.remove_checkbox()
        checkbox_removed = not self.is_present(self.CHECKBOX, timeout=0.5)

        input_message = self.enable_input()
        typed = self.type_into_input(text)

        return DynamicControlsResult(
            checkbox_removed=checkbox_removed,
            checkbox_message=checkbox_message,
            input_enabled=self.is_input_enabled(),
            input_message=input_message,
            typed_text=typed,
        )
