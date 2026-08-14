# OpenWRT USB Scanner Web Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move LuCI to port 81 and serve a new single-page scanner web app on port 80 of the OpenWrt router at `192.168.1.1`, driving the USB-attached Canon LiDE 400 via `scanimage`.

**Architecture:** Static HTML/CSS/JS frontend + two thin Python3 CGI scripts (`scan.py`, `download.py`) under a second uhttpd listen instance, calling `scanimage` on the router. Pure logic (param validation, filename generation, path-safety checks, command building) lives in small standalone modules under `scanlib/` so it's unit-testable on a dev machine without the router or scanner attached; the CGI scripts themselves are thin glue, verified by syntax-check locally and a live smoke test on the router.

**Tech Stack:** Python 3 (stdlib only — no `cgi` module, removed in 3.13; use `urllib.parse` + manual CONTENT_LENGTH reads), uhttpd (already on router), `scanimage` (sane-backends, already installed), vanilla HTML/CSS/JS (no framework, no Node available on router).

## Global Constraints

- Router: `192.168.1.1`, SSH as `root`, key-based (no password prompt).
- Scanner device string: `pixma:04A91912_43A16F` (sane-pixma backend — NOT genesys).
- `--resolution` values: `150|300|600|1200`, default `150`.
- `--mode` UI labels: `Color` → CLI `Color`; `Grayscale` → CLI `Gray`. Default `Color`.
- `--format` UI labels: `PDF` → CLI `pdf`, file ext `.pdf`; `JPG` → CLI `jpeg`, file ext `.jpg`. Default `PDF`.
- Saved scans go to `/overlay/scans/` on the router, filename `scan_<YYYYmmdd_HHMMSS>.<ext>`.
- No authentication (LAN-trust, matches existing LuCI).
- Single page per scan only — no batch/multi-page PDF assembly.
- LuCI: `listen_http` moves from port 80 to port 81. `listen_https` (443) untouched.
- New `scanner` uhttpd instance: port 80, `script_timeout '300'` (high-res color scans run minutes).
- Python on router is `python3-light` 3.13.9 — no `cgi`/`cgitb` stdlib module available.
- Local dev machine has `python3` (3.14) but no `pytest` — use stdlib `unittest`.

---

## File Structure

```
OpenWRTScanner/
  todo.txt
  docs/superpowers/specs/2026-08-13-openwrt-scanner-design.md   (already written)
  docs/superpowers/plans/2026-08-13-openwrt-scanner-implementation.md  (this file)
  www-scanner/
    index.html
    style.css
    app.js
    cgi-bin/
      scan.py               # thin CGI: POST handler, runs a scan
      download.py            # thin CGI: GET handler, streams a saved file
      scanlib/
        __init__.py
        validation.py        # pure: validate_resolution/mode/format
        naming.py             # pure: make_filename(ext, now)
        safepath.py           # pure: is_safe_scan_filename(name)
        runner.py             # pure-ish: build_scan_command(...), run_scan(cmd, timeout, runner=subprocess.run)
  tests/
    test_validation.py
    test_naming.py
    test_safepath.py
    test_runner.py
  deploy/
    deploy.sh                # scp files to router, apply UCI changes, restart uhttpd
  README.md
```

---

### Task 1: `scanlib.validation` — resolution/mode/format validation

**Files:**
- Create: `www-scanner/cgi-bin/scanlib/__init__.py`
- Create: `www-scanner/cgi-bin/scanlib/validation.py`
- Test: `tests/test_validation.py`

**Interfaces:**
- Produces: `validate_resolution(value: str) -> int`, `validate_mode(value: str) -> str`, `validate_format(value: str) -> tuple[str, str]` (returns `(scanimage_format, file_extension)`). All three raise `ValueError` on invalid input.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_validation.py`:

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.validation import validate_resolution, validate_mode, validate_format


class TestValidateResolution(unittest.TestCase):
    def test_accepts_all_allowed_values(self):
        for value, expected in [("150", 150), ("300", 300), ("600", 600), ("1200", 1200)]:
            self.assertEqual(validate_resolution(value), expected)

    def test_rejects_unlisted_value(self):
        with self.assertRaises(ValueError):
            validate_resolution("2400")

    def test_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            validate_resolution("abc")

    def test_rejects_missing(self):
        with self.assertRaises(ValueError):
            validate_resolution("")


class TestValidateMode(unittest.TestCase):
    def test_color_maps_to_cli_color(self):
        self.assertEqual(validate_mode("Color"), "Color")

    def test_grayscale_maps_to_cli_gray(self):
        self.assertEqual(validate_mode("Grayscale"), "Gray")

    def test_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            validate_mode("Lineart")

    def test_rejects_cli_value_directly(self):
        # UI sends the label "Grayscale", not the CLI value "Gray" - reject the latter
        with self.assertRaises(ValueError):
            validate_mode("Gray")


class TestValidateFormat(unittest.TestCase):
    def test_pdf_maps_to_pdf_pdf(self):
        self.assertEqual(validate_format("PDF"), ("pdf", "pdf"))

    def test_jpg_maps_to_jpeg_jpg(self):
        self.assertEqual(validate_format("JPG"), ("jpeg", "jpg"))

    def test_rejects_unknown_format(self):
        with self.assertRaises(ValueError):
            validate_format("PNG")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_validation -v`
Expected: `ModuleNotFoundError: No module named 'scanlib'` (module doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `www-scanner/cgi-bin/scanlib/__init__.py` (empty file).

Create `www-scanner/cgi-bin/scanlib/validation.py`:

```python
"""Pure validation helpers for scan request parameters.

No I/O, no subprocess calls - safe to unit test without the router or scanner.
"""

ALLOWED_RESOLUTIONS = (150, 300, 600, 1200)

# UI label -> scanimage --mode value
ALLOWED_MODES = {
    "Color": "Color",
    "Grayscale": "Gray",
}

# UI label -> (scanimage --format value, saved file extension)
ALLOWED_FORMATS = {
    "PDF": ("pdf", "pdf"),
    "JPG": ("jpeg", "jpg"),
}


def validate_resolution(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("resolution must be an integer, got %r" % (value,))
    if parsed not in ALLOWED_RESOLUTIONS:
        raise ValueError(
            "resolution must be one of %r, got %r" % (ALLOWED_RESOLUTIONS, parsed)
        )
    return parsed


def validate_mode(value):
    try:
        return ALLOWED_MODES[value]
    except KeyError:
        raise ValueError(
            "mode must be one of %r, got %r" % (sorted(ALLOWED_MODES), value)
        )


def validate_format(value):
    try:
        return ALLOWED_FORMATS[value]
    except KeyError:
        raise ValueError(
            "format must be one of %r, got %r" % (sorted(ALLOWED_FORMATS), value)
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_validation -v`
Expected: `OK` (11 tests pass).

- [ ] **Step 5: Commit**

```bash
git add www-scanner/cgi-bin/scanlib/__init__.py www-scanner/cgi-bin/scanlib/validation.py tests/test_validation.py
git commit -m "feat: add scan param validation module"
```

---

### Task 2: `scanlib.naming` — timestamped output filenames

**Files:**
- Create: `www-scanner/cgi-bin/scanlib/naming.py`
- Test: `tests/test_naming.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `make_filename(extension: str, now: datetime.datetime) -> str`, e.g. `make_filename("pdf", datetime(2026, 8, 13, 22, 30, 45))` → `"scan_20260813_223045.pdf"`. Later tasks (safepath, scan.py) rely on this exact `scan_<YYYYmmdd_HHMMSS>.<ext>` shape.

- [ ] **Step 1: Write the failing test**

Create `tests/test_naming.py`:

```python
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.naming import make_filename


class TestMakeFilename(unittest.TestCase):
    def test_formats_timestamp_and_extension(self):
        now = datetime.datetime(2026, 8, 13, 22, 30, 45)
        self.assertEqual(make_filename("pdf", now), "scan_20260813_223045.pdf")

    def test_jpg_extension(self):
        now = datetime.datetime(2026, 1, 1, 0, 0, 0)
        self.assertEqual(make_filename("jpg", now), "scan_20260101_000000.jpg")

    def test_zero_pads_single_digit_fields(self):
        now = datetime.datetime(2026, 3, 5, 9, 7, 2)
        self.assertEqual(make_filename("pdf", now), "scan_20260305_090702.pdf")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_naming -v`
Expected: `ModuleNotFoundError: No module named 'scanlib.naming'`

- [ ] **Step 3: Write the implementation**

Create `www-scanner/cgi-bin/scanlib/naming.py`:

```python
"""Pure filename generation for saved scans."""


def make_filename(extension, now):
    """Build the on-disk filename for a scan.

    `now` is injected (a datetime.datetime) rather than read from the clock
    here, so this stays a pure function callers can unit test deterministically.
    """
    return "scan_%s.%s" % (now.strftime("%Y%m%d_%H%M%S"), extension)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_naming -v`
Expected: `OK` (3 tests pass).

- [ ] **Step 5: Commit**

```bash
git add www-scanner/cgi-bin/scanlib/naming.py tests/test_naming.py
git commit -m "feat: add scan filename generator"
```

---

### Task 3: `scanlib.safepath` — filename whitelist for downloads

**Files:**
- Create: `www-scanner/cgi-bin/scanlib/safepath.py`
- Test: `tests/test_safepath.py`

**Interfaces:**
- Consumes: the filename shape produced by `make_filename` in Task 2 (`scan_<YYYYmmdd_HHMMSS>.<ext>`).
- Produces: `is_safe_scan_filename(name: str) -> bool`. `download.py` (Task 7) calls this before touching the filesystem, so it must reject anything containing `/`, `..`, or not matching the exact `scan_` pattern.

- [ ] **Step 1: Write the failing test**

Create `tests/test_safepath.py`:

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.safepath import is_safe_scan_filename


class TestIsSafeScanFilename(unittest.TestCase):
    def test_accepts_well_formed_pdf_name(self):
        self.assertTrue(is_safe_scan_filename("scan_20260813_223045.pdf"))

    def test_accepts_well_formed_jpg_name(self):
        self.assertTrue(is_safe_scan_filename("scan_20260101_000000.jpg"))

    def test_rejects_path_traversal(self):
        self.assertFalse(is_safe_scan_filename("../../etc/passwd"))

    def test_rejects_embedded_slash(self):
        self.assertFalse(is_safe_scan_filename("scans/scan_20260813_223045.pdf"))

    def test_rejects_wrong_extension(self):
        self.assertFalse(is_safe_scan_filename("scan_20260813_223045.exe"))

    def test_rejects_missing_prefix(self):
        self.assertFalse(is_safe_scan_filename("20260813_223045.pdf"))

    def test_rejects_empty_string(self):
        self.assertFalse(is_safe_scan_filename(""))

    def test_rejects_non_digit_timestamp(self):
        self.assertFalse(is_safe_scan_filename("scan_aaaaaaaa_bbbbbb.pdf"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_safepath -v`
Expected: `ModuleNotFoundError: No module named 'scanlib.safepath'`

- [ ] **Step 3: Write the implementation**

Create `www-scanner/cgi-bin/scanlib/safepath.py`:

```python
"""Pure filename-safety check for the download endpoint.

Matches exactly the shape scanlib.naming.make_filename produces:
scan_<8 digits>_<6 digits>.<pdf|jpg>
"""

import re

_SAFE_NAME_RE = re.compile(r"^scan_\d{8}_\d{6}\.(pdf|jpg)$")


def is_safe_scan_filename(name):
    if not isinstance(name, str):
        return False
    return bool(_SAFE_NAME_RE.match(name))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_safepath -v`
Expected: `OK` (8 tests pass).

- [ ] **Step 5: Commit**

```bash
git add www-scanner/cgi-bin/scanlib/safepath.py tests/test_safepath.py
git commit -m "feat: add safe filename check for download endpoint"
```

---

### Task 4: `scanlib.runner` — build and run the scanimage command

**Files:**
- Create: `www-scanner/cgi-bin/scanlib/runner.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `validate_resolution`/`validate_mode`/`validate_format` output types from Task 1 (ints/strings), `make_filename` output from Task 2 (used by caller, not by this module directly).
- Produces: `build_scan_command(device: str, resolution: int, mode_cli: str, scan_format: str, output_path: str) -> list[str]` and `run_scan(cmd: list[str], timeout: int, runner=subprocess.run) -> subprocess.CompletedProcess`. `scan.py` (Task 6) calls both. `runner` is injectable so tests never actually invoke `scanimage`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_runner.py`:

```python
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.runner import build_scan_command, run_scan


class TestBuildScanCommand(unittest.TestCase):
    def test_builds_expected_argv(self):
        cmd = build_scan_command(
            device="pixma:04A91912_43A16F",
            resolution=150,
            mode_cli="Color",
            scan_format="pdf",
            output_path="/overlay/scans/scan_20260813_223045.pdf",
        )
        self.assertEqual(
            cmd,
            [
                "scanimage",
                "-d",
                "pixma:04A91912_43A16F",
                "--resolution",
                "150",
                "--mode",
                "Color",
                "--format=pdf",
                "-o",
                "/overlay/scans/scan_20260813_223045.pdf",
            ],
        )

    def test_grayscale_mode_passed_through_as_cli_value(self):
        cmd = build_scan_command(
            device="pixma:04A91912_43A16F",
            resolution=600,
            mode_cli="Gray",
            scan_format="jpeg",
            output_path="/overlay/scans/scan_20260813_223045.jpg",
        )
        self.assertIn("--mode", cmd)
        self.assertEqual(cmd[cmd.index("--mode") + 1], "Gray")
        self.assertIn("--format=jpeg", cmd)


class FakeCompletedProcess:
    def __init__(self, returncode, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


class TestRunScan(unittest.TestCase):
    def test_returns_runner_result_on_success(self):
        calls = []

        def fake_runner(cmd, capture_output, text, timeout):
            calls.append((cmd, capture_output, text, timeout))
            return FakeCompletedProcess(returncode=0)

        result = run_scan(["scanimage", "-d", "x"], timeout=300, runner=fake_runner)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)
        cmd, capture_output, text, timeout = calls[0]
        self.assertEqual(cmd, ["scanimage", "-d", "x"])
        self.assertTrue(capture_output)
        self.assertTrue(text)
        self.assertEqual(timeout, 300)

    def test_propagates_timeout_expired(self):
        def fake_runner(cmd, capture_output, text, timeout):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

        with self.assertRaises(subprocess.TimeoutExpired):
            run_scan(["scanimage"], timeout=5, runner=fake_runner)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_runner -v`
Expected: `ModuleNotFoundError: No module named 'scanlib.runner'`

- [ ] **Step 3: Write the implementation**

Create `www-scanner/cgi-bin/scanlib/runner.py`:

```python
"""Build and execute the scanimage command line.

build_scan_command is pure. run_scan takes an injectable `runner` callable
(defaults to subprocess.run) so tests never invoke the real scanimage binary.
"""

import subprocess


def build_scan_command(device, resolution, mode_cli, scan_format, output_path):
    return [
        "scanimage",
        "-d",
        device,
        "--resolution",
        str(resolution),
        "--mode",
        mode_cli,
        "--format=%s" % scan_format,
        "-o",
        output_path,
    ]


def run_scan(cmd, timeout, runner=subprocess.run):
    return runner(cmd, capture_output=True, text=True, timeout=timeout)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_runner -v`
Expected: `OK` (4 tests pass).

- [ ] **Step 5: Commit**

```bash
git add www-scanner/cgi-bin/scanlib/runner.py tests/test_runner.py
git commit -m "feat: add scanimage command builder and injectable runner"
```

---

### Task 5: `scan.py` CGI endpoint

**Files:**
- Create: `www-scanner/cgi-bin/scan.py`

**Interfaces:**
- Consumes: `validate_resolution`, `validate_mode`, `validate_format` (Task 1), `make_filename` (Task 2), `build_scan_command`, `run_scan` (Task 4).
- Produces: an HTTP CGI response. On success, JSON body `{"ok": true, "file": "<name>", "url": "/cgi-bin/download.py?name=<name>"}`. `app.js` (Task 8) and `download.py` (Task 6) depend on that exact JSON shape and URL pattern.

This file has no router/scanner attached locally, so it's verified by a local
syntax/import check here and by the live smoke test in Task 9 — there is no
meaningful unit test for a thin CGI entrypoint that only orchestrates
already-tested pure functions.

- [ ] **Step 1: Write the implementation**

Create `www-scanner/cgi-bin/scan.py`:

```python
#!/usr/bin/env python3
"""CGI endpoint: POST resolution/mode/format, run a scan, save it, return JSON."""

import datetime
import fcntl
import json
import os
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))

from scanlib.naming import make_filename
from scanlib.runner import build_scan_command, run_scan
from scanlib.validation import validate_format, validate_mode, validate_resolution

DEVICE = "pixma:04A91912_43A16F"
SCANS_DIR = "/overlay/scans"
LOCK_FILE = "/tmp/scan.lock"
SCAN_TIMEOUT_SECONDS = 300


def read_form_body():
    try:
        length = int(os.environ.get("CONTENT_LENGTH", "0"))
    except ValueError:
        length = 0
    raw = sys.stdin.buffer.read(length) if length > 0 else b""
    parsed = urllib.parse.parse_qs(raw.decode("utf-8", errors="replace"))
    return {key: values[0] for key, values in parsed.items()}


def respond_json(status_line, payload):
    print("Status: %s" % status_line)
    print("Content-Type: application/json")
    print()
    print(json.dumps(payload))


def main():
    form = read_form_body()

    try:
        resolution = validate_resolution(form.get("resolution", ""))
        mode_cli = validate_mode(form.get("mode", ""))
        scan_format, extension = validate_format(form.get("format", ""))
    except ValueError as exc:
        respond_json("400 Bad Request", {"ok": False, "error": str(exc)})
        return

    os.makedirs(SCANS_DIR, exist_ok=True)
    filename = make_filename(extension, datetime.datetime.now())
    output_path = os.path.join(SCANS_DIR, filename)
    cmd = build_scan_command(DEVICE, resolution, mode_cli, scan_format, output_path)

    lock_fh = open(LOCK_FILE, "w")
    try:
        try:
            fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            respond_json(
                "409 Conflict", {"ok": False, "error": "Scan already in progress."}
            )
            return

        try:
            result = run_scan(cmd, timeout=SCAN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            respond_json(
                "504 Gateway Timeout",
                {"ok": False, "error": "Scan timed out after %ss." % SCAN_TIMEOUT_SECONDS},
            )
            return

        if result.returncode != 0:
            respond_json(
                "500 Internal Server Error",
                {
                    "ok": False,
                    "error": "Scanner not found or scan failed: %s"
                    % (result.stderr or "unknown error").strip(),
                },
            )
            return

        respond_json(
            "200 OK",
            {
                "ok": True,
                "file": filename,
                "url": "/cgi-bin/download.py?name=%s" % urllib.parse.quote(filename),
            },
        )
    finally:
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        lock_fh.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Syntax-check locally**

Run: `python3 -m py_compile www-scanner/cgi-bin/scan.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add www-scanner/cgi-bin/scan.py
git commit -m "feat: add scan.py CGI endpoint"
```

---

### Task 6: `download.py` CGI endpoint

**Files:**
- Create: `www-scanner/cgi-bin/download.py`

**Interfaces:**
- Consumes: `is_safe_scan_filename` (Task 3), `SCANS_DIR` value `/overlay/scans` (same constant as Task 5 — duplicated here since CGI scripts run standalone with no shared process state).
- Produces: raw file bytes over CGI with `Content-Type: application/pdf` or `image/jpeg`, used by `app.js` (Task 8) as both the preview `src` and the download link `href`.

- [ ] **Step 1: Write the implementation**

Create `www-scanner/cgi-bin/download.py`:

```python
#!/usr/bin/env python3
"""CGI endpoint: GET ?name=<file>, stream a previously saved scan back."""

import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))

from scanlib.safepath import is_safe_scan_filename

SCANS_DIR = "/overlay/scans"

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
}


def respond_error(status_line, message):
    print("Status: %s" % status_line)
    print("Content-Type: text/plain")
    print()
    print(message)


def main():
    query = urllib.parse.parse_qs(os.environ.get("QUERY_STRING", ""))
    names = query.get("name", [])
    name = names[0] if names else ""

    if not is_safe_scan_filename(name):
        respond_error("400 Bad Request", "Invalid filename.")
        return

    path = os.path.join(SCANS_DIR, name)
    if not os.path.isfile(path):
        respond_error("404 Not Found", "No such scan.")
        return

    extension = name.rsplit(".", 1)[-1]
    content_type = CONTENT_TYPES.get(extension, "application/octet-stream")

    print("Content-Type: %s" % content_type)
    print("Content-Disposition: inline; filename=\"%s\"" % name)
    print()
    sys.stdout.flush()

    with open(path, "rb") as fh:
        sys.stdout.buffer.write(fh.read())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Syntax-check locally**

Run: `python3 -m py_compile www-scanner/cgi-bin/download.py`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add www-scanner/cgi-bin/download.py
git commit -m "feat: add download.py CGI endpoint"
```

---

### Task 7: Frontend — `index.html`, `style.css`, `app.js`

**Files:**
- Create: `www-scanner/index.html`
- Create: `www-scanner/style.css`
- Create: `www-scanner/app.js`

**Interfaces:**
- Consumes: `scan.py`'s JSON response shape `{"ok": bool, "file"?: str, "url"?: str, "error"?: str}` (Task 5), `download.py`'s URL pattern `/cgi-bin/download.py?name=<name>` (Task 6).
- Produces: the page a browser loads at `http://192.168.1.1/`.

- [ ] **Step 1: Write `www-scanner/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Scanner</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main>
    <h1>Scanner</h1>

    <form id="scan-form">
      <label>
        Resolution
        <select name="resolution" id="resolution">
          <option value="150" selected>150 dpi</option>
          <option value="300">300 dpi</option>
          <option value="600">600 dpi</option>
          <option value="1200">1200 dpi</option>
        </select>
      </label>

      <label>
        Mode
        <select name="mode" id="mode">
          <option value="Color" selected>Color</option>
          <option value="Grayscale">Grayscale</option>
        </select>
      </label>

      <label>
        Format
        <select name="format" id="format">
          <option value="PDF" selected>PDF</option>
          <option value="JPG">JPG</option>
        </select>
      </label>

      <button type="submit" id="scan-button">Scan</button>
    </form>

    <p id="status"></p>

    <div id="preview"></div>

    <p id="download-area"></p>
  </main>

  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `www-scanner/style.css`**

```css
body {
  font-family: system-ui, sans-serif;
  max-width: 40rem;
  margin: 2rem auto;
  padding: 0 1rem;
  color: #1a1a1a;
}

form {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: end;
  margin-bottom: 1.5rem;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
}

button {
  padding: 0.5rem 1.25rem;
  font-size: 1rem;
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.6;
}

#status {
  min-height: 1.5rem;
  font-weight: bold;
}

#preview img,
#preview iframe {
  max-width: 100%;
  border: 1px solid #ccc;
  margin-top: 1rem;
}

#preview iframe {
  width: 100%;
  height: 32rem;
}
```

- [ ] **Step 3: Write `www-scanner/app.js`**

```js
const form = document.getElementById("scan-form");
const scanButton = document.getElementById("scan-button");
const statusEl = document.getElementById("status");
const previewEl = document.getElementById("preview");
const downloadAreaEl = document.getElementById("download-area");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  scanButton.disabled = true;
  statusEl.textContent = "Scanning… this can take a few minutes at high resolution.";
  previewEl.innerHTML = "";
  downloadAreaEl.innerHTML = "";

  const formData = new URLSearchParams(new FormData(form));

  try {
    const response = await fetch("/cgi-bin/scan.py", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });
    const result = await response.json();

    if (!result.ok) {
      statusEl.textContent = "Error: " + result.error;
      return;
    }

    statusEl.textContent = "Scan saved: " + result.file;

    const format = form.elements["format"].value;
    if (format === "PDF") {
      previewEl.innerHTML = '<iframe src="' + result.url + '"></iframe>';
    } else {
      previewEl.innerHTML = '<img src="' + result.url + '" alt="Scan preview">';
    }

    downloadAreaEl.innerHTML =
      '<a href="' + result.url + '" download="' + result.file + '">Download ' + result.file + "</a>";
  } catch (err) {
    statusEl.textContent = "Error: " + err.message;
  } finally {
    scanButton.disabled = false;
  }
});
```

- [ ] **Step 4: Commit**

```bash
git add www-scanner/index.html www-scanner/style.css www-scanner/app.js
git commit -m "feat: add scanner web page"
```

---

### Task 8: Deploy script + README

**Files:**
- Create: `deploy/deploy.sh`
- Create: `README.md`

**Interfaces:**
- Consumes: the full `www-scanner/` tree (Tasks 1-7).
- Produces: a repeatable one-command deploy to the router.

- [ ] **Step 1: Write `deploy/deploy.sh`**

```bash
#!/bin/sh
# Deploy the scanner app to the router and reconfigure uhttpd.
# Usage: deploy/deploy.sh
set -eu

ROUTER="root@192.168.1.1"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)/www-scanner"
REMOTE_DIR="/www-scanner"

echo "== Syncing www-scanner/ to $ROUTER:$REMOTE_DIR =="
ssh "$ROUTER" "mkdir -p $REMOTE_DIR"
scp -r "$LOCAL_DIR"/* "$ROUTER:$REMOTE_DIR/"
ssh "$ROUTER" "chmod +x $REMOTE_DIR/cgi-bin/scan.py $REMOTE_DIR/cgi-bin/download.py"
ssh "$ROUTER" "mkdir -p /overlay/scans"

echo "== Reconfiguring uhttpd (LuCI -> :81, scanner -> :80) =="
ssh "$ROUTER" '
  set -e
  uci delete uhttpd.main.listen_http 2>/dev/null || true
  uci add_list uhttpd.main.listen_http="0.0.0.0:81"
  uci add_list uhttpd.main.listen_http="[::]:81"

  uci delete uhttpd.scanner 2>/dev/null || true
  uci set uhttpd.scanner=uhttpd
  uci add_list uhttpd.scanner.listen_http="0.0.0.0:80"
  uci add_list uhttpd.scanner.listen_http="[::]:80"
  uci set uhttpd.scanner.home="/www-scanner"
  uci set uhttpd.scanner.cgi_prefix="/cgi-bin"
  uci set uhttpd.scanner.script_timeout="300"
  uci set uhttpd.scanner.network_timeout="30"

  uci commit uhttpd
  /etc/init.d/uhttpd restart
'

echo "== Done. LuCI: http://192.168.1.1:81  Scanner: http://192.168.1.1/ =="
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x deploy/deploy.sh`

- [ ] **Step 3: Write `README.md`**

```markdown
# OpenWRT Scanner

Web UI for scanning documents from a Canon LiDE 400 (USB `04a9:1912`) attached to
an OpenWrt router, served directly off the router via uhttpd + Python3 CGI.

- Scanner page: `http://192.168.1.1/`
- LuCI (moved off port 80): `http://192.168.1.1:81/`

## Layout

- `www-scanner/` - the deployed app (HTML/CSS/JS + `cgi-bin/` Python CGI scripts).
- `www-scanner/cgi-bin/scanlib/` - pure, unit-tested logic (validation, filename
  generation, path safety, scanimage command building).
- `tests/` - `unittest` tests for `scanlib`. Run: `python3 -m unittest discover tests`
- `deploy/deploy.sh` - rsyncs `www-scanner/` to the router and applies the uhttpd
  UCI config (LuCI -> :81, scanner app -> :80).
- `docs/superpowers/specs/` and `docs/superpowers/plans/` - design spec and
  implementation plan.

## Deploying

```bash
deploy/deploy.sh
```

Requires SSH key access to `root@192.168.1.1` (already set up).

## Scanner device

Backend is `sane-pixma`, device string `pixma:04A91912_43A16F` - NOT `sane-genesys`
(that backend doesn't support the LiDE 400 despite the model name suggesting it
should use genesys). Confirmed via `scanimage -L` on the router.
```

- [ ] **Step 4: Commit**

```bash
git add deploy/deploy.sh README.md
git commit -m "feat: add deploy script and README"
```

---

### Task 9: Deploy and live smoke test

**Files:** none (operational task against the real router).

**Interfaces:**
- Consumes: everything from Tasks 1-8.
- Produces: a working, verified scanner page and relocated LuCI.

- [ ] **Step 1: Run the full local test suite one more time**

Run: `python3 -m unittest discover tests -v`
Expected: `OK`, all tests from Tasks 1-4 pass.

- [ ] **Step 2: Deploy**

Run: `deploy/deploy.sh`
Expected: script completes with `== Done. ==` line, no SSH/UCI errors.

- [ ] **Step 3: Confirm LuCI moved**

Run: `curl -s -o /dev/null -w "%{http_code}\n" http://192.168.1.1:81/`
Expected: `200` (or a `30x` redirect to the LuCI login page — either is fine).

Run: `curl -s -o /dev/null -w "%{http_code}\n" --max-time 3 http://192.168.1.1:80/cgi-bin/luci 2>&1; true`
Expected: this should NOT be LuCI any more (port 80 is now the scanner app).

- [ ] **Step 4: Confirm HTTPS unaffected**

Run: `curl -sk -o /dev/null -w "%{http_code}\n" https://192.168.1.1:443/`
Expected: `200` (or LuCI's normal redirect/response code, same as before this change).

- [ ] **Step 5: Load the scanner page**

Run: `curl -s http://192.168.1.1/ | head -5`
Expected: the `<!doctype html>` / `<title>Scanner</title>` content from Task 7's `index.html`.

- [ ] **Step 6: Live scan via curl, 150dpi PDF**

Run:
```bash
curl -s -X POST http://192.168.1.1/cgi-bin/scan.py \
  -d "resolution=150&mode=Color&format=PDF"
```
Expected: JSON like `{"ok": true, "file": "scan_20260813_223045.pdf", "url": "/cgi-bin/download.py?name=scan_20260813_223045.pdf"}`.

- [ ] **Step 7: Confirm the file is retrievable and saved on the router**

Run: `curl -s -o /tmp/downloaded_test.pdf -w "%{http_code}\n" "http://192.168.1.1/cgi-bin/download.py?name=<file-from-step-6>"`
Expected: `200`, and `/tmp/downloaded_test.pdf` is a non-empty PDF.

Run: `ssh root@192.168.1.1 "ls -la /overlay/scans/"`
Expected: the same file listed there.

- [ ] **Step 8: Browser check of all format/mode combinations**

Open `http://192.168.1.1/` in a browser. Run one scan for each of: PDF+Color,
PDF+Grayscale, JPG+Color, JPG+Grayscale. Confirm for each: status line shows
"Scan saved: ...", preview renders (iframe for PDF, image for JPG), download
link works.

- [ ] **Step 9: Concurrency guard check**

Fire two scans back to back (e.g. two browser tabs, submit both quickly).
Expected: one succeeds, the other gets `{"ok": false, "error": "Scan already
in progress."}`.

- [ ] **Step 10: Commit any fixes found during smoke testing**

If any step above failed and required a code fix, commit it:
```bash
git add -A
git commit -m "fix: <describe the smoke-test fix>"
```

If everything passed with no changes needed, nothing to commit here.
