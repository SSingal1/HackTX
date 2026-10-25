import os
import tempfile
import unittest
from decimal import Decimal
from unittest.mock import patch

from nextmove.data.snowflake import SnowflakeRepository, SnowflakeSettings


class FakeCursor:
    description = [("PROFILE_ID",)]

    def __init__(self, rows):
        self.rows, self.query, self.params = rows, None, None

    def execute(self, query, params=None):
        self.query, self.params = query, params

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)
        self.committed = self.rolled_back = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class SnowflakeSettingsTests(unittest.TestCase):
    def test_defaults_are_project_values(self):
        with patch.dict(
            os.environ, {"SNOWFLAKE_ACCOUNT": "org-account", "SNOWFLAKE_USER": "user"}, clear=True
        ):
            settings = SnowflakeSettings.from_env(env_file="/does/not/exist")
        self.assertEqual(settings.authenticator, "externalbrowser")
        self.assertEqual(settings.role, "NEXTMOVE_APP_ROLE")
        self.assertEqual(settings.warehouse, "COMPUTE_WH")
        self.assertNotIn("password", settings.connection_kwargs())

    def test_missing_identity_fails_early(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "SNOWFLAKE_ACCOUNT"):
                SnowflakeSettings.from_env(env_file="/does/not/exist")

    def test_dotenv_loads_and_environment_overrides_it(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = os.path.join(directory, ".env")
            with open(env_file, "w", encoding="utf-8") as handle:
                handle.write(
                    "SNOWFLAKE_ACCOUNT=file-account\n"
                    "SNOWFLAKE_USER=file-user\n"
                    "SNOWFLAKE_WAREHOUSE=file-warehouse\n"
                )
            with patch.dict(
                os.environ,
                {"SNOWFLAKE_ACCOUNT": "environment-account"},
                clear=True,
            ):
                settings = SnowflakeSettings.from_env(env_file=env_file)

        self.assertEqual(settings.account, "environment-account")
        self.assertEqual(settings.user, "file-user")
        self.assertEqual(settings.warehouse, "file-warehouse")

    def test_native_password_is_passed_but_hidden_from_repr(self):
        with patch.dict(
            os.environ,
            {
                "SNOWFLAKE_ACCOUNT": "org-account",
                "SNOWFLAKE_USER": "user",
                "SNOWFLAKE_PASSWORD": "do-not-display",
                "SNOWFLAKE_AUTHENTICATOR": "snowflake",
            },
            clear=True,
        ):
            settings = SnowflakeSettings.from_env(env_file="/does/not/exist")

        self.assertEqual(settings.connection_kwargs()["password"], "do-not-display")
        self.assertEqual(settings.authenticator, "snowflake")
        self.assertNotIn("do-not-display", repr(settings))


class SnowflakeRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.settings = SnowflakeSettings(account="org-account", user="user")

    def test_profile_lookup_is_parameterized(self):
        connection = FakeConnection([])
        repository = SnowflakeRepository(self.settings, connection_factory=lambda **_: connection)
        self.assertIsNone(repository.get_profile("profile' OR 1=1 --"))
        self.assertEqual(connection.cursor_instance.params, ("profile' OR 1=1 --",))
        self.assertIn("PROFILE_ID = %s", connection.cursor_instance.query)

    def test_guardian_list_uses_one_batched_query_and_groups_service_rows(self):
        repository = SnowflakeRepository(self.settings)
        calls = []
        base = {
            "PROFILE_ID": "alex",
            "FIRST_NAME": "Alex Morgan",
            "INITIALS": "AM",
            "PROFILE_LABEL": "Alex",
            "SERVICE_COVERAGE_LIMIT": 0,
            "CASH_RESERVE": 7000,
            "PROTECTED_CASH_RESERVE": 2000,
            "REGION": "Austin, TX",
            "VEHICLE_ID": "vehicle-1",
            "MODEL_YEAR": 2018,
            "MAKE": "Toyota",
            "MODEL": "Camry",
            "TRIM": "SE",
            "CURRENT_MILEAGE": 78000,
            "CONTRACT_ID": "contract-1",
            "CONTRACT_TYPE": "CASH",
            "MONTHLY_PAYMENT": 0,
            "PAYOFF_AMOUNT": 0,
        }

        def fetch(query, params=None):
            calls.append((query, params))
            return [
                {
                    **base,
                    "SERVICE_ID": "service-2",
                    "SERVICE_DATE": "2026-09-01",
                    "SERVICE_MILEAGE": 77000,
                    "SERVICE_TYPE": "Inspection",
                    "SERVICE_COST": 0,
                    "NOTES": "Synthetic inspection",
                },
                {
                    **base,
                    "SERVICE_ID": "service-1",
                    "SERVICE_DATE": "2026-08-01",
                    "SERVICE_MILEAGE": 76000,
                    "SERVICE_TYPE": "Oil change",
                    "SERVICE_COST": 75,
                    "NOTES": "Synthetic service",
                },
            ]

        repository._fetch_all = fetch
        profiles = repository.list_guardian_profiles()

        self.assertEqual(len(calls), 2)
        self.assertIn("VEHICLE_TELEMETRY", calls[1][0])
        self.assertIn("LEFT JOIN SERVICE_HISTORY", calls[0][0])
        self.assertEqual(len(profiles["alex"]["service_history"]), 2)
        self.assertEqual(profiles["alex"]["region"], "Austin, TX")

    def test_scenario_is_committed_and_serializes_decimal(self):
        connection = FakeConnection([])
        repository = SnowflakeRepository(self.settings, connection_factory=lambda **_: connection)
        repository.save_scenario(
            {
                "run_id": "run-1",
                "profile_id": "profile-1",
                "decision_type": "LEASE_END",
                "horizon_months": 12,
                "calculator_version": "v1",
                "inputs": {"buyout": Decimal("24900.50")},
                "options": [],
            }
        )
        self.assertTrue(connection.committed)
        self.assertIn("24900.5", connection.cursor_instance.params[5])


if __name__ == "__main__":
    unittest.main()
