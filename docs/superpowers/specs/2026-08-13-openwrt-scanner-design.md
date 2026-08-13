# OpenWRT USB Scanner Web Server — Design

Date: 2026-08-13

## Context

Router: Google WiFi ("Gale"), OpenWrt 25.12.5, ipq40xx/chromium, arm_cortex-a7_neon-vfpv4,
494MB RAM, 3.5GB free on `/overlay` (extroot). Reached at `192.168.1.1`, SSH as `root`
(key-based, no password prompt).

USB scanner: Canon CanoScan LiDE 400, USB ID `04a9:1912`. SANE backend: `sane-pixma`
(NOT genesys — genesys backend does not list this model; pixma detects it fine as
`pixma:04A91912_43A16F`, "CANON CanoScan LiDE 400 multi-function peripheral").

Verified device-specific scanimage options:
- `--resolution`: `75|150|300|600|1200|2400|4800dpi` (default 75)
- `--mode`: `auto|Color|Gray|48 bits color|16 bits gray|Lineart` (default Color)
- `--format`: `pnm|tiff|png|jpeg|pdf` (scanimage native, no extra conversion needed)

No Node.js in this router's opkg/apk feeds. `python3-light-3.13.9` is available.
uhttpd (already installed, already serving LuCI) supports multiple listen instances
and a `cgi_prefix`, so CGI is a natural fit — no extra webserver needed.

Live test: `scanimage -d pixma:04A91912_43A16F --resolution 150 --mode Color
--format=pdf -o test.pdf` succeeded in ~13s, produced a 53KB PDF.

## Requirements (from todo.txt)

1. Move LuCI off port 80 to port 81.
2. New page on port 80: scanner web UI.
3. Resolution setting: 150/300/600/1200dpi, default 150.
4. Mode setting: Color or Grayscale, default Color.
5. Format setting: PDF or JPG, default PDF.
6. Scanned image preview on the page.
7. Save the scanned document (on router).

## Decisions made during brainstorming

- Backend language: **Python3-light CGI** (no Node available; more maintainable than
  shell/Lua for HTML + binary streaming).
- Save behavior: save to router (`/overlay/scans/`) **and** show a download link in
  the UI.
- Access control: **no auth** — same LAN-trust model LuCI already uses.
- Scope: **single page per scan**, no multi-page/batch PDF assembly (YAGNI; todo.txt
  says "the scanned document", singular).

## Architecture

Two uhttpd instances on the router (one process, `/etc/config/uhttpd`, multiple
`config uhttpd` sections):

- `main` (existing, LuCI): `listen_http` changed `80` → `81` (both `0.0.0.0:81` and
  `[::]:81`). `listen_https` stays on `443`, unchanged.
- `scanner` (new): `listen_http` on `0.0.0.0:80` / `[::]:80`, `home '/www-scanner'`,
  `cgi_prefix '/cgi-bin'`, `script_timeout '300'` (a 1200dpi color scan can run
  minutes — default 60s is too short).

## Components

- `www-scanner/index.html`, `style.css`, `app.js` — single static page. Controls:
  resolution `<select>` (150/300/600/1200, default 150), mode `<select>`
  (Color/Grayscale, default Color — UI label "Grayscale" maps to CLI value `Gray`),
  format `<select>` (PDF/JPG, default PDF), Scan button, preview pane
  (`<iframe>` for PDF, `<img>` for JPG), download link, status/error line.

- `www-scanner/cgi-bin/scan.py` — CGI, POST. Parses
  `application/x-www-form-urlencoded` body from stdin via `urllib.parse.parse_qs`
  (no `cgi` stdlib module — removed in Python 3.13). Validates `resolution` against
  `{150,300,600,1200}`, `mode` against `{Color,Gray}`, `format` against
  `{pdf,jpeg}` — reject anything else with 400. Acquires an flock on
  `/tmp/scan.lock` (non-blocking; busy → JSON error, no queueing). Runs:

  ```
  scanimage -d pixma:04A91912_43A16F --resolution <R> --mode <M> --format=<F> \
      -o /overlay/scans/scan_<YYYYmmdd_HHMMSS>.<ext>
  ```

  On success: JSON `{"ok": true, "file": "<name>", "url": "/cgi-bin/download.py?name=<name>"}`.
  On failure (nonzero exit / timeout): JSON `{"ok": false, "error": "<message>"}`,
  CGI `Status: 500`.

- `www-scanner/cgi-bin/download.py` — CGI, GET, `?name=`. Whitelists the name against
  actual basenames present in `/overlay/scans/` (rejects `/`, `..`, anything not an
  exact match) to block path traversal. Streams the file with the right
  `Content-Type` (`application/pdf` / `image/jpeg`); used both for the preview
  pane's src and the download link.

## Data flow

Browser submits form → `scan.py` validates + locks + runs `scanimage` → file lands
in `/overlay/scans/` → JSON response with filename → `app.js` points the preview
element and download link at `download.py?name=...`.

## Error handling

- Scanner unplugged/not detected → scanimage exits nonzero → surfaced verbatim-ish
  as "Scanner not found — check USB connection."
- Concurrent scan attempt → lockfile held → "Scan already in progress."
- Invalid/missing form param → CGI 400, generic "Invalid request."
- Low disk space is not actively pre-checked (3.5GB free, single-page images are
  small — YAGNI).

## Testing

After deploy:
1. `curl` `scan.py` directly at 150dpi to confirm a file lands in `/overlay/scans/`.
2. Load the page in a browser, run one scan through each format (PDF, JPG) and mode
   (Color, Grayscale) combination at least once.
3. Confirm LuCI is still reachable on `:81` and HTTPS `:443` is unaffected.

## Out of scope (deliberately)

- Multi-page / batch scanning into one PDF.
- Authentication.
- Scan history / gallery of past scans in the UI (files just accumulate in
  `/overlay/scans/`; user can browse via SCP/Samba if ever needed).
