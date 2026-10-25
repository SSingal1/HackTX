# Toyota TCO & Smart Service Guardian sandbox

A TFS-inspired static frontend served by the Toyota NextMove FastAPI backend. The public homepage introduces Smart Service Guardian as a subpage of a simulated Toyota Financial Services experience.

- `dist/index.html`: simulated TFS homepage and Guardian entry point.
- `dist/guardian.html`: account dashboard with Overview, Maintenance, Local Offers, Keep vs. Upgrade, and My Next Move views.
- `dist/guardian.js`: same-origin Guardian API client and UI behavior.
- `dist/common.js` and `dist/styles.css`: shared responsive shell, dialogs, navigation, and design.

## Run with the backend

From `/Users/ashrithv/Projects/toyota-nextmove`, activate the Python environment and run:

```bash
uvicorn nextmove.main:app --reload
```

Open `http://127.0.0.1:8000/`. The backend serves this `dist` directory under `/site` and exposes the same-origin API at `/api/v1/guardian`, so no browser API key or separate frontend server is required.

## Data boundaries

The frontend loads synthetic customer, vehicle, contract, service-history, source, comparison, inquiry, and provider-evidence data from the backend. The backend prefers seeded Snowflake profiles and returns an explicitly labeled local synthetic fallback if Snowflake is unavailable. Upcoming service allowances remain frontend planning fixtures and are labeled as such.

The Local Offers view requests `/api/v1/guardian/providers?profile=<id>&refresh=false` once per profile and reuses that response in browser memory. The backend may return cached SerpApi evidence or a clearly labeled synthetic fallback. Only the **Refresh live results** confirmation sends `refresh=true`, which may consume one search API request. The browser never calls SerpApi directly and never receives an API key.

Provider prices, promotions, service scope, and Toyota authorization are always shown as unverified. Search snippets never become calculation inputs. The optional $50 adjustment remains a separate synthetic what-if toggle.

The assistant sends one request to `/api/v1/guardian/chat` only after a user submits a message or selects a suggestion. It sends the selected synthetic profile, current scenario, current view, and at most six short prior messages. The backend owns Gemini access, validation, authoritative calculations, cached evidence, and deterministic fallback; no key or direct Gemini call reaches the browser. Replies identify fallback/warning state and evidence IDs. Proposed scenario changes require an explicit confirmation before local state changes and a debounced comparison recalculation. Failed requests keep the chat open and do not alter the scenario.

Saved scenario controls use `localStorage`; saved inquiries go to the backend’s local demo database. No provider contact, payment, claim, or booking occurs.

Run the dependency-free frontend check with:

```bash
node check.mjs
```

Toyota marks belong to their respective owners. This independent hackathon sandbox is not affiliated with or endorsed by Toyota or Toyota Financial Services.
