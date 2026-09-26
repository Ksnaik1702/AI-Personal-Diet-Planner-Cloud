# AI-Powered Personal Diet Planner with Cloud Storage

A student cloud-computing project demonstrating a React frontend, FastAPI backend, Firebase Authentication, user-scoped Firestore data, and rule-based sample plan generation. Use synthetic/demo profile details only. Meal ideas are educational examples, not medical or clinical nutrition advice.

## Current architecture

- `frontend/` — React + Vite app with Firebase email/password sign-in.
- `backend/` — FastAPI service with profile validation and a deterministic sample-plan endpoint.
- Firebase Authentication — identifies signed-in demo users.
- Cloud Firestore — stores each user's profile and generated plans under `users/{uid}/...`.
- `firestore.rules` — restricts profile and plan documents to the signed-in user whose UID matches the document path.
- `frontend/src/localObjectStorage.js` — simulates object storage in browser IndexedDB and provides a plan JSON download.

## Storage note

Firebase Cloud Storage is not enabled in this project. Firebase currently requires the pay-as-you-go Blaze plan to provision or use a Cloud Storage bucket. This project is staying on the no-cost Spark plan, so plan files use the local IndexedDB simulator instead. Firestore remains the real cloud database. The local simulator does not sync files to other devices.

If a Firebase Storage bucket is enabled later, the project can replace the local adapter with Firebase Storage and publish per-user Storage Security Rules. Review the current [Firebase Storage pricing requirements](https://firebase.google.com/docs/storage/faqs-storage-changes-announced-sept-2024) before changing billing.

## Run locally

Keep the frontend and backend in separate PowerShell windows.

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app
```

The frontend runs at `http://localhost:5173/`; the API docs run at `http://127.0.0.1:8000/docs`.

The local Firebase client settings are in `frontend/.env.local`, which is excluded by `.gitignore`. Do not commit private service-account keys. The Firebase web config is public client configuration; protect data with Firebase Security Rules.

## Current limitations and next work

- The plan engine uses fixed sample ideas, a local ingredient catalog, and allergen tags. It removes matching menu items and flags avoid-food entries with no exact catalog match for review. It does not calculate calories, portions, nutrition, or cost, and it cannot check product labels, recipe variations, incomplete ingredient data, or kitchen cross-contact. Plans are not a guarantee of allergen safety.
- The API currently accepts requests without verifying Firebase ID tokens. Keep it local/demo-only until backend authentication is added before deployment.
- The plan-history screen displays the latest ten saved plans for the signed-in user.
- Allergy terms outside the planner's supported alias list stop generation rather than being silently ignored.
- Add authenticated backend requests, automated tests, deployment instructions, screenshots, and interview documentation before presenting the project as production-ready.
