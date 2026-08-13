#!/bin/sh
# Deploy the scanner app to the router and reconfigure uhttpd.
# Usage: deploy/deploy.sh
set -eu

ROUTER="root@192.168.1.1"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)/www-scanner"
REMOTE_DIR="/www-scanner"

echo "== Syncing www-scanner/ to $ROUTER:$REMOTE_DIR =="
ssh "$ROUTER" "mkdir -p $REMOTE_DIR"
# Router has no /usr/libexec/sftp-server, so scp's default SFTP transfer fails.
# -O forces the legacy SCP protocol, which the router's ssh does support.
scp -O -r "$LOCAL_DIR"/* "$ROUTER:$REMOTE_DIR/"
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
