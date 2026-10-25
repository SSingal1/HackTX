#!/usr/bin/env python3
"""Open browser authentication and verify the backend can read its demo profile."""

from nextmove.data.snowflake import SnowflakeRepository, SnowflakeSettings


def main() -> None:
    settings = SnowflakeSettings.from_env()
    if settings.authenticator.lower() == "snowflake" and not settings.password:
        raise SystemExit(
            "Native Snowflake authentication needs SNOWFLAKE_PASSWORD in .env. "
            "Keep that file local and never commit it."
        )
    repository = SnowflakeRepository(settings)
    try:
        health = repository.health()
        profile = repository.get_profile("rav4-lease-001")
    except Exception as exc:
        if getattr(exc, "errno", None) == 390190:
            raise SystemExit(
                "Browser SSO is unavailable for this Snowflake account. Set "
                "SNOWFLAKE_AUTHENTICATOR=snowflake and add SNOWFLAKE_PASSWORD "
                "to your local .env, then run this test again."
            ) from None
        raise
    print("Snowflake connection successful")
    print(f"Role: {health['ROLE']}")
    print(f"Location: {health['DATABASE']}.{health['SCHEMA']}")
    print(f"Warehouse: {health['WAREHOUSE']}")
    print(f"Customer count: {health['CUSTOMER_COUNT']}")
    print(f"Demo profile: {profile['profile_id'] if profile else 'missing'}")


if __name__ == "__main__":
    main()
