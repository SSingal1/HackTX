from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import dotenv_values


@dataclass(frozen=True)
class SnowflakeSettings:
    account: str
    user: str
    password: str | None = field(default=None, repr=False)
    authenticator: str = "externalbrowser"
    role: str = "NEXTMOVE_APP_ROLE"
    warehouse: str = "COMPUTE_WH"
    database: str = "TFS_NEXT_MOVE"
    schema: str = "CORE"

    @classmethod
    def from_env(cls, env_file: str | os.PathLike[str] = ".env") -> SnowflakeSettings:
        """Load a local dotenv file, with real environment variables taking precedence."""
        file_values = dotenv_values(Path(env_file))

        def value(name: str, default: str = "") -> str:
            resolved = os.environ.get(name, file_values.get(name, default))
            return (resolved or default).strip()

        account = value("SNOWFLAKE_ACCOUNT")
        user = value("SNOWFLAKE_USER")
        missing = [
            name
            for name, value in (("SNOWFLAKE_ACCOUNT", account), ("SNOWFLAKE_USER", user))
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required Snowflake settings: {', '.join(missing)}")
        return cls(
            account=account,
            user=user,
            password=value("SNOWFLAKE_PASSWORD") or None,
            authenticator=value("SNOWFLAKE_AUTHENTICATOR", "externalbrowser"),
            role=value("SNOWFLAKE_ROLE", "NEXTMOVE_APP_ROLE"),
            warehouse=value("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=value("SNOWFLAKE_DATABASE", "TFS_NEXT_MOVE"),
            schema=value("SNOWFLAKE_SCHEMA", "CORE"),
        )

    def connection_kwargs(self) -> dict[str, Any]:
        settings = {
            "account": self.account,
            "user": self.user,
            "authenticator": self.authenticator,
            "role": self.role,
            "warehouse": self.warehouse,
            "database": self.database,
            "schema": self.schema,
            "login_timeout": 30,
            "client_session_keep_alive": False,
        }
        if self.password:
            settings["password"] = self.password
        return settings


PROFILE_QUERY = """
SELECT
  c.PROFILE_ID, c.REGION, c.BUDGET_MONTHLY, c.CASH_RESERVE, c.SIMULATED,
  v.VEHICLE_ID, v.MODEL_YEAR, v.MAKE, v.MODEL, v.TRIM, v.CURRENT_MILEAGE,
  ct.CONTRACT_ID, ct.CONTRACT_TYPE, ct.MONTHLY_PAYMENT, ct.MONTHS_REMAINING,
  ct.MATURITY_DATE, ct.BUYOUT_AMOUNT, ct.PAYOFF_AMOUNT, ct.APR,
  ct.REMAINING_TERM_MONTHS, ct.MILEAGE_ALLOWANCE, ct.EXCESS_MILE_RATE,
  ct.DISPOSITION_FEE, ct.CONTRACT_VERSION,
  mp.EXPECTED_MONTHLY_MILES, mp.HARD_CONSTRAINTS, mp.OPTIONAL_PREFERENCES
FROM CUSTOMER c
JOIN VEHICLE v USING (PROFILE_ID)
JOIN CONTRACT ct USING (PROFILE_ID, VEHICLE_ID)
LEFT JOIN MOBILITY_PREFERENCE mp USING (PROFILE_ID)
"""


class SnowflakeRepository:
    """Least-privilege adapter for the TFS_NEXT_MOVE.CORE schema."""

    def __init__(
        self, settings: SnowflakeSettings, connection_factory: Callable[..., Any] | None = None
    ) -> None:
        self.settings = settings
        self._connection_factory = connection_factory

    def _connect(self) -> Any:
        factory = self._connection_factory
        if factory is None:
            try:
                import snowflake.connector
            except ImportError as exc:
                raise RuntimeError(
                    "Install snowflake-connector-python before using Snowflake"
                ) from exc
            factory = snowflake.connector.connect
        return factory(**self.settings.connection_kwargs())

    def _fetch_all(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()
            connection.close()

    def _execute(self, query: str, params: tuple[Any, ...]) -> None:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(query, params)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def health(self) -> dict[str, Any]:
        return self._fetch_all("""
            SELECT CURRENT_USER() AS USER, CURRENT_ROLE() AS ROLE,
                   CURRENT_WAREHOUSE() AS WAREHOUSE, CURRENT_DATABASE() AS DATABASE,
                   CURRENT_SCHEMA() AS SCHEMA,
                   (SELECT COUNT(*) FROM CUSTOMER) AS CUSTOMER_COUNT
        """)[0]

    def list_profile_ids(self) -> list[str]:
        return [
            row["PROFILE_ID"]
            for row in self._fetch_all("SELECT PROFILE_ID FROM CUSTOMER ORDER BY PROFILE_ID")
        ]

    def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        rows = self._fetch_all(PROFILE_QUERY + " WHERE c.PROFILE_ID = %s", (profile_id,))
        return self._normalize_profile(rows[0]) if rows else None

    def list_guardian_profiles(self) -> dict[str, dict[str, Any]]:
        """Load the complete demo profile set with one Snowflake connection."""
        rows = self._fetch_all("""
            SELECT c.PROFILE_ID, c.FIRST_NAME, c.INITIALS, c.PROFILE_LABEL,
                   c.SERVICE_COVERAGE_LIMIT, c.CASH_RESERVE, c.PROTECTED_CASH_RESERVE,
                   c.REGION,
                   v.VEHICLE_ID, v.MODEL_YEAR, v.MAKE, v.MODEL, v.TRIM, v.CURRENT_MILEAGE,
                   ct.CONTRACT_ID, ct.CONTRACT_TYPE, ct.MONTHLY_PAYMENT, ct.PAYOFF_AMOUNT,
                   sh.SERVICE_ID, sh.SERVICE_DATE, sh.MILEAGE AS SERVICE_MILEAGE,
                   sh.SERVICE_TYPE, sh.COST AS SERVICE_COST, sh.NOTES
            FROM CUSTOMER c
            JOIN VEHICLE v USING (PROFILE_ID)
            LEFT JOIN CONTRACT ct USING (PROFILE_ID, VEHICLE_ID)
            LEFT JOIN SERVICE_HISTORY sh USING (VEHICLE_ID)
            WHERE c.PROFILE_ID IN ('alex', 'covered', 'limited') AND c.SIMULATED = TRUE
            ORDER BY c.PROFILE_ID, sh.SERVICE_DATE DESC
        """)
        grouped: dict[str, list[Mapping[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(row["PROFILE_ID"], []).append(row)
        profiles = {
            profile_id: self._normalize_guardian_profile(profile_rows)
            for profile_id, profile_rows in grouped.items()
        }
        try:
            telemetry_rows = self._fetch_all("""
                SELECT VEHICLE_ID, CAPTURED_AT, ODOMETER_MILES, TIRE_PRESSURE_PSI,
                       BATTERY_TYPE, BATTERY_HEALTH_PERCENT, BATTERY_VOLTAGE,
                       STATE_OF_CHARGE_PERCENT, ESTIMATED_RANGE_MILES,
                       EQUIVALENT_FULL_CYCLES
                FROM VEHICLE_TELEMETRY WHERE SIMULATED = TRUE
            """)
        except Exception:
            telemetry_rows = []
        by_vehicle = {row["VEHICLE_ID"]: self._normalize_telemetry(row) for row in telemetry_rows}
        for profile in profiles.values():
            telemetry = by_vehicle.get(profile["vehicle"]["vehicle_id"])
            if telemetry:
                profile["telemetry"] = telemetry
        return profiles

    @staticmethod
    def _normalize_telemetry(row: Mapping[str, Any]) -> dict[str, Any]:
        pressures = row.get("TIRE_PRESSURE_PSI") or {}
        if isinstance(pressures, str):
            pressures = json.loads(pressures)
        return {
            "captured_at": row.get("CAPTURED_AT"),
            "odometer_miles": row.get("ODOMETER_MILES"),
            "tire_pressure_psi": pressures,
            "battery": {
                "type": row.get("BATTERY_TYPE"),
                "health_percent": row.get("BATTERY_HEALTH_PERCENT"),
                "voltage": row.get("BATTERY_VOLTAGE"),
                "state_of_charge_percent": row.get("STATE_OF_CHARGE_PERCENT"),
                "estimated_range_miles": row.get("ESTIMATED_RANGE_MILES"),
                "equivalent_full_cycles": row.get("EQUIVALENT_FULL_CYCLES"),
            },
        }

    def get_guardian_profile(self, profile_id: str) -> dict[str, Any] | None:
        rows = self._fetch_all(
            """
            SELECT c.PROFILE_ID, c.FIRST_NAME, c.INITIALS, c.PROFILE_LABEL,
                   c.SERVICE_COVERAGE_LIMIT, c.CASH_RESERVE, c.PROTECTED_CASH_RESERVE,
                   v.VEHICLE_ID, v.MODEL_YEAR, v.MAKE, v.MODEL, v.TRIM, v.CURRENT_MILEAGE,
                   ct.CONTRACT_ID, ct.CONTRACT_TYPE, ct.MONTHLY_PAYMENT, ct.PAYOFF_AMOUNT
            FROM CUSTOMER c
            JOIN VEHICLE v USING (PROFILE_ID)
            LEFT JOIN CONTRACT ct USING (PROFILE_ID, VEHICLE_ID)
            WHERE c.PROFILE_ID = %s AND c.SIMULATED = TRUE
        """,
            (profile_id,),
        )
        if not rows:
            return None
        row = rows[0]
        services = self._fetch_all(
            """
            SELECT SERVICE_ID, SERVICE_DATE, MILEAGE, SERVICE_TYPE, COST, NOTES
            FROM SERVICE_HISTORY WHERE VEHICLE_ID = %s ORDER BY SERVICE_DATE DESC
        """,
            (row["VEHICLE_ID"],),
        )
        enriched = [
            {
                **row,
                "SERVICE_ID": service["SERVICE_ID"],
                "SERVICE_DATE": service["SERVICE_DATE"],
                "SERVICE_MILEAGE": service["MILEAGE"],
                "SERVICE_TYPE": service["SERVICE_TYPE"],
                "SERVICE_COST": service["COST"],
                "NOTES": service["NOTES"],
            }
            for service in services
        ]
        return self._normalize_guardian_profile(enriched or [row])

    def _normalize_guardian_profile(self, rows: list[Mapping[str, Any]]) -> dict[str, Any]:
        row = rows[0]
        service_history = [
            {
                "service_id": service["SERVICE_ID"],
                "service_date": service["SERVICE_DATE"],
                "mileage": service["SERVICE_MILEAGE"],
                "service_type": service["SERVICE_TYPE"],
                "cost": service["SERVICE_COST"] or 0,
                "notes": service["NOTES"],
            }
            for service in rows
            if service.get("SERVICE_ID") is not None
        ]
        return {
            "profile_id": row["PROFILE_ID"],
            "name": row["FIRST_NAME"],
            "initials": row["INITIALS"],
            "label": row["PROFILE_LABEL"],
            "coverage": row["SERVICE_COVERAGE_LIMIT"] or 0,
            "cash": row["CASH_RESERVE"],
            "reserve": row["PROTECTED_CASH_RESERVE"],
            "region": row.get("REGION"),
            "vehicle": {
                "vehicle_id": row["VEHICLE_ID"],
                "year": row["MODEL_YEAR"],
                "make": row["MAKE"],
                "model": row["MODEL"],
                "trim": row["TRIM"],
                "mileage": row["CURRENT_MILEAGE"],
            },
            "contract": {
                "contract_id": row["CONTRACT_ID"],
                "contract_type": row["CONTRACT_TYPE"],
                "monthly_payment": row["MONTHLY_PAYMENT"] or 0,
                "payoff_amount": row["PAYOFF_AMOUNT"] or 0,
            },
            "service_history": service_history,
            "source": {
                "type": "snowflake",
                "database": self.settings.database,
                "schema": self.settings.schema,
                "simulated": True,
            },
        }

    def get_evidence(self, evidence_ids: list[str]) -> list[dict[str, Any]]:
        if not evidence_ids:
            return []
        placeholders = ", ".join(["%s"] * len(evidence_ids))
        query = (
            "SELECT * FROM EVIDENCE "
            f"WHERE EVIDENCE_ID IN ({placeholders}) ORDER BY RETRIEVED_AT DESC"
        )
        return self._fetch_all(
            query,
            tuple(evidence_ids),
        )

    def save_evidence(self, evidence: Mapping[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO EVIDENCE
              (EVIDENCE_ID, SOURCE_TYPE, SOURCE_URL, RETRIEVED_AT, QUERY_PARAMETERS,
               NORMALIZED_FACTS, RAW_RESPONSE, STATUS)
            SELECT %s, %s, %s, CURRENT_TIMESTAMP(),
                   PARSE_JSON(%s), PARSE_JSON(%s), PARSE_JSON(%s), %s
        """,
            (
                evidence["evidence_id"],
                evidence["source_type"],
                evidence.get("source_url"),
                _json(evidence.get("query_parameters", {})),
                _json(evidence.get("normalized_facts", {})),
                _json(evidence.get("raw_response", {})),
                evidence.get("status", "LIVE"),
            ),
        )

    def save_scenario(self, scenario: Mapping[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO SCENARIO_RUN
              (RUN_ID, PROFILE_ID, DECISION_TYPE, HORIZON_MONTHS, CALCULATOR_VERSION,
               INPUTS, OPTIONS, ASSUMPTIONS, UNKNOWNS, EVIDENCE_IDS, RECOMMENDED_OPTION_ID)
            SELECT %s, %s, %s, %s, %s, PARSE_JSON(%s), PARSE_JSON(%s), PARSE_JSON(%s),
                   PARSE_JSON(%s), PARSE_JSON(%s), %s
        """,
            (
                scenario["run_id"],
                scenario["profile_id"],
                scenario["decision_type"],
                scenario["horizon_months"],
                scenario["calculator_version"],
                _json(scenario.get("inputs", {})),
                _json(scenario.get("options", [])),
                _json(scenario.get("assumptions", [])),
                _json(scenario.get("unknowns", [])),
                _json(scenario.get("evidence_ids", [])),
                scenario.get("recommended_option_id"),
            ),
        )

    def record_action(self, action: Mapping[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO ACTION_EVENT
              (ACTION_EVENT_ID, RUN_ID, PROFILE_ID, ACTION_TYPE, ACTION_STATUS, PAYLOAD)
            SELECT %s, %s, %s, %s, %s, PARSE_JSON(%s)
        """,
            (
                action["action_event_id"],
                action["run_id"],
                action["profile_id"],
                action["action_type"],
                action.get("action_status", "SIMULATED"),
                _json(action.get("payload", {})),
            ),
        )

    @staticmethod
    def _normalize_profile(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "profile_id": row["PROFILE_ID"],
            "region": row["REGION"],
            "budget_monthly": row["BUDGET_MONTHLY"],
            "cash_reserve": row["CASH_RESERVE"],
            "simulated": bool(row["SIMULATED"]),
            "vehicle": {
                "vehicle_id": row["VEHICLE_ID"],
                "model_year": row["MODEL_YEAR"],
                "make": row["MAKE"],
                "model": row["MODEL"],
                "trim": row["TRIM"],
                "current_mileage": row["CURRENT_MILEAGE"],
            },
            "contract": {
                "contract_id": row["CONTRACT_ID"],
                "contract_type": row["CONTRACT_TYPE"],
                "monthly_payment": row["MONTHLY_PAYMENT"],
                "months_remaining": row["MONTHS_REMAINING"],
                "maturity_date": row["MATURITY_DATE"],
                "buyout_amount": row["BUYOUT_AMOUNT"],
                "payoff_amount": row["PAYOFF_AMOUNT"],
                "apr": row["APR"],
                "remaining_term_months": row["REMAINING_TERM_MONTHS"],
                "mileage_allowance": row["MILEAGE_ALLOWANCE"],
                "excess_mile_rate": row["EXCESS_MILE_RATE"],
                "disposition_fee": row["DISPOSITION_FEE"],
                "contract_version": row["CONTRACT_VERSION"],
            },
            "mobility_preference": {
                "expected_monthly_miles": row["EXPECTED_MONTHLY_MILES"],
                "hard_constraints": _variant(row["HARD_CONSTRAINTS"], {}),
                "optional_preferences": _variant(row["OPTIONAL_PREFERENCES"], {}),
            },
        }


def _json(value: Any) -> str:
    return json.dumps(value, default=_json_default, separators=(",", ":"))


def _variant(value: Any, default: Any) -> Any:
    """Normalize Snowflake VARIANT values across connector configurations."""
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Cannot serialize {type(value).__name__} to JSON")
