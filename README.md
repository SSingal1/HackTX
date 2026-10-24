# Toyota TCO & Smart Service Guardian sandbox

Two responsive pages built with HTML, CSS and vanilla JavaScript. No installation or build step is required.

- `dist/index.html`: TFS-inspired public homepage with navigation, search, highlight carousel and Guardian entry point.
- `dist/guardian.html`: personalized service dashboard with five functional sections.
- `dist/common.js`: shared header, icons, accessible dialogs and sandbox notices.
- `dist/guardian.js`: deterministic cost calculations, profile fixtures, offer handling, what-if inputs, scripted assistant and browser-local plan storage.
- `dist/styles.css`: shared responsive design.
- `dist/assets/vehicle.svg`: local illustrative vehicle asset; no external image dependency.

## Run locally

Serve the `dist` directory using any static HTTP server, for example `npx serve dist`. Open `index.html`, then follow Smart Service Guardian. Hash routes preserve the five Guardian views.

## Demo data and interactions

Profiles: Alex has no repair coverage, Jordan has an explicit $1,000 synthetic benefit, and Sam has limited available cash. All share the same Camry and base estimate. The $50 brake promotion cannot stack with coverage. Mileage, repair amount and reserve controls recalculate the comparison. The assistant can propose edits, which require confirmation. Saved inquiries stay in `localStorage`, and plans can be exported as JSON. No actual provider contact, payment, claim or booking occurs.

## API integration boundaries

This is a frontend sandbox. It does not make live SerpApi, Gemini or Snowflake calls and does not collect secrets. The source identifies this in the UI. The recommended next implementation is a server with these routes:

- GET /api/profile: authenticated synthetic/authorized account context from Snowflake SQL API.
- POST /api/discover: server-controlled Google Search and Google Maps queries through SerpApi; normalize and save evidence with source URL and retrieval time.
- POST /api/compare: deterministic calculations followed by schema-validated Gemini explanation. Input modifications require confirmation.
- POST /api/inquiries and GET /api/history: persist and reload selected scenarios and simulated actions through Snowflake SQL API.

Put provider credentials in server environment variables, never the browser or repository. A real TFS integration requires separately authorized identity/account access. Service history and protection coverage require their own verified sources.

## Design and attribution

Public reference: https://www.toyotafinancial.com/us/en.html. This independent sandbox reproduces familiar TFS branding, navigation hierarchy, red accents and financial-services layouts, with a new Guardian experience. It is not a pixel-perfect clone or official Toyota property. The vehicle is an original SVG illustration. Google Fonts are optional; system font fallbacks are included. Toyota marks belong to their respective owners.
