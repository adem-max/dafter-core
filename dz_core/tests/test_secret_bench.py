"""dz_core.secret_bench: passwords from the environment, never the command line
(review of 27 October 2026, 3.1).

Run: bench --site <site> run-tests --module dz_core.tests.test_secret_bench
"""

from frappe.tests import UnitTestCase

from dz_core.secret_bench import argv


class TestSecretBench(UnitTestCase):
	def test_passwords_move_from_the_environment_to_the_options(self):
		environ = {"DZ_DB_ROOT_PASSWORD": "root-pw", "DZ_ADMIN_PASSWORD": "admin-pw", "PATH": "/usr/bin"}
		args = argv(["--site", "a.localhost", "new-site", "a.localhost"], environ)
		self.assertEqual(
			args,
			[
				"bench",
				"frappe",
				"--site",
				"a.localhost",
				"new-site",
				"a.localhost",
				"--db-root-password",
				"root-pw",
				"--admin-password",
				"admin-pw",
			],
		)
		# taken out: the bench command's own children do not inherit them
		self.assertEqual(environ, {"PATH": "/usr/bin"})

	def test_no_password_no_option(self):
		self.assertEqual(argv(["--site", "a.localhost", "drop-site", "a.localhost"], {})[-1], "a.localhost")
