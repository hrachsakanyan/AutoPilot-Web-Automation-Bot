<div align="center">

# 🤖 AutoPilot

### Web Automation Bot 

**A production-style Selenium automation project built for learning real-world browser automation.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge\&logo=python\&logoColor=white)](#)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-43B02A?style=for-the-badge\&logo=selenium\&logoColor=white)](#)
[![Pytest](https://img.shields.io/badge/Pytest-Tested-0A9EDC?style=for-the-badge\&logo=pytest\&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-Educational-lightgrey?style=for-the-badge)](#)

<br>

> **Automate smarter. Wait explicitly. Fail safely.**

<br>

</div>

---

## 🧭 Overview

**AutoPilot** is an educational Selenium project that drives a **public browser-automation practice site** end to end.

It demonstrates how to build reliable browser automation using:

* 🧩 **Page Object Model**
* ⏳ **Explicit waits**
* 🔄 **Retry & backoff logic**
* 🛡️ **Target allow-list security**
* 📸 **Automatic screenshots**
* 📊 **CSV data extraction**
* 🧪 **Pytest browser & unit tests**
* 🧹 **Clean browser shutdown**

The goal isn't simply to make Selenium click buttons.

The goal is to understand **why browser automation becomes flaky** and how to design around those problems.

---

## ⚡ What AutoPilot Can Do

<table>
<tr>
<td width="33%" align="center">

### 🔐 Login Flow

Data-driven authentication testing with both valid and invalid credentials.

</td>
<td width="33%" align="center">

### ⚙️ Dynamic Forms

Handles dynamically changing elements using explicit waits.

</td>
<td width="33%" align="center">

### 📊 Table Extraction

Sorts a table and exports its contents directly to CSV.

</td>
</tr>
</table>

---

## 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │      CLI / main     │
                    │      src/main.py    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        ┌──────────┐     ┌──────────┐     ┌──────────┐
        │  Login   │     │   Form   │     │  Table   │
        │   Flow   │     │   Flow   │     │   Flow   │
        └────┬─────┘     └────┬─────┘     └────┬─────┘
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                    ┌─────────────────────┐
                    │     Page Objects    │
                    │      src/pages/     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Selenium WebDriver│
                    └──────────┬──────────┘
                               │
                               ▼
                    🌐 Practice Sandbox
```

---

## ✨ Key Features

| Feature                       | Description                                                       |
| :---------------------------- | :---------------------------------------------------------------- |
| 🧩 **Page Object Model**      | Locators and page interactions stay inside dedicated page classes |
| ⏳ **Explicit Waits**          | No `time.sleep()` in the automation path                          |
| 🔄 **Retry Logic**            | Exponential backoff around the complete run                       |
| 🩹 **Self-Healing Click**     | Recovers from stale/intercepted elements                          |
| 📸 **Screenshots**            | Captured on successful checkpoints and failures                   |
| 🛡️ **Allow-List Guard**      | Blocks navigation to unauthorized hosts                           |
| 🧪 **Automated Tests**        | Unit + real-browser Selenium tests                                |
| 🌐 **Browser Auto-Selection** | Detects an installed browser with a compatible driver             |
| 🧹 **Clean Shutdown**         | Browser closes inside `finally`, including interruptions          |
| 📄 **CSV Support**            | Data-driven login cases and table extraction                      |

---

## 🔐 Safety First

AutoPilot intentionally restricts navigation to approved hosts:

```python
ALLOWED_HOSTS = frozenset({
    "the-internet.herokuapp.com",
    "localhost",
    "127.0.0.1"
})
```

Every navigation passes through:

```text
assert_allowed()
       │
       ▼
   Is host allowed?
      /      \
    YES       NO
     │         │
     ▼         ▼
 Navigate   UnsafeTargetError
```

This makes the safety policy part of the **implementation**, not just documentation.

> ⚠️ **Use AutoPilot only against systems you own or sites that explicitly permit automation.**

Never use it to:

* bypass CAPTCHAs
* bypass rate limits
* access private accounts
* automate unauthorized targets
* circumvent Terms of Service

---

## 📁 Project Structure

```text
autopilot/
│
├── 📂 src/
│   ├── main.py
│   ├── config.py
│   ├── utils.py
│   ├── exceptions.py
│   │
│   └── 📂 pages/
│       ├── base_page.py
│       ├── login_page.py
│       ├── secure_area_page.py
│       ├── dynamic_controls_page.py
│       └── tables_page.py
│
├── 📂 tests/
│   └── 24 automated tests
│
├── 📂 data/
│   └── users.csv
│
├── 📂 screenshots/
│   └── *.png
│
├── 📂 output/
│   ├── table_data.csv
│   └── login_results.csv
│
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## 🔄 Automation Flows 

### 🔐 Login

```text
users.csv
    │
    ▼
Read test case
    │
    ▼
Open login page
    │
    ▼
Enter credentials
    │
    ▼
Submit
   / \
  /   \
 ✓     ✗
 │     │
 ▼     ▼
Success Failure
 │     │
 └──┬──┘
    ▼
Screenshot
    │
    ▼
Logout
```

### ⚙️ Dynamic Controls

```text
Open page
    │
    ▼
Remove checkbox
    │
    ▼
Wait for actual end state
    │
    ▼
Checkbox disappears
    │
    ▼
Enable input
    │
    ▼
Wait until input.is_enabled()
```

### 📊 Table Extraction

```text
Open table
    │
    ▼
Click "Last Name"
    │
    ▼
Wait for sorted state
    │
    ▼
Extract rows
    │
    ▼
Convert → CSV
    │
    ▼
output/table_data.csv
```

---

## 🧠 What I Practised

This project was built to understand the parts of Selenium that tend to cause **real-world flakiness**.

### Selenium

* Locators
* `WebDriver`
* `WebElement`
* Explicit waits
* `expected_conditions`
* Browser lifecycle

### Software Design

* Page Object Model
* Separation of concerns
* Reusable utilities
* Configuration management
* Custom exceptions

### Reliability

* Retry strategies
* Exponential backoff
* Stale element recovery
* Failure screenshots
* Deterministic waiting

### Testing

* `pytest`
* Unit tests
* Browser integration tests
* Offline test execution
* Test markers

---

## 🐛 Real Problems I Solved

### 1. Waiting for the Wrong Thing 

The dynamic-controls page displays a spinner while enabling the input.

The obvious implementation was:

```text
wait until spinner disappears
```

But the spinner never actually disappears.

The correct approach was:

```text
Don't wait for the decoration.

Wait for the state you actually need.
                ↓
        input.is_enabled()
```

---

### 2. The Old Page Was Still on Screen

Navigation could return before the previous document was completely replaced.

That created a subtle race:

```text
driver.get()
     │
     ▼
old document still rendered
     │
     ▼
click / type
     │
     ▼
new document commits
     │
     ▼
interaction silently disappears
```

`BasePage.navigate()` solves this by waiting for the previous `<html>` element to become stale before interacting with the new page.

---

## 🧪 Testing

```bash
# Run everything
pytest

# Fast offline unit tests
pytest -m "not web"

# Watch browser tests
pytest --headed
```

**24 tests**

* 15 unit tests
* 9 browser tests

Coverage includes:

* Allow-list security
* Retry decorator
* CSV round-trips
* Configuration validation
* Valid login
* Invalid password
* Unknown user
* Logout
* Dynamic controls
* Table sorting
* Table extraction

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone <your-repo-url>
cd autopilot
```

### 2. Create virtual environment

```bash
python -m venv .venv
```

### 3. Activate

**Windows**

```bash
.venv\Scripts\activate
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run

```bash
python -m src.main
```

---

## 🎛️ CLI

```text
--flow       login | form | table | all
--browser    auto | chrome | edge | firefox
--headless   Run without a visible browser
--timeout    Explicit wait timeout
--retries    Number of retry attempts
--users      Path to login CSV
```

Examples:

```bash
# Run everything
python -m src.main

# Run table flow headlessly
python -m src.main --flow table --headless

# Use Edge
python -m src.main --browser edge

# Increase timeout and retries
python -m src.main --timeout 20 --retries 3

# Custom login cases
python -m src.main --flow login --users data/users.csv
```

---

## 📸 Screenshots

AutoPilot captures timestamped screenshots during important checkpoints:

| Screenshot                        | Purpose                    |
| :-------------------------------- | :------------------------- |
| `*_login-1-success.png`           | Successful authentication  |
| `*_login-2-failure.png`           | Rejected credentials       |
| `*_dynamic-controls-before.png`   | Initial form state         |
| `*_dynamic-controls-after.png`    | Final form state           |
| `*_table-sorted-by-last-name.png` | Sorted table               |
| `*_FAILED-<test>.png`             | Automatic failure evidence |

---

## 📤 Generated Output

### Login Results

```csv
case,username,expected,outcome,matched,message
1,tomsmith,success,success,yes,...
2,tomsmith,failure,failure,yes,...
3,ghost,failure,failure,yes,...
```

### Table Data

```csv
Last Name,First Name,Email,Due,Web Site,Action
Bach,Frank,fbach@yahoo.com,$51.00,http://www.frank.com,edit delete
Conway,Tim,tconway@earthlink.net,$50.00,http://www.timconway.com,edit delete
Doe,Jason,jdoe@hotmail.com,$100.00,http://www.jdoe.com,edit delete
Smith,John,jsmith@gmail.com,$50.00,http://www.jsmith.com,edit delete
```

---

## ⚠️ Known Issue

Chromium-based browsers can occasionally experience problems when the browser and driver patch versions don't match.

AutoPilot therefore supports:

```text
--browser auto
```

The automatic selection attempts to use an installed browser with a compatible driver and skips problematic combinations.

You can also force a browser:

```bash
python -m src.main --browser chrome
```

---

<div align="center">

## 🤖 AutoPilot

**Reliable browser automation starts with reliable waits.**

Built with 🐍 Python + Selenium

</div>
