# Batch Lecture Summary Creator

### 1\. Prerequisites

  - Python 3.7+
  - Google Chrome
  - [ChromeDriver](https://googlechromelabs.github.io/chrome-for-testing/) that matches your Chrome version.

### 2\. Installation

Clone this repository and install the required Python packages:

```bash
pip install selenium pyperclip
```

### 3\. Configuration

**Create `assignments.json`**

Create a file named `assignments.json` to define your assignments. See the format below.

**(Optional) Set Credentials**

For convenience, set the following environment variables. If they are not set, the script will prompt you for input.

```bash
export GS_EMAIL="your_email@example.com"
export GS_PASSWORD="your_password"
export GS_COURSE_URL="https://www.gradescope.com/courses/123456"
```

### `assignments.json` Format

This file should contain a JSON list of assignment objects.

  - **Required:** `name`, `release_date`, `due_date`, `total_points`.
  - **Optional:** `late_due_date`, `enforce_time_limit`, `time_limit`, `group_submission`, `group_size`, `anonymous_grading`, etc.
  - **Date Format:** `'YYYY-MM-DD HH:MM'` (24-hour clock).

### Example `assignments.json`

```json
[
  {
    "name": "Homework 1: Introduction",
    "release_date": "2025-09-01 09:00",
    "due_date": "2025-09-08 23:59",
    "total_points": 100,
    "late_due_date": "2025-09-10 23:59"
  },
  {
    "name": "Quiz 1",
    "release_date": "2025-09-10 10:00",
    "due_date": "2025-09-10 10:50",
    "total_points": 20,
    "enforce_time_limit": true,
    "time_limit": 50,
    "anonymous_grading": true
  },
  {
    "name": "Lab 1: Group Project",
    "release_date": "2025-09-12 09:00",
    "due_date": "2025-09-19 17:00",
    "total_points": 50,
    "group_submission": true,
    "group_size": 3
  }
]
```

### Usage

Run the script with your `assignments.json` file in the same directory:

```bash
python LS_batch_creator.py
```

**Disclaimer:** This tool relies on web scraping. If Gradescope's website structure changes, the script may need updates. Use at your own risk.
