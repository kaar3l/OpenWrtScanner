#!/bin/sh
# Deploy the scanner app to a router and reconfigure uhttpd.
# Usage: deploy/deploy.sh [router-ip]   (defaults to 192.168.1.1)
#
# Works against both apk-based (OpenWrt 23.05+/24.x+ snapshots) and
# opkg-based (older 24.x releases) routers - picks whichever is present.
set -eu

ROUTER_IP="${1:-192.168.1.1}"
ROUTER="root@$ROUTER_IP"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)/www-scanner"
REMOTE_DIR="/www-scanner"
PKGS="python3-light python3-urllib libsane sane-daemon sane-frontends sane-pixma"

echo "== Deploying to $ROUTER_IP =="

echo "== Ensuring required packages are installed (python3-light omits urllib) =="
ssh "$ROUTER" "
  if command -v apk >/dev/null 2>&1; then
    apk add $PKGS
  else
    opkg update >/dev/null 2>&1 || true
    opkg install $PKGS
  fi
"

echo "== Syncing www-scanner/ to $ROUTER:$REMOTE_DIR =="
ssh "$ROUTER" "mkdir -p $REMOTE_DIR"
# Router has no /usr/libexec/sftp-server, so scp's default SFTP transfer fails.
# -O forces the legacy SCP protocol, which the router's ssh does support.
scp -O -r "$LOCAL_DIR"/* "$ROUTER:$REMOTE_DIR/"
ssh "$ROUTER" "chmod +x $REMOTE_DIR/cgi-bin/scan.py $REMOTE_DIR/cgi-bin/download.py $REMOTE_DIR/cgi-bin/history.py $REMOTE_DIR/cgi-bin/thumb.py $REMOTE_DIR/cgi-bin/progress.py $REMOTE_DIR/cgi-bin/delete.py $REMOTE_DIR/cgi-bin/cancel.py"
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

echo "== Done. LuCI: http://$ROUTER_IP:81  Scanner: http://$ROUTER_IP/ =="
