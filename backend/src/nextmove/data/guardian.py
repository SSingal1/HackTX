from __future__ import annotations

from copy import deepcopy
from threading import Lock
from time import monotonic
from typing import Any, Protocol

from .snowflake import SnowflakeRepository


class GuardianProfileRepository(Protocol):
    def list_guardian_profiles(self) -> dict[str, dict[str, Any]]: ...
    def get_guardian_profile(self, profile_id: str) -> dict[str, Any] | None: ...


LOCAL_SYNTHETIC_PROFILES: dict[str, dict[str, Any]] = {
    "alex": {
        "profile_id": "alex",
        "name": "Alex Morgan",
        "initials": "AM",
        "label": "Alex · no coverage",
        "coverage": 0,
        "cash": 7000,
        "reserve": 2000,
        "region": "Austin, TX",
        "vehicle": {
            "vehicle_id": "guardian-camry-alex",
            "year": 2018,
            "make": "Toyota",
            "model": "Camry",
            "trim": "SE",
            "mileage": 78000,
        },
        "service_needs": [
            {
                "service_id": "brake-estimate-alex",
                "service_type": "Brake pads & rotor service",
                "estimated_cost": 1800,
                "status": "estimate_ready",
                "source": "synthetic_customer_estimate",
                "updated_at": "2026-10-24",
            }
        ],
        "telemetry": {
            "captured_at": "2026-10-25T09:15:00-05:00",
            "odometer_miles": 78000,
            "tire_pressure_psi": {
                "front_left": 34,
                "front_right": 34,
                "rear_left": 33,
                "rear_right": 33,
            },
            "battery": {
                "type": "12V",
                "health_percent": 82,
                "voltage": 12.5,
                "state_of_charge_percent": None,
                "estimated_range_miles": None,
                "equivalent_full_cycles": None,
            },
        },
        "contract": {
            "contract_id": "guardian-contract-alex",
            "contract_type": "CASH",
            "monthly_payment": 0,
            "payoff_amount": 0,
        },
        "service_history": [
            {
                "service_id": "guardian-service-alex-1",
                "service_date": "2026-08-15",
                "mileage": 76500,
                "service_type": "Inspection",
                "cost": 0,
                "notes": "Brake service recommended; synthetic record.",
            }
        ],
    },
    "covered": {
        "profile_id": "covered",
        "name": "Jordan Lee",
        "initials": "JL",
        "label": "Jordan · $1,000 coverage",
        "coverage": 1000,
        "cash": 7000,
        "reserve": 2000,
        "region": "Austin, TX",
        "vehicle": {
            "vehicle_id": "guardian-camry-covered",
            "year": 2019,
            "make": "Toyota",
            "model": "Camry",
            "trim": "LE",
            "mileage": 69000,
        },
        "service_needs": [
            {
                "service_id": "brake-estimate-covered",
                "service_type": "Brake pads & rotor service",
                "estimated_cost": 1800,
                "status": "estimate_ready",
                "source": "synthetic_customer_estimate",
                "updated_at": "2026-10-24",
            }
        ],
        "telemetry": {
            "captured_at": "2026-10-25T09:17:00-05:00",
            "odometer_miles": 69000,
            "tire_pressure_psi": {
                "front_left": 35,
                "front_right": 35,
                "rear_left": 34,
                "rear_right": 34,
            },
            "battery": {
                "type": "12V",
                "health_percent": 91,
                "voltage": 12.7,
                "state_of_charge_percent": None,
                "estimated_range_miles": None,
                "equivalent_full_cycles": None,
            },
        },
        "contract": {
            "contract_id": "guardian-contract-covered",
            "contract_type": "CASH",
            "monthly_payment": 0,
            "payoff_amount": 0,
        },
        "service_history": [
            {
                "service_id": "guardian-service-covered-1",
                "service_date": "2026-09-02",
                "mileage": 68400,
                "service_type": "Diagnostic",
                "cost": 125,
                "notes": "Repair eligible for $1,000 synthetic coverage.",
            }
        ],
    },
    "limited": {
        "profile_id": "limited",
        "name": "Sam Rivera",
        "initials": "SR",
        "label": "Sam · limited cash",
        "coverage": 0,
        "cash": 2800,
        "reserve": 2000,
        "region": "Austin, TX",
        "vehicle": {
            "vehicle_id": "guardian-camry-limited",
            "year": 2017,
            "make": "Toyota",
            "model": "Camry",
            "trim": "XLE",
            "mileage": 92000,
        },
        "service_needs": [
            {
                "service_id": "brake-estimate-limited",
                "service_type": "Brake pads & rotor service",
                "estimated_cost": 1800,
                "status": "estimate_ready",
                "source": "synthetic_customer_estimate",
                "updated_at": "2026-10-24",
            }
        ],
        "telemetry": {
            "captured_at": "2026-10-25T09:20:00-05:00",
            "odometer_miles": 92000,
            "tire_pressure_psi": {
                "front_left": 31,
                "front_right": 33,
                "rear_left": 32,
                "rear_right": 32,
            },
            "battery": {
                "type": "12V",
                "health_percent": 68,
                "voltage": 12.2,
                "state_of_charge_percent": None,
                "estimated_range_miles": None,
                "equivalent_full_cycles": None,
            },
        },
        "contract": {
            "contract_id": "guardian-contract-limited",
            "contract_type": "CASH",
            "monthly_payment": 0,
            "payoff_amount": 0,
        },
        "service_history": [
            {
                "service_id": "guardian-service-limited-1",
                "service_date": "2026-07-20",
                "mileage": 90800,
                "service_type": "Inspection",
                "cost": 0,
                "notes": "Brake and tire work recommended; synthetic record.",
            }
        ],
    },
}


class ResilientGuardianProfileRepository:
    """Snowflake-first demo repository with an explicitly labeled local fallback."""

    _cache_ttl_seconds = 300

    def __init__(self, snowflake: SnowflakeRepository | None) -> None:
        self.snowflake = snowflake
        self._cache_lock = Lock()
        self._profile_cache: tuple[float, dict[str, dict[str, Any]]] | None = None

    def list_guardian_profiles(self) -> dict[str, dict[str, Any]]:
        with self._cache_lock:
            now = monotonic()
            if self._profile_cache is not None:
                expires_at, profiles = self._profile_cache
                if now < expires_at:
                    return deepcopy(profiles)
                self._profile_cache = None

            profiles = self._load_snowflake_profiles()
            if profiles is None:
                return self._fallback()
            self._profile_cache = (monotonic() + self._cache_ttl_seconds, profiles)
            return deepcopy(profiles)

    def get_guardian_profile(self, profile_id: str) -> dict[str, Any] | None:
        return self.list_guardian_profiles().get(profile_id)

    def _load_snowflake_profiles(self) -> dict[str, dict[str, Any]] | None:
        if self.snowflake is None:
            return None
        try:
            profiles = self.snowflake.list_guardian_profiles()
        except Exception:
            return None
        if (
            not isinstance(profiles, dict)
            or not profiles
            or any(
                not isinstance(profile_id, str)
                or not isinstance(profile, dict)
                or profile.get("profile_id", profile_id) != profile_id
                for profile_id, profile in profiles.items()
            )
        ):
            return None
        return self._with_telemetry(profiles)

    @staticmethod
    def _with_telemetry(profiles: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Merge the simulated app snapshot into Snowflake-backed personas.

        Telemetry is deliberately labeled and never represented as a live vehicle feed.
        The matching Snowflake table is created by the demo migration, while this merge
        keeps older workshop databases usable until that migration is run.
        """
        result = deepcopy(profiles)
        for profile_id, profile in result.items():
            fixture = LOCAL_SYNTHETIC_PROFILES.get(profile_id, {})
            profile.setdefault("telemetry", deepcopy(fixture.get("telemetry", {})))
            profile.setdefault("service_needs", deepcopy(fixture.get("service_needs", [])))
        return result

    @staticmethod
    def _fallback() -> dict[str, dict[str, Any]]:
        profiles = deepcopy(LOCAL_SYNTHETIC_PROFILES)
        for profile in profiles.values():
            profile["source"] = {"type": "local_synthetic_fallback", "simulated": True}
        return profiles
