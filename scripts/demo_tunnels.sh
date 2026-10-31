#!/usr/bin/env bash
# The three demo sites on public links, to open them from another computer
# (docs/DEMO.md, "Show the demos from another computer").
#
#   bash ~/frappe-bench/apps/dz_core/scripts/demo_tunnels.sh          # start, print the links
#   bash ~/frappe-bench/apps/dz_core/scripts/demo_tunnels.sh stop     # close the links and the demo servers
#
# Each demo gets its own development server (bench serve, one port per site)
# and its own Cloudflare quick tunnel (no Cloudflare account, a new
# *.trycloudflare.com link at every start). Anyone with a link reaches the
# login page: stop it when the demo is over. bench serve runs with CI=1: it
# then starts Werkzeug without its debugger, whose error pages show the code
# and offer a console (frappe/app.py serve; review of 31 October 2026), and
# DEV_SERVER=0 (set by `bench start`): Frappe then shows tracebacks to anyone
# (frappe/utils/response.py is_traceback_allowed).
#
# Needs: `bench start` running (workers and Redis), cloudflared in ~/.local/bin
# or on the PATH, the demo sites already loaded (docs/DEMO.md "Create a demo
# site", dafter-cod docs/DEMO.md for the shop). A missing site is skipped.

set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"

BENCH_DIR="${BENCH_DIR:-$HOME/frappe-bench}"
LOGS="${LOGS:-$HOME/demo-tunnels}"
# site:port
DEMOS=("food-demo.localhost:8001" "atelier-demo.localhost:8002" "demo.localhost:8003")
# The shop has only Administrator after its load: a demo login is added
SHOP_SITE="demo.localhost"
SHOP_LOGIN="gerant@demo.localhost"
# A new password at every start, set on every demo login of the three sites:
# the repo is public, so a password written in it is no password on a public link
PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(12))")

cd "$BENCH_DIR" || { echo "No bench at $BENCH_DIR"; exit 1; }
mkdir -p "$LOGS"

stop() {
	pkill -f "cloudflared tunnel --no-autoupdate --url http://localhost:800[1-3]"
	pkill -f "serve --port 800[1-3]"
	sleep 1
}

if [ "${1:-start}" = "stop" ]; then
	stop
	echo "Demo links and demo servers stopped (bench start keeps running)."
	exit 0
fi

command -v cloudflared > /dev/null || { echo "cloudflared not found (~/.local/bin or PATH)"; exit 1; }
stop   # a new start gives new links: close the old ones first

for demo in "${DEMOS[@]}"; do
	site="${demo%%:*}"
	port="${demo##*:}"
	if [ ! -f "sites/$site/site_config.json" ]; then
		echo "--- $site: no such site, skipped"
		continue
	fi
	CI=1 DEV_SERVER=0 nohup bench --site "$site" serve --port "$port" > "$LOGS/serve-$port.log" 2>&1 &
	nohup cloudflared tunnel --no-autoupdate --url "http://localhost:$port" > "$LOGS/tunnel-$port.log" 2>&1 &
done

if [ -f "sites/$SHOP_SITE/site_config.json" ] \
	&& ! bench --site "$SHOP_SITE" execute frappe.db.exists --args "['User', '$SHOP_LOGIN']" 2> /dev/null \
		| grep -q "$SHOP_LOGIN"; then
	echo "--- adding the login $SHOP_LOGIN to $SHOP_SITE"
	bench --site "$SHOP_SITE" add-user "$SHOP_LOGIN" --first-name "Gérant" --password "$PASSWORD" \
		--add-role "Sales Manager" --add-role "Sales User" \
		--add-role "Stock Manager" --add-role "Stock User" \
		--add-role "Accounts Manager" --add-role "Accounts User"
fi

# The new password on every demo login, and no demo login keeps System Manager
for demo in "${DEMOS[@]}"; do
	site="${demo%%:*}"
	[ -f "sites/$site/site_config.json" ] || continue
	bench --site "$site" execute dz_core.demo.loader.secure_logins --args "['$PASSWORD']" > /dev/null \
		|| echo "--- $site: could not set the demo password, see the error above"
done

# A quick tunnel prints its link a few seconds after it starts
echo "Waiting for the links..."
for _ in $(seq 30); do
	sleep 1
	missing=0
	for demo in "${DEMOS[@]}"; do
		port="${demo##*:}"
		[ -f "$LOGS/tunnel-$port.log" ] || continue
		grep -q 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOGS/tunnel-$port.log" || missing=1
	done
	[ "$missing" = 0 ] && break
done

for demo in "${DEMOS[@]}"; do
	site="${demo%%:*}"
	port="${demo##*:}"
	[ -f "$LOGS/tunnel-$port.log" ] || continue
	link=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOGS/tunnel-$port.log" | head -1)
	printf "%-24s %s\n" "$site" "${link:-no link yet, see $LOGS/tunnel-$port.log}"
done
echo "Logins: docs/DEMO.md. Password for every demo login, until the next start: $PASSWORD"
echo "Stop with: $0 stop"
