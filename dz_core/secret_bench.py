"""Run one bench command whose passwords come from the environment, never
from the command line (reviews of 20 and 27 October 2026, 3.3 and 3.1).

    DZ_DB_ROOT_PASSWORD=... [DZ_ADMIN_PASSWORD=...] \\
        python -m dz_core.secret_bench --site <site> <command> [args...]

Run from the bench's sites folder with the bench's Python, like `bench`.

Any local user can read a process's arguments (`ps`, /proc/<pid>/cmdline);
only the same user and root can read its environment. This process starts
with the site and the command only. It takes the passwords out of its
environment (so the bench command's own children do not inherit them), adds
them as --db-root-password / --admin-password to its own sys.argv, which
Python changes in memory only (the kernel keeps the cmdline it was started
with), then runs bench's own entry point, as `bench` would.

Used by the hub's "Créer le site" (dz_hub/remote.py) and the restore drill
(scripts/restore_test.sh). `new-site`, `restore` and `drop-site` take both
options; a command that takes no admin password gets none.
"""

import os
import sys

SECRETS = {"DZ_DB_ROOT_PASSWORD": "--db-root-password", "DZ_ADMIN_PASSWORD": "--admin-password"}


def argv(args, environ):
	"""The argv bench's entry point reads, with the passwords taken out of `environ`."""
	extra = []
	for name, option in SECRETS.items():
		value = environ.pop(name, None)
		if value:
			extra += [option, value]
	return ["bench", "frappe", *args, *extra]


def main():
	sys.argv = argv(sys.argv[1:], os.environ)
	from frappe.utils.bench_helper import main as bench

	bench()


if __name__ == "__main__":
	main()
