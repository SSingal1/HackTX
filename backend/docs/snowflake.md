# Snowflake connection

Snowflake trial accounts may not have a SAML identity provider. For those accounts, use native
Snowflake authentication. The password stays only in the ignored local `.env` and is excluded from
configuration representations and application output.

Required environment values:

```dotenv
SNOWFLAKE_ACCOUNT=PVTBTXA-GS22830
SNOWFLAKE_USER=ASHV04
SNOWFLAKE_PASSWORD=your-snowflake-password
SNOWFLAKE_AUTHENTICATOR=snowflake
SNOWFLAKE_ROLE=NEXTMOVE_APP_ROLE
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=TFS_NEXT_MOVE
SNOWFLAKE_SCHEMA=CORE
```

Run `sql/001_schema.sql`, `sql/002_seed_demo.sql`, and `sql/003_app_role.sql` only if that setup has not already been completed. Then install the project and run:

```bash
python scripts/test_snowflake_connection.py
```

A successful check reports the active role, database, schema, warehouse, customer count, and demo
profile. Never commit `.env` or paste its password into source code, screenshots, or chat.

If the account later has working SAML/SSO, remove `SNOWFLAKE_PASSWORD` and set
`SNOWFLAKE_AUTHENTICATOR=externalbrowser` to return to browser authentication.

