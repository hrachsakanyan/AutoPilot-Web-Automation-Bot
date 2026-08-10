"""Offline unit tests — no browser needed, so these run anywhere."""

from __future__ import annotations

import pytest

from src.config import Settings
from src.exceptions import UnsafeTargetError
from src.utils import assert_allowed, read_csv, retry, slugify, write_csv


class TestAllowList:
    def test_permitted_host_passes(self):
        url = "https://the-internet.herokuapp.com/login"
        assert assert_allowed(url) == url

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/login",
            "https://mail.google.com",
            "https://the-internet.herokuapp.com.evil.test/login",
        ],
    )
    def test_other_hosts_are_refused(self, url):
        with pytest.raises(UnsafeTargetError):
            assert_allowed(url)


class TestRetry:
    def test_returns_on_first_success(self):
        calls = []

        @retry(attempts=3, delay=0, exceptions=(ValueError,))
        def works():
            calls.append(1)
            return "ok"

        assert works() == "ok"
        assert len(calls) == 1

    def test_retries_then_succeeds(self):
        calls = []

        @retry(attempts=3, delay=0, exceptions=(ValueError,))
        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("not yet")
            return "ok"

        assert flaky() == "ok"
        assert len(calls) == 3

    def test_reraises_after_last_attempt(self):
        calls = []

        @retry(attempts=2, delay=0, exceptions=(ValueError,))
        def always_fails():
            calls.append(1)
            raise ValueError("nope")

        with pytest.raises(ValueError, match="nope"):
            always_fails()
        assert len(calls) == 2

    def test_unlisted_exception_is_not_retried(self):
        calls = []

        @retry(attempts=3, delay=0, exceptions=(ValueError,))
        def wrong_error():
            calls.append(1)
            raise KeyError("different")

        with pytest.raises(KeyError):
            wrong_error()
        assert len(calls) == 1


class TestSettings:
    def test_rejects_unknown_browser(self):
        with pytest.raises(ValueError, match="Unsupported browser"):
            Settings(browser="netscape")

    def test_attempts_includes_first_try(self):
        assert Settings(retries=2).attempts == 3


class TestCsv:
    def test_round_trip(self, tmp_path):
        rows = [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
        path = write_csv(tmp_path / "out.csv", rows)
        assert read_csv(path) == rows

    def test_blank_lines_are_skipped(self, tmp_path):
        path = tmp_path / "in.csv"
        path.write_text("a,b\n1,2\n,\n3,4\n", encoding="utf-8")
        assert len(read_csv(path)) == 2


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Login Success", "login-success"), ("  A/B  ", "a-b"), ("!!!", "shot")],
)
def test_slugify(raw, expected):
    assert slugify(raw) == expected
