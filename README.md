# AI-Powered Personal Diet Planner with Cloud Storage

A student project prototype with a React and Vite frontend, a FastAPI backend, Firebase Authentication, user-scoped Firestore records, and optional Gemini-assisted meal selection. It is an educational project, not a medical or clinical nutrition service. Use synthetic profile information while developing.

## Current features

- Create an account, sign in, and sign out with Firebase Authentication.
- Save a profile and generated plans in the signed-in user's Firestore records.
- Generate meal ideas from a predefined, ingredient-catalogued menu.
- When configured, Gemini arranges choices from the server-filtered menu. The server validates every selected meal name and ingredient list before returning the plan.
- If Gemini is not configured or unavailable, the local rule-based planner generates the plan instead.
- Browse saved plans and download a JSON copy. The downloaded copy is held in this browser's IndexedDB; it is not Firebase Cloud Storage.

## Architecture

- `frontend/` — React + Vite user interface and Firebase client integration.
- `backend/` — FastAPI profile validation and plan-generation endpoint.
- Gemini API — optional server-side meal arrangement; the API key stays in the backend environment.
- Cloud Firestore — stores profiles and saved plans under `users/{uid}/...`.
- `firestore.rules` — restricts those profile and plan documents to the signed-in user whose UID matches the path.

## Configure the Gemini key

Copy `backend/.env.example` to `backend/.env`, then add your Gemini API key to `GEMINI_API_KEY`. The `.env` file is ignored by Git. Never commit or share it. The default model is `gemini-3.8-flash`; set `GEMINI_MODEL` in the backend `.env` if you need to use a different model available to your account.

Use made-up profile details during development. Free-tier model availability and quotas can change. Do not send real health or allergy details to an AI provider unless you have reviewed its current data and privacy terms.

## Run locally

Keep the frontend and backend in separate PowerShell windows.

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173/`; the API documentation is at `http://127.0.0.1:8000/docs`.

## Storage note

Firebase Cloud Storage is not enabled. Profile and plan records use Cloud Firestore, but downloaded plan files are stored in browser IndexedDB and do not sync to other devices. This project does not currently support cloud file uploads.

## Limitations and next work

- Gemini can select and arrange only meals in the predefined menu. If the key is missing, a request fails, or the response fails validation, the local rule-based planner is used.
- Allergy and food exclusions are checked against a limited ingredient list. Ingredient variations, packaged-food labels, missing ingredients, and kitchen cross-contact are not checked. Review every ingredient and label; the planner cannot guarantee allergen safety.
- The app does not calculate calories, portions, macros, nutrition, hydration, or budget. It does not track daily intake or progress.
- The FastAPI endpoints do not yet verify Firebase ID tokens. Keep the backend local; it is not ready for public deployment.
- Firebase Cloud Storage, cloud deployment, automated tests, and the full report, screenshot, and interview materials described in the course specification are not implemented yet.
