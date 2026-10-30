#!/bin/bash
# Monthly restore drill: restore the latest backup of a site into a throwaway
# site, compare it with the live site, then delete the throwaway site.
#
#   DBPASS='mariadb root password' ~/restore_test.sh erp.client1.com [backup folder]
#
# DBPASS is read from the environment and handed to bench the same way
# (dz_core/secret_bench.py), never on a command line. The restored copy runs
# with its scheduler paused and e-mails muted, and the live site is compared
# as it was at the backup's time: the copy must hold at least that much.
#
# The backup folder defaults to the site's local backups. To test the OFF-SITE
# copy (the real disaster case), download it first and pass that folder:
#   rclone copy offsite:erp-backups/<server>/erp.client1.com/ /tmp/restore/ --max-age 48h
#   DBPASS=... ~/restore_test.sh erp.client1.com /tmp/restore
#
# Set KEEP=1 to keep the restored site (restore-test.localhost) for a look.
# Needs bench running (Frappe v16 needs its Redis to create a site).

set -euo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SITE="${1:?usage: restore_test.sh <site> [backup folder]}"
BENCH_DIR="${BENCH_DIR:-$HOME/frappe-bench}"
: "${DBPASS:?set DBPASS to the MariaDB root password}"
TEST_SITE="restore-test.localhost"

cd "$BENCH_DIR"
BACKUP_DIR="$(realpath "${2:-sites/$SITE/private/backups}")"

# The 4 files of the latest backup share one prefix: <date>_<time>-<site>
latest_db=$(ls -t "$BACKUP_DIR"/*-database.sql.gz 2>/dev/null | head -1)
[ -n "$latest_db" ] || { echo "No *-database.sql.gz in $BACKUP_DIR"; exit 1; }
B="${latest_db%-database.sql.gz}"
# Frappe 16 writes the files as .tar (.tgz with --compress, and before v15)
files_of() {
	for ext in tar tgz; do
		[ -f "$B-$1.$ext" ] && { echo "$B-$1.$ext"; return; }
	done
	echo "Missing $B-$1.tar (or .tgz): the backup is incomplete" >&2
	exit 1
}
PUBLIC=$(files_of files)
PRIVATE=$(files_of private-files)
[ -f "$B-site_config_backup.json" ] || { echo "Missing $B-site_config_backup.json"; exit 1; }
echo "=== Restoring $(basename "$B") into $TEST_SITE"
# The backup's own time, from its name (20261029_023000-<site>): the live site
# is compared as it was then
STAMP=$(basename "$B" | cut -c1-15)
BACKUP_TIME="${STAMP:0:4}-${STAMP:4:2}-${STAMP:6:2} ${STAMP:9:2}:${STAMP:11:2}:${STAMP:13:2}"

# bench commands that need the MariaDB root password get it through their
# environment (dz_core/secret_bench.py), never their arguments: any local
# user can read a process's arguments with ps
secret_bench() {
	(cd sites && DZ_DB_ROOT_PASSWORD="$DBPASS" "$BENCH_DIR/env/bin/python" -m dz_core.secret_bench "$@")
}

if [ -d "sites/$TEST_SITE" ]; then
	secret_bench --site "$TEST_SITE" drop-site "$TEST_SITE" --force --no-backup
fi
DZ_ADMIN_PASSWORD="$(head -c 18 /dev/urandom | base64)" \
	secret_bench --site "$TEST_SITE" new-site "$TEST_SITE" > /dev/null
# The copy must never act on the real world while it exists: no scheduler (the
# hourly courier sync with the client's keys), no e-mails. Both are site_config
# keys, which a restore keeps (review of 20 October 2026, 3.2)
bench --site "$TEST_SITE" set-config pause_scheduler 1
bench --site "$TEST_SITE" set-config mute_emails 1
secret_bench --site "$TEST_SITE" restore "$B-database.sql.gz" \
	--with-public-files "$PUBLIC" --with-private-files "$PRIVATE"

# The original encryption key, so stored passwords (couriers' API tokens,
# e-mail accounts) can still be read
KEY=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('encryption_key',''))" \
	"$B-site_config_backup.json")
[ -n "$KEY" ] && bench --site "$TEST_SITE" set-config encryption_key "$KEY"
bench --site "$TEST_SITE" migrate > /dev/null

echo "=== Comparing the live site as it was at $BACKUP_TIME with the restored copy"
check() {
	bench --site "$1" execute dz_core.setup.restore_check.summary ${2:+--kwargs "{'until': '$2'}"} \
		2>/dev/null | tail -1
}
LIVE=$(check "$SITE" "$BACKUP_TIME")
RESTORED=$(check "$TEST_SITE")

status=0
python3 - "$LIVE" "$RESTORED" <<'EOF' || status=$?
import json, sys
live, restored = json.loads(sys.argv[1]), json.loads(sys.argv[2])
problems = []
print(f"{'':22}{'live at backup':>28}{'restored':>28}")
for key in live:
	print(f"{key:22}{str(live[key]):>28}{str(restored.get(key)):>28}")
	if key.startswith("passwords"):
		continue
	# What existed at the backup must all be in the copy: fewer records, or an
	# older last record, is a loss (a deletion after the backup is no problem)
	if isinstance(live[key], int) and restored.get(key, 0) < live[key]:
		problems.append(key)
	if key.startswith("last ") and live[key] and str(restored.get(key) or "") < live[key]:
		problems.append(key)
if restored["passwords_unreadable"]:
	problems.append("passwords cannot be decrypted (wrong encryption_key)")
if problems:
	print("RESTORE TEST FAILED:", ", ".join(problems))
	sys.exit(1)
print("RESTORE TEST OK")
EOF

if [ "${KEEP:-0}" = "1" ]; then
	echo "Kept $TEST_SITE (drop it with: bench drop-site $TEST_SITE --force)"
else
	secret_bench --site "$TEST_SITE" drop-site "$TEST_SITE" --force --no-backup > /dev/null
	echo "Dropped $TEST_SITE"
fi
exit $status
