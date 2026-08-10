"""Page object for /tables — the data-extraction target."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from src.pages.base_page import BasePage, Locator


class TablesPage(BasePage):
    PATH = "/tables"
    NAME = "tables"

    TABLE: Locator = (By.ID, "table1")
    HEADERS: Locator = (By.CSS_SELECTOR, "#table1 thead th")
    ROWS: Locator = (By.CSS_SELECTOR, "#table1 tbody tr")

    def wait_until_loaded(self) -> None:
        self.visible(self.TABLE)
        self.all_visible(self.ROWS)

    # -- extraction --------------------------------------------------------
    def headers(self) -> list[str]:
        return [header.text.strip() for header in self.all_visible(self.HEADERS)]

    def rows(self) -> list[dict[str, str]]:
        """Every data row as {header: cell text}.

        Re-read from the DOM on each call so it stays correct after a sort.
        """
        headers = self.headers()
        extracted: list[dict[str, str]] = []
        for row in self.all_visible(self.ROWS):
            cells = row.find_elements(By.TAG_NAME, "td")
            extracted.append(
                {
                    header: (cells[index].text.strip() if index < len(cells) else "")
                    for index, header in enumerate(headers)
                }
            )
        self.log.info("Extracted %d row(s) from #table1", len(extracted))
        return extracted

    def column(self, header: str) -> list[str]:
        return [row[header] for row in self.rows()]

    def sort_by(self, header: str) -> "TablesPage":
        """Click a column header and wait until the order actually changes."""
        before = self.column(header)
        target = next(
            (
                element
                for element in self.all_visible(self.HEADERS)
                if element.text.strip().lower() == header.lower()
            ),
            None,
        )
        if target is None:
            raise ValueError(f"No column named {header!r}; have {self.headers()}")

        self.log.info("Sorting by %r", header)
        self.scroll_into_view(target)
        target.click()
        # The site sorts client-side and instantly; wait for the observable
        # result rather than assuming the click already took effect.
        self.wait().until(
            lambda _: self.column(header) != before or before == sorted(before),
            f"column {header!r} never changed order after the click",
        )
        return self
