# Toyota NextMove backend

NextMove turns a synthetic Toyota customer profile, vehicle and contract into a ranked set of practical next actions. The backend owns deterministic calculations and data access; Gemini can explain results, and SerpApi can attach current public-market evidence.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,ai]"
cp .env.example .env  # skip this if .env already exists
uvicorn nextmove.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation. The health check is available at `GET /api/v1/health`.

The frontend-facing endpoints are:

- `GET /api/v1/profiles` — list available synthetic profile IDs from Snowflake
- `GET /api/v1/profiles/{profile_id}` — load the joined customer decision context
- `POST /api/v1/decisions/evaluate` — calculate, rank, and explain submitted options
- `GET /api/v1/guardian/providers?profile=alex&refresh=false` — return cached nearby
  service-provider evidence derived from the selected synthetic profile
- `POST /api/v1/guardian/chat` — explain the authoritative synthetic profile and current
  deterministic Guardian comparison, with optional confirmation-only scenario proposals

The decision endpoint still works without SerpApi or Gemini keys. It records missing live evidence as an unknown and returns deterministic explanatory copy.

Guardian provider discovery uses a persistent SQLite cache. Its default six-hour TTL means ordinary
page navigation does not spend SerpApi calls. Set `refresh=true` only for a deliberate refresh. The
backend derives the bounded search and location from the selected profile; browser-provided search
text is never accepted. Missing keys, errors, and empty results return clearly labeled synthetic
provider examples without prices or discounts.

Guardian chat makes one Gemini request only when the user explicitly sends a message. The backend
reloads the synthetic profile, recalculates the scenario, and reads provider evidence from SQLite
without refreshing SerpApi. Messages, history, and provider text are treated as untrusted data.
Model output is schema checked and rejected if it introduces unsupported numbers, citations, or
scenario values. Any rejected or unavailable response uses deterministic recommendation copy.
`GUARDIAN_GEMINI_TIMEOUT_SECONDS` controls the wait for that single request and defaults to 30
seconds; no automatic retry or extra model call is made.

## Configuration

Configuration comes from environment variables or `.env`. Snowflake defaults are shown in `.env.example`; local credentials and API keys belong only in `.env`, which Git ignores. `externalbrowser` authentication is recommended for the hackathon account because it does not store a password.

## Structure

```text
src/nextmove/
  api/          HTTP routes
  domain/       API and business-domain models
  services/     recommendation and integration logic
  repositories/ data-access implementations
```

The frontend should consume the versioned `/api/v1` contract. Keep financial calculations deterministic and include assumptions and evidence with every recommendation. Customer data used for the demo must be synthetic.

## Checks

```bash
pytest
ruff check .
```

