### Confluence Team Calendar API Test Suite

This project provides a modular Python-based framework to automate and test event lifecycles within Confluence Team Calendars. It leverages Pydantic for data validation and the Atlassian Python API for REST communication.

---

#### Project Structure

* **`models.py`**: Defines the `CalendarEvent` Pydantic model to ensure technical accuracy of event data.
* **`confluence_calendar.py`**: The core action class containing methods for creation, modification, and intelligent series-aware deletion.
* **`constants.py`**: Stores non-sensitive configuration such as API paths and headers.
* **`run_tests.py`**: A comprehensive regression script that executes and verifies various calendar scenarios.
* **`.env`**: Stores sensitive credentials (URL, Token, and Calendar Name).

---

#### Features

* **Dynamic ID Resolution**: Automatically identifies Parent and Child calendar IDs using the display name (e.g., "Wanton Mee Stall").
* **Comprehensive Test Scenarios**: Covers standalone timed events, multi-day all-day events, and complex recurring series.
* **Smart Cleanup**: Logic to identify and wipe unique Master UIDs, preventing redundant API calls and errors during full resets.
* **Unified Deletion**: Supports `SERIES` (entire series), `SINGLE` (one instance), and `FUTURE` (instance and all following) deletion modes.

---

#### Setup and Installation

1. **Install Dependencies**:
```bash
pip install -r requirements.txt

```


(Requires: `atlassian-python-api`, `pydantic`, `python-dotenv`, `requests`).
2. **Configure Environment**:
Create a `.env` file in the root directory:
```text
CONFLUENCE_URL=http://localhost:8090
CONFLUENCE_TOKEN=your_token_here
CONFLUENCE_CAL_NAME=Wanton Mee Stall
```.


```


3. **Run the Tests**:
```bash
python run_tests.py
```.


```



---

#### Verification and Logging

The test suite provides granular logging for every lifecycle phase:

* **[ACTION]**: Logs write/edit/delete requests sent to the API.
* **[VERIFY]**: Explicitly checks the calendar state to confirm if the action was successful.
* **Logs**: All output is mirrored to `comprehensive_test.log` for troubleshooting.

---
