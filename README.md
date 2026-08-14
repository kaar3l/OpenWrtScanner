# OpenWRT Scanner

Web UI for scanning documents from a Canon LiDE 400 (USB `04a9:1912`) attached to
an OpenWrt router, served directly off the router via uhttpd + Python3 CGI.
Deployable to multiple routers unmodified - see "Scanner device" below.

- Scanner page: `http://<router-ip>/`
- LuCI (moved off port 80): `http://<router-ip>:81/`

Currently deployed to:
- `192.168.1.1`
- `192.168.100.250`

## Layout

- `www-scanner/` - the deployed app (HTML/CSS/JS + `cgi-bin/` Python CGI scripts).
- `www-scanner/cgi-bin/scanlib/` - pure, unit-tested logic (validation, filename
  generation, path safety, scanimage command building, device detection).
- `tests/` - `unittest` tests for `scanlib`. Run: `python3 -m unittest discover tests`
- `deploy/deploy.sh` - syncs `www-scanner/` to a router and applies the uhttpd
  UCI config (LuCI -> :81, scanner app -> :80).
- `docs/superpowers/specs/` and `docs/superpowers/plans/` - design specs and
  implementation plans.

## Deploying

```bash
deploy/deploy.sh [router-ip]   # defaults to 192.168.1.1
```

Requires SSH key access to `root@<router-ip>` (already set up for both routers
above). Works against both `apk`-based and `opkg`-based OpenWrt releases - the
script detects which one the router has. It installs `python3-light`,
`python3-urllib` (`python3-light` alone omits the `urllib` module that
`scan.py`/`download.py`/`thumb.py` need), and the SANE packages, if missing.

## Scanner device

Backend is `sane-pixma`, NOT `sane-genesys` (that backend doesn't support the
LiDE 400 despite the model name suggesting it should).

The device string (e.g. `pixma:04A91912_43A16F`) embeds a per-unit USB serial
number, so it differs between physically identical scanners on different
routers. `scan.py` does **not** hardcode it - it runs `scanimage -L` and picks
the first device found (`scanlib/devicedetect.py`) fresh on every scan
request. This is what lets the same codebase deploy unmodified to any router
with exactly one attached scanner.
