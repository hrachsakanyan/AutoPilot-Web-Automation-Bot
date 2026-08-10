# AutoPilot — Web Automation Bot 🤖

An educational Selenium project that drives a **public practice site** end to end:
it logs into a sandbox, works through a dynamically-loading form, extracts a data
table to CSV, takes screenshots along the way, and always shuts the browser down
cleanly.

Built to practise the parts of browser automation that actually break in real
life: **explicit waits, page objects, retries, and error handling**.

---

## ⚠️ Legal & ethical use

This project automates **only** [the-internet.herokuapp.com](https://the-internet.herokuapp.com),
a playground published by Sauce Labs specifically for automation practice.

- ❌ Never point this at real accounts, private data, or anyone else's site.
- ❌ Never use it to solve CAPTCHAs, bypass rate limits, or work around a site's Terms of Service.
- ✅ Only automate sites that explicitly permit it — practice sandboxes, demos, or systems you own.

This is enforced in code, not just in the docs. Every navigation goes through
`assert_allowed()` in [src/utils.py](src/utils.py), which raises `UnsafeTargetError`
for any host outside the allow-list in [src/config.py](src/config.py):

```python
ALLOWED_HOSTS = frozenset({"the-internet.herokuapp.com", "localhost", "127.0.0.1"})
```

The login credentials used here (`tomsmith` / `SuperSecretPassword!`) are printed
on the sandbox's own login page — they are demo values, not a real account.

---

## Features

| Flow | What it does |
| --- | --- |
| `login` | Data-driven logins from a CSV (valid **and** invalid cases), asserts each result against `expect`, screenshots both outcomes, logs out |
| `form` | Removes a checkbox and enables a disabled input on a page where each action takes ~3s behind a spinner — pure explicit-wait territory |
| `table` | Sorts a data table by clicking a column header, extracts every row, writes `output/table_data.csv` |

Under the hood:

- **Page Object Model** — one class per page, locators kept out of the flow code
- **Explicit waits everywhere** — not a single `time.sleep()` in the automation path
- **Headless mode** — `--headless`
- **Data-driven runs** — [data/users.csv](data/users.csv)
- **Retry logic** — exponential backoff around the whole run, plus a self-healing
  click for stale/intercepted elements
- **Screenshots** — timestamped, on success and automatically on failure
- **Clean shutdown** — the browser is closed in a `finally` block, even on Ctrl-C
- **Browser auto-selection** — picks an installed browser whose driver version
  actually matches it (see [Known issue](#known-issue-mismatched-chromedriver))

---

## Project structure

```
autopilot/
├── src/
│   ├── main.py                  # CLI + the three flows
│   ├── config.py                # settings, paths, host allow-list
│   ├── utils.py                 # driver factory, logging, retries, CSV, screenshots
│   ├── exceptions.py            # AutoPilotError and friends
│   └── pages/                   # page objects
│       ├── base_page.py         # waits + interactions every page inherits
│       ├── login_page.py
│       ├── secure_area_page.py
│       ├── dynamic_controls_page.py
│       └── tables_page.py
├── tests/                       # pytest: 15 unit + 9 browser tests
├── data/users.csv               # login cases for the data-driven flow
├── screenshots/                 # PNG output (git-ignored)
├── output/                      # CSV output (git-ignored)
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## Setup

Requires **Python 3.10+** and Chrome, Edge, or Firefox.

```bash
git clone <your-repo-url>
cd autopilot

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

**No manual driver download needed.** Selenium 4.6+ ships Selenium Manager, which
fetches the matching driver automatically; `webdriver-manager` is wired in as a
fallback if that ever fails.

---

## Usage

```bash
# everything, visible browser
python -m src.main

# one flow, headless
python -m src.main --flow table --headless

# pick a browser explicitly
python -m src.main --browser edge

# more patience on a slow connection, more retries
python -m src.main --timeout 20 --retries 3

# your own login cases
python -m src.main --flow login --users data/users.csv
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--flow` | `all` | `login`, `form`, `table` or `all` |
| `--browser` | `auto` | `auto`, `chrome`, `edge`, `firefox` |
| `--headless` | off | run without a visible window |
| `--timeout` | `10` | explicit-wait budget in seconds |
| `--retries` | `2` | extra attempts before giving up |
| `--users` | `data/users.csv` | CSV of login cases |

### Sample output

```
19:06:23 | INFO | autopilot.LoginPage    | Logging in as 'tomsmith'
19:06:23 | INFO | autopilot.LoginPage    | Login succeeded
19:06:27 | INFO | autopilot.main         | Case 2: got failure, expected failure -> OK
19:06:33 | INFO | autopilot.DynamicCon.. | Checkbox gone — site says "It's gone!"
19:06:38 | INFO | autopilot.DynamicCon.. | Input enabled — site says "It's enabled!"
19:06:43 | INFO | autopilot.utils        | Wrote 4 row(s) -> table_data.csv
19:06:46 | INFO | autopilot.utils        | Browser closed cleanly
```

`output/table_data.csv`:

```csv
Last Name,First Name,Email,Due,Web Site,Action
Bach,Frank,fbach@yahoo.com,$51.00,http://www.frank.com,edit delete
Conway,Tim,tconway@earthlink.net,$50.00,http://www.timconway.com,edit delete
Doe,Jason,jdoe@hotmail.com,$100.00,http://www.jdoe.com,edit delete
Smith,John,jsmith@gmail.com,$50.00,http://www.jsmith.com,edit delete
```

`output/login_results.csv`:

```csv
case,username,expected,outcome,matched,message
1,tomsmith,success,success,yes,Welcome to the Secure Area. When you are done click logout below.
2,tomsmith,failure,failure,yes,Your password is invalid!
3,ghost,failure,failure,yes,Your username is invalid!
```

---

## Screenshots

Each run drops timestamped PNGs in `screenshots/`:

| File | When |
| --- | --- |
| `*_login-1-success.png` | after reaching the secure area |
| `*_login-2-failure.png` | the rejected-credentials banner |
| `*_dynamic-controls-before/after.png` | before and after the waits |
| `*_table-sorted-by-last-name.png` | the sorted table that was extracted |
| `*_FAILED-<test name>.png` | automatically, whenever a browser test fails |

---

## Tests

```bash
pytest                 # everything (needs a browser + network)
pytest -m "not web"    # unit tests only — fast, offline
pytest --headed        # watch the browser tests run
```

24 tests: the allow-list guard, the retry decorator, CSV round-trips and settings
validation offline; login (valid, wrong password, unknown user, logout), dynamic
controls, and table extraction/sorting in a real browser.

---

## Two real bugs this project ran into

Worth writing down, because both are the kind of thing that makes automation
"randomly flaky" until you find them.

**1. Waiting on the wrong thing.** The dynamic-controls page shows a spinner while
enabling its text field, so the obvious wait is "spinner disappears". That wait
hangs forever — the site never hides that particular spinner, it just enables the
input underneath it. The fix is the rule this whole project follows: **wait for
the end state you actually care about** (`input.is_enabled()`), never for a
decoration that happens to correlate with it.

**2. The old page is still on screen.** `driver.get()` and `element.click()` can
return while the previous document is still rendered — most visibly when you
navigate to the URL the browser is already on. Anything typed or clicked in that
gap is silently discarded when the new document commits. `BasePage.navigate()`
closes the race by waiting for the old `<html>` element to go stale before
touching the new page.

---

## Known issue: mismatched chromedriver

A Chromium driver whose version does not match its browser **exactly** can start
up perfectly and then quietly stop delivering clicks and keystrokes after the
first page change — no exception, elements just never react.

Seen on the machine this was built on:

```
Chrome  150.0.7871.188   +   chromedriver 150.0.7871.124   ->  broken input
Edge    151.0.4129.59    +   msedgedriver 151.0.4129.59    ->  fine
```

This happens when Chrome auto-updates to a patch release before a matching
chromedriver is published. That is why `--browser auto` is the default: it starts
the first installed browser whose driver version matches it exactly, logs a
warning about any it skips, and only falls back if nothing matches. Force a
specific browser with `--browser chrome` if you want the raw behaviour.

---

## What I practised

- Selenium locators, explicit waits, and the `expected_conditions` vocabulary
- Structuring automation with the Page Object Model instead of one long script
- Telling "the page is slow" apart from "the page is broken" in error handling
- Retries with backoff, and why a self-healing click is worth having
- Building a safety guard into the code so the tool can't be aimed somewhere it shouldn't be
