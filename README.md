# 🧠 AI Knowledge Hub

**AI-Powered Enterprise Knowledge Hub & RAG Query Resolution Platform**
*B.Tech Final Year Project*

---

## Overview

A monorepo for an enterprise RAG (Retrieval-Augmented Generation) platform. The
FastAPI backend provides JWT authentication, role-based workspace access, PDF/
Markdown/text ingestion with Gemini embeddings, pgvector retrieval, persisted
conversations, and grounded streamed answers from Gemini or Groq. The React
frontend uses those APIs for authentication, workspace onboarding, analytics,
document management, chat, conversation history, team management, and workspace
settings.

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11+ |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic 1.13 |
| Database | PostgreSQL 15+ with pgvector (local machine verified on PostgreSQL 18 / pgvector 0.8.7) |
| Config | Pydantic Settings (.env) |
| Frontend | React 19 + Vite 8 + Tailwind CSS 3 |
| Language | TypeScript |

---

## Project Structure

```
PROJECT2/
├── .github/workflows/ci.yml # Backend and frontend checks on pushes and PRs
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app factory + CORS + lifespan
│   │   ├── config.py         # Pydantic Settings — reads .env
│   │   ├── database.py       # Async SQLAlchemy engine + session + get_db()
│   │   ├── core/             # Password hashing, JWT, authorization, API errors
│   │   ├── models/           # Auth, workspace, document, and conversation models
│   │   ├── routers/          # Health, auth, workspace, document, and RAG APIs
│   │   ├── services/         # Ingestion, Gemini embeddings, and RAG
│   │   └── schemas/          # Validated API request and response models
│   ├── alembic/
│   │   ├── env.py            # Async migration environment
│   │   ├── script.py.mako    # Migration file template
│   │   └── versions/         # Auth, document, and RAG migrations
│   ├── alembic.ini           # Alembic config
│   ├── requirements.txt      # Python dependencies (pinned)
│   ├── requirements-test.txt # Test dependencies
│   ├── tests/                # Auth, ingestion, RAG, and tenant isolation tests
│   ├── .env.example          # Template — safe to commit
│   └── .env                  # Real secrets — git-ignored
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx          # React entry point
│   │   ├── auth/             # Login/register and shared session/workspace state
│   │   ├── api/              # Typed API client
│   │   ├── components/       # Workspace navigation and shared UI
│   │   └── pages/            # Dashboard, documents, chat, team, and settings
│   ├── index.html            # SEO-ready HTML shell
│   ├── tailwind.config.js    # Custom color palette + animations
│   ├── postcss.config.js     # PostCSS + autoprefixer
│   ├── tsconfig.json         # TypeScript config
│   ├── vite.config.ts        # Vite config
│   └── .env.example          # VITE_API_BASE_URL template
│
├── .gitignore
└── README.md
```

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | [python.org](https://www.python.org) |
| PostgreSQL | 15+ | [postgresql.org](https://www.postgresql.org) |
| pgvector | latest | See below |
| Node.js | 22+ | [nodejs.org](https://nodejs.org) |

### Install pgvector in PostgreSQL

```sql
-- Run in psql as superuser
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux

# 6. Edit .env — update DATABASE_URL with your PostgreSQL credentials
notepad .env

# 7. Generate a unique JWT secret and set SECRET_KEY in backend/.env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Create the Database

```sql
-- In psql:
CREATE DATABASE knowledge_hub;
\c knowledge_hub
CREATE EXTENSION IF NOT EXISTS vector;
```

### Run Migrations

```bash
# Apply authentication, document, and RAG migrations
alembic upgrade head

# Check migration status
alembic current
```

### Start the Backend

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:
- **Swagger UI** → http://localhost:8000/docs
- **ReDoc** → http://localhost:8000/redoc
- **Health check** → http://localhost:8000/api/v1/health

---

## Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Configure environment (optional)
copy .env.example .env.local    # Windows
# cp .env.example .env.local   # macOS/Linux

# 4. Start dev server (explicit IPv4 host works consistently on Windows)
npm run dev -- --host 127.0.0.1
```

Open **http://127.0.0.1:5173**, register or sign in, and create/select a workspace.
The browser session stores the access token in `sessionStorage`; sign out clears it.
Set `VITE_API_BASE_URL` in `frontend/.env.local` if the backend is not at
`http://localhost:8000`.

The backend CORS defaults permit both `localhost` and `127.0.0.1` for the
development frontend. If login/register reports a network error, confirm
`http://127.0.0.1:8000/api/v1/health` responds and that the frontend origin is
included in `CORS_ORIGINS`, then restart the API after changing `backend/.env`.

```bash
# Production frontend build
npm run build
```

### Frontend capabilities and limits

- Registration/login and workspace onboarding use the real authentication and workspace APIs.
- Dashboard counts are workspace-scoped database aggregates. Document processing status refreshes while a document is pending/processing.
- Document previews display extracted text chunks. Original upload bytes are not retained by the backend, so original-file rendering/download is not available.
- Chat uses the authenticated SSE endpoint; conversations and validated source citations are persisted and displayed.
- Team management adds an already-registered user by email. The backend does not send invitation emails.
- Workspace settings currently support name and description only. AI provider credentials must be configured on the backend, not in the browser.
- Support tickets, notification preferences, 2FA, audit logs, billing, and workspace deletion are not implemented by the backend; the UI does not display placeholder records or claim those actions work.

### AI provider setup

Configure `GEMINI_API_KEY` for Gemini embeddings and, depending on
`RAG_LLM_PROVIDER`, configure either `GEMINI_API_KEY` or `GROQ_API_KEY` for
answer generation. Set `RAG_LLM_PROVIDER`, `GEMINI_MODEL`, `GROQ_MODEL`,
`RAG_TOP_K`, and `RAG_RELEVANCE_THRESHOLD` in `backend/.env`, then restart the
backend. Do not put these provider keys in frontend variables.

### Integration checks

```powershell
# Backend tests
cd backend
.\.venv\Scripts\python.exe -m pytest -q tests

# Frontend type-check and build
cd ..\frontend
npm run build
npm run lint
```

Live answer generation requires valid provider credentials and outbound network
access. This repository is currently set up for local development and testing;
Render deployment configuration will be added separately when you are ready to
deploy.

---

## API Reference

The frontend expects the backend at the configured `VITE_API_BASE_URL`. Protected
requests send the JWT as a Bearer token. Workspace selection never grants access
by itself: the API checks current membership and role for every protected call.

### `GET /api/v1/health`

Liveness probe — returns HTTP 200 when the service is running.

**Response:**
```json
{
  "status": "ok",
  "app_name": "AI Knowledge Hub",
  "version": "0.1.0",
  "environment": "development"
}
```

---

### Authentication

Passwords are bcrypt-hashed. The API returns bearer JWTs; send them in
`Authorization: Bearer <access_token>`. Registration does not create a
workspace. A user who creates a workspace becomes its first Admin.

| Method | Endpoint | Access |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Public |
| `POST` | `/api/v1/auth/login` | Public |
| `GET` | `/api/v1/auth/me` | Authenticated |

Register and log in:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alex@example.com","password":"correct-horse-battery","full_name":"Alex"}'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alex@example.com","password":"correct-horse-battery"}'
```

Copy `access_token` from the login response into `TOKEN` in the examples below.

### Workspaces and membership

All workspace operations validate the caller's active membership in that
workspace. A caller who is not a member receives `404` so workspace existence
is not disclosed. All members can view workspace details and the member list.
Only Admins can add, change, or remove members. The workspace owner must remain
an Admin, and every workspace must retain an active Admin.

| Method | Endpoint | Access |
|---|---|---|
| `POST` | `/api/v1/workspaces` | Authenticated; creator becomes Admin |
| `GET` | `/api/v1/workspaces` | Authenticated; lists caller's workspaces |
| `GET` | `/api/v1/workspaces/{workspace_id}` | Active workspace member |
| `GET` | `/api/v1/workspaces/{workspace_id}/members` | Active workspace member |
| `GET` | `/api/v1/workspaces/{workspace_id}/analytics` | Active workspace member |
| `PATCH` | `/api/v1/workspaces/{workspace_id}` | Workspace Admin |
| `POST` | `/api/v1/workspaces/{workspace_id}/members` | Workspace Admin |
| `PATCH` | `/api/v1/workspaces/{workspace_id}/members/{user_id}` | Workspace Admin |
| `DELETE` | `/api/v1/workspaces/{workspace_id}/members/{user_id}` | Workspace Admin |

Membership roles are `admin`, `support_agent`, and `user`. Support Agents and
Users can access member-visible workspace operations; membership administration
and workspace settings are restricted to Admin. Add a registered user by email:

```bash
curl -X POST http://localhost:8000/api/v1/workspaces \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Engineering","description":"Engineering team"}'

curl -X POST http://localhost:8000/api/v1/workspaces/1/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"teammate@example.com","role":"support_agent"}'

curl -X PATCH http://localhost:8000/api/v1/workspaces/1/members/2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role":"user"}'

curl -X DELETE http://localhost:8000/api/v1/workspaces/1/members/2 \
  -H "Authorization: Bearer $TOKEN"
```

Open **http://localhost:8000/docs** to exercise each endpoint interactively:
register and log in, click **Authorize**, paste the `access_token` value, then
invoke workspace routes with the returned workspace and user IDs. Errors use
an `error` object with a stable `code` and safe `message`; validation errors
also include field locations.

### Backend tests

Install test dependencies after the backend requirements and run the backend
tests (they use an in-memory SQLite database):

```bash
cd backend
pip install -r requirements-test.txt
pytest
```

The tests cover authentication, workspace roles and tenant isolation, document
uploads and parsing, Gemini embedding task selection, RAG retrieval and
citations, conversation history, and access controls.

### Document management and ingestion

Run `alembic upgrade head` after configuring PostgreSQL. The database must have
the pgvector extension installed; create it as a PostgreSQL administrator if
needed:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The API accepts `.pdf`, `.md`, `.markdown`, and `.txt` files up to the
configured size limit. Text is split into overlapping character-based chunks.
PDF chunks include their one-based page number; Markdown and text chunks have
no page number. Each chunk stores its zero-based index and a 1536-dimensional
pgvector embedding. Uploads return `202 Accepted` with `pending`; check the
document details endpoint for `processing`, `completed`, or `failed`.

Document and question embeddings use Gemini's `models/gemini-embedding-001`
with 1536 output dimensions and matching retrieval task types. Set
`GEMINI_API_KEY` and, if needed, `EMBEDDING_MODEL` in `backend/.env`. The
embedding model is recorded per document; only documents embedded with the
current model are searched, so documents previously embedded with a different
model must be re-ingested before retrieval. The original upload is processed
in the background and is not retained after ingestion.

Answer generation is selectable with `RAG_LLM_PROVIDER=gemini` or `groq`.
Gemini uses `GEMINI_API_KEY` and `GEMINI_MODEL`; Groq uses `GROQ_API_KEY` and
`GROQ_MODEL`. Configure `RAG_TOP_K`, `RAG_RELEVANCE_THRESHOLD`,
`RAG_MAX_CONTEXT_CHARS`, and `RAG_IVFFLAT_PROBES` to tune retrieval.

### Workspace RAG and conversations

| Method | Endpoint | Access |
|---|---|---|
| `POST` | `/api/v1/workspaces/{workspace_id}/ask` | Active workspace member |
| `POST` | `/api/v1/workspaces/{workspace_id}/ask/stream` | Active workspace member |
| `GET` | `/api/v1/workspaces/{workspace_id}/conversations` | Owner of conversation and active workspace member |
| `GET` | `/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}` | Owner of conversation and active workspace member |

Ask a question with no `conversation_id` to create a persisted conversation;
send the returned ID on subsequent turns. The response contains the answer,
whether context was insufficient, and citations with actual document names,
page numbers (when known), chunk indexes, excerpts, and similarity scores.
Invalid or missing model citations are discarded and result in the safe
insufficient-context answer. Conversation history is private to its creator,
even for other members of the same workspace.

```json
{
  "question": "What does the policy say about password rotation?",
  "conversation_id": null
}
```

Retrieved chunks are filtered by the authenticated workspace, completion status,
current embedding model, cosine similarity threshold, and configured top-k. The
system prompt treats the question and document excerpts as untrusted data and
instructs the LLM to ignore embedded instructions. Answers must cite retrieved
source IDs; the API only resolves citation IDs to chunks actually retrieved for
that workspace. If no chunks pass the relevance threshold, the API returns an
uncertainty response without asking the LLM.

The streaming endpoint uses real provider token streams (no artificial delays)
and emits SSE `conversation`, `text`, `citations`, `error`, and `complete` events.
It persists the user turn before streaming and persists exactly one assistant
turn after a complete, validated response. Provider failures save a generic
failure turn; client disconnects close the provider stream and do not save partial
assistant output. Follow-up questions include the owning conversation's recent
history.

To test the complete flow in Swagger UI:

1. Set `GEMINI_API_KEY` in `backend/.env`, apply migrations, and start the API.
   This key is used for document and question embeddings even when Groq is
   selected for answer generation.
2. Register and log in, create a workspace, and upload a PDF, Markdown, or
   plain-text document. Poll its details endpoint until `status` is `completed`.
3. Click **Authorize** in Swagger UI and enter the login access token.
4. Open **POST `/api/v1/workspaces/{workspace_id}/ask`**, enter the workspace
   ID, and submit the question JSON above. To continue that conversation, set
   `conversation_id` to the ID from the response.
5. Inspect the `answer`, `insufficient_context`, and `citations` fields. Use the
   conversation list and detail endpoints to view persisted messages.

Set `RAG_LLM_PROVIDER=groq` and `GROQ_API_KEY` to use Groq for answer generation;
Gemini remains the embedding provider.

### React streaming chat

Sign in through the frontend and select a workspace; the chat page uses the
shared session and streams actual API responses with citations and status
indicators. Conversation history is scoped to its owner and workspace.

| Method | Endpoint | Access |
|---|---|---|
| `POST` | `/api/v1/workspaces/{workspace_id}/documents` | Workspace Admin or Support Agent |
| `GET` | `/api/v1/workspaces/{workspace_id}/documents` | Active workspace member |
| `GET` | `/api/v1/workspaces/{workspace_id}/documents/{document_id}` | Active workspace member |
| `DELETE` | `/api/v1/workspaces/{workspace_id}/documents/{document_id}` | Workspace Admin or Support Agent |

To test an upload in Swagger UI:

1. Register/log in, click **Authorize**, and paste the `access_token` value. Swagger UI applies the Bearer scheme.
2. Create a workspace, or use a workspace where your role is Admin or Support Agent.
3. Open **POST `/api/v1/workspaces/{workspace_id}/documents`**, enter the workspace ID, choose a `.pdf`, `.md`, `.markdown`, or `.txt` file, and click **Execute**.
4. Use the returned document ID with **GET `/api/v1/workspaces/{workspace_id}/documents/{document_id}`** to inspect its status and extracted chunks. The response does not include embeddings.
5. Use **GET `/api/v1/workspaces/{workspace_id}/documents`** to list documents or **DELETE** on a document to delete it and its chunks.

Only active workspace members can list or read documents. A non-member receives
`404`; a workspace `user` role receives `403` when uploading or deleting.
Unsupported extensions return `415`; oversized files return `413`. Parse and
provider failures are recorded on the document with status `failed` and a
non-sensitive error code/message.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `"AI Knowledge Hub"` | Application display name |
| `APP_VERSION` | `"0.1.0"` | Semantic version |
| `ENVIRONMENT` | `development` | Application environment label |
| `DEBUG` | `true` | Enable SQL query logging |
| `DATABASE_URL` | *(see example)* | `postgresql+asyncpg://user:pass@host/db` |
| `API_V1_PREFIX` | `/api/v1` | Base path for all API routes |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated allowed origins |
| `SECRET_KEY` | *(required)* | Unique JWT signing secret; generate a random value before starting |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access-token lifetime |
| `MAX_DOCUMENT_SIZE_MB` | `10` | Maximum upload size in megabytes (1–100) |
| `MAX_EXTRACTED_TEXT_CHARS` | `5000000` | Maximum extracted characters per document |
| `DOCUMENT_CHUNK_SIZE` | `1200` | Chunk size in characters |
| `DOCUMENT_CHUNK_OVERLAP` | `200` | Overlap between adjacent chunks |
| `EMBEDDING_MODEL` | `models/gemini-embedding-001` | Gemini model producing 1536-dimensional vectors |
| `RAG_LLM_PROVIDER` | `gemini` | `gemini` or `groq` answer-generation provider |
| `RAG_TOP_K` | `5` | Maximum retrieved chunks |
| `RAG_RELEVANCE_THRESHOLD` | `0.35` | Minimum cosine similarity (0–1) |
| `RAG_MAX_CONTEXT_CHARS` | `16000` | Maximum document-excerpt characters included in the LLM prompt |
| `RAG_IVFFLAT_PROBES` | `10` | pgvector IVFFlat lists searched |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

---

## Development Roadmap

| Phase | Feature | Status |
|---|---|---|
| **1** | Project Foundation (this) | ✅ Done |
| **2** | Authentication & RBAC | ✅ Done |
| **3** | Document Upload & Processing | ✅ Done |
| **4** | RAG / pgvector Semantic Search | ✅ Done |
| **5** | AI Answer Generation (Gemini/Groq) | ✅ Done |

---

## Common Commands

```bash
# Backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
alembic revision --autogenerate -m ""  # Generate migration
alembic upgrade head                   # Apply all migrations
alembic downgrade -1                   # Roll back last migration
alembic history                        # Show migration history

# Frontend
npm run dev -- --host 127.0.0.1  # Start dev server (http://127.0.0.1:5173)
npm run build      # Build for production
npm run preview    # Preview the production build locally
npm run lint       # Run ESLint
```

---

## Notes

- **Tailwind CSS 3** audit warnings: These are in dev-only dependencies and are **not shipped** to production. Safe to ignore for development.
- **No real secrets** are committed. The `.env` file is in `.gitignore`.
- Alembic will fail to connect until you configure a real PostgreSQL database in `.env` — this is expected.
