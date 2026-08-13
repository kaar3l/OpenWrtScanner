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
