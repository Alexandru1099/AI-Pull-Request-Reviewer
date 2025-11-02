## Repo-Aware AI Pull Request Reviewer

Phase 1: infrastructure scaffold for a repo-aware AI PR reviewer.  
This phase sets up a production-minded monorepo with a typed Next.js frontend and a FastAPI backend, plus Docker Compose and a Makefile for local orchestration. **No GitHub or AI logic is implemented yet.**

---

### Architecture

- **Monorepo layout**
  - `frontend/`: Next.js (App Router) + TypeScript + Tailwind, minimal landing page
  - `backend/`: FastAPI + Pydantic, `GET /health` endpoint
  - Root tooling: `docker-compose.yml`, `Makefile`, `.env.example`

- **Backend**
  - FastAPI app in `backend/app`
  - `GET /health` returns a typed JSON health object
  - Config managed via environment variables (`app/core/config.py`)

- **Frontend**
  - Entry page at `/` showing project title and description
  - Tailwind configured and ready for future shadcn/ui components
  - Global config via `src/lib/config.ts`

---

### Prerequisites

- Node.js 18+ (Node 20+ recommended)
- Yarn (or adapt commands for `npm`/`pnpm`)
- Python 3.11+
- Docker and Docker Compose (for containerised dev)

---

### Environment setup

From the repo root:

```bash
cp .env.example .env

cd backend
cp .env.example .env
cd ..

cd frontend
cp .env.example .env
cd ..
```

You can adjust ports and URLs in these `.env` files as needed.

---

### Backend: local development

Create a virtual environment and install dependencies:

```bash
cd backend

# Option A: using uv (if installed)
uv sync

# Option B: using venv + pip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the FastAPI server:

```bash
# From backend/
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify the health endpoint:

- Open `http://localhost:8000/health` in your browser, or
- Use curl:

  ```bash
  curl http://localhost:8000/health
  ```

Expected response (shape):

```json
{
  "status": "ok",
  "service": "repo-aware-reviewer-backend",
  "timestamp": "2026-03-17T00:00:00Z"
}
```

(Timestamp will vary.)

---

### Frontend: local development

Install dependencies and run dev server:

```bash
cd frontend
yarn install
yarn dev
```

Visit `http://localhost:3000` in your browser.

You should see the landing page titled:

> **Repo-Aware AI Pull Request Reviewer**

with a short description and a small checklist of what Phase 1 provides.

---

### Using Docker Compose

From the repo root:

```bash
# Build and start both services
make up
# or
docker-compose up --build
```

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000/health`

Stop services:

```bash
make down
# or
docker-compose down
```

Tail logs:

```bash
make logs
```

---

### Run commands summary

From repo root:

- **Frontend dev**: `make frontend-dev`
- **Backend dev**: `make backend-dev`
- **Compose up**: `make up`
- **Compose down**: `make down`
- **Compose logs**: `make logs`

---

### Verification checklist (Phase 1)

1. **Backend health**
   - [ ] Run `make backend-dev` (or `uvicorn app.main:app --reload` from `backend/`)
   - [ ] Visit `http://localhost:8000/health`
   - [ ] Confirm JSON with `"status": "ok"` and `"service": "repo-aware-reviewer-backend"`

2. **Frontend landing page**
   - [ ] Run `make frontend-dev` (or `yarn dev` from `frontend/`)
   - [ ] Visit `http://localhost:3000`
   - [ ] Confirm:
     - The title `Repo-Aware AI Pull Request Reviewer`
     - A short descriptive subtitle
     - A section describing Phase 1 readiness

3. **Docker Compose**
   - [ ] Run `make up`
   - [ ] Visit `http://localhost:8000/health` and `http://localhost:3000`
   - [ ] Confirm both services respond as above
   - [ ] Run `make down` to stop containers

---

### Future phases

Phase 1 intentionally **does not** implement:

- GitHub authentication or webhooks
- Pull request inspection or diff analysis
- Any AI or LLM calls

Those will be added in later phases on top of this scaffold.

---

### GitHub OAuth Security Notes

- GitHub OAuth uses the OAuth App flow with a signed `state` cookie to mitigate CSRF during callback handling.
- Session cookies are configured as `httpOnly`, `sameSite=lax`, and `secure` in production environments.
- GitHub access tokens are kept server-side only and are never returned to the frontend API payloads.
- Session state is currently stored in-memory on the backend process. This is acceptable for local development and a single-instance deployment, but it is not a durable multi-instance session store.
- Session expiry is enforced server-side through `AUTH_SESSION_TTL_SECONDS`.
- OAuth state expiry is enforced through `AUTH_STATE_TTL_SECONDS`.
- Secrets such as `GITHUB_CLIENT_SECRET` and `SESSION_SECRET` must be provided via environment variables.
- The current integration is read-oriented and intended for repository and pull request access only. It does not perform write actions on GitHub resources.
- Security assumptions and limitations:
  - a single backend instance owns the in-memory session state
  - logout and session expiration clear local session state only
  - rotating GitHub tokens or restarting the backend invalidates active sessions

# AI-Pull-Request-Reviewer
# AI-Pull-Request-Reviewer
