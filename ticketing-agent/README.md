# ⚔️ Cavaleiro Capa Preta — Rio Branco ES Ticketing Agent

> A production-ready LangGraph RAG chatbot for the **Rio Branco Esporte Clube** website.  
> The agent answers fan questions using semantic search over the club's website content,  
> captures commercial leads into PostgreSQL, and persists full conversation history per session.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM | OpenAI `gpt-4.1-mini` (configurable) |
| Vector store | [ChromaDB](https://www.trychroma.com/) |
| Embeddings | OpenAI `text-embedding-3-large` |
| API server | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Conversation memory | PostgreSQL via `langgraph-checkpoint-postgres` |
| Lead capture | PostgreSQL via `psycopg2` |
| Frontend | Vanilla HTML/CSS/JS (served by FastAPI) |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                 │
│  GET /demo → Chat UI (index.html)                               │
│  POST /agent/chat → { session_id, message }                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   FastAPI   │  react_agent/app.py
                    │  + lifespan │  (CORS, static files, Jinja2)
                    └──────┬──────┘
                           │
                    ┌──────▼──────────────────────────────────────┐
                    │           LangGraph Agent Graph             │
                    │                                             │
                    │  START                                      │
                    │    │                                        │
                    │  route_start()                              │
                    │    ├─ (empty) ──► greeting_node ──► END     │
                    │    └─ (message) ──► call_model_node         │
                    │                         │                   │
                    │                   route_model_output()      │
                    │                         ├─ tool_calls ──►   │
                    │                         │   tools_node      │
                    │                         │       │           │
                    │                         │  call_model_node  │
                    │                         └─ done ──► END     │
                    └─────────────────────────────────────────────┘
                           │                    │
              ┌────────────▼───┐     ┌──────────▼──────────┐
              │  PostgreSQL    │     │      ChromaDB        │
              │  Checkpointer  │     │  riobranco_pages     │
              │  (conv. memory)│     │  (website embeddings)│
              └────────────────┘     └─────────────────────-┘
                           │
              ┌────────────▼───┐
              │  PostgreSQL    │
              │  leads table   │
              │ (captured leads)│
              └────────────────┘
```

### Agent Nodes

| Node | Trigger | Behaviour |
|---|---|---|
| `greeting_node` | First message is empty | Returns a hardcoded welcome message in Portuguese |
| `call_model_node` | Every user message | Invokes GPT-4.1-mini with tools bound + system prompt |
| `tools_node` | LLM requests a tool call | Executes `search_website` or `collect_customer_info` |

### Tools

| Tool | Description |
|---|---|
| `search_website(query)` | Semantic search over ChromaDB `riobranco_pages` collection — returns top 3 results with Title, Content snippet, URL |
| `collect_customer_info(name, email, phone?, address?)` | Inserts a lead row into the PostgreSQL `leads` table |

---

## Project Structure

```
ticketing-agent/
│
├── react_agent/                   # Main Python package
│   ├── __init__.py
│   ├── app.py                     # FastAPI app + lifespan (PostgresSaver init)
│   ├── graph.py                   # LangGraph StateGraph (nodes + edges)
│   ├── state.py                   # InputState / State TypedDicts
│   ├── configuration.py           # Dataclass: model, system_prompt
│   ├── prompts.py                 # SYSTEM_PROMPT for Cavaleiro Capa Preta
│   ├── tools.py                   # search_website + collect_customer_info
│   ├── utils.py                   # load_chat_model() helper
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── chat.py                # POST /agent/chat endpoint
│   │
│   └── templates/
│       └── index.html             # Chat UI (served at GET /demo)
│
├── scripts/
│   ├── __init__.py
│   ├── chroma_client.py           # get_chroma_client() helper
│   ├── load_to_chroma.py          # Ingest pages_with_metadata.csv → ChromaDB
│   └── create_leads_table.py      # Create PostgreSQL leads table
│
├── static/                        # Images served at /static/*
│   ├── mascot1.png
│   ├── stadium1.jpeg … stadium6.jpg
│   └── …
│
├── pages_with_metadata.csv        # Source data for ChromaDB ingestion
├── pyproject.toml                 # Project dependencies
├── .env.example                   # Environment variable template
├── .gitignore
└── README.md
```

---

## Prerequisites

- **Python** ≥ 3.11
- **PostgreSQL** ≥ 14 (running locally or remote)
- **ChromaDB** server (running locally or remote)
- **OpenAI API key** with access to `gpt-4.1-mini` and `text-embedding-3-large`

---

## Local Setup

### 1. Clone & enter the project

```bash
git clone <your-repo-url>
cd ticketing-agent
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 3. Install the package and dependencies

```bash
pip install -e .
# For development extras (pytest, black, mypy):
pip install -e ".[dev]"
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```dotenv
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...   # optional — only needed if switching to Claude
DATABASE_URL=postgresql://user:password@localhost:5432/riobranco
CHROMA_URL=http://localhost:8001
```

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | Used for LLM calls and embeddings |
| `ANTHROPIC_API_KEY` | ❌ | Only needed if using `anthropic/claude-*` models |
| `DATABASE_URL` | ✅ | PostgreSQL connection string for conversation history + leads |
| `CHROMA_URL` | ✅ | ChromaDB HTTP server URL |

---

## Database Setup

### PostgreSQL — Create the database

```bash
createdb riobranco
# or via psql:
psql -c "CREATE DATABASE riobranco;"
```

### Create the leads table

```bash
python scripts/create_leads_table.py
```

This creates the `leads` table with columns: `id`, `name`, `email` (unique), `phone`, `address`, `created_at`.

> The LangGraph checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) are created automatically on first server startup via `checkpointer.setup()`.

---

## Load Data to ChromaDB

Start your ChromaDB server first:

```bash
chroma run --host 0.0.0.0 --port 8001
```

Then ingest the website content:

```bash
python scripts/load_to_chroma.py
```

This reads `pages_with_metadata.csv`, generates embeddings using `text-embedding-3-large`, and upserts documents into the `riobranco_pages` collection.

---

## Run the Server

### Development (with auto-reload)

```bash
uvicorn react_agent.app:app --reload --host 0.0.0.0 --port 8000
```

### Verify it's running

```bash
curl http://localhost:8000/health
# → {"status":"ok","agent":"Cavaleiro Capa Preta"}
```

### Open the Chat UI

Navigate to: **http://localhost:8000/demo**

---

## API Reference

### `POST /agent/chat`

Invoke the agent for a given session.

**Request**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Quais são os próximos jogos do Rio Branco?"
}
```

| Field | Type | Description |
|---|---|---|
| `session_id` | `string` | Unique identifier for the conversation (used as `thread_id` for checkpointing) |
| `message` | `string` | The user's message. Send `""` (empty string) to trigger the greeting. |

**Response**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    { "role": "human",  "content": "Quais são os próximos jogos do Rio Branco?" },
    { "role": "tool",   "content": "Título: Jogos...\nURL: ...", "tool_call_id": "..." },
    { "role": "ai",     "content": "Os próximos jogos do Rio Branco são..." }
  ]
}
```

The `messages` array contains the **full updated conversation history** for the session, including any intermediate tool messages.

### `GET /demo`

Serves the full-featured chat UI (`templates/index.html`).

### `GET /health`

Liveness probe — returns `{"status": "ok"}`.

---

## Customising the Agent

### Switch LLM model

Pass a different model in the request config (via LangGraph's `RunnableConfig`), or change the default in `react_agent/configuration.py`:

```python
model: str = "openai/gpt-4.1-mini"   # change to e.g. "anthropic/claude-3-5-sonnet"
```

The format is `"provider/model-name"` — `load_chat_model()` in `utils.py` splits this automatically.

### Edit the system prompt

Open `react_agent/prompts.py` and modify `SYSTEM_PROMPT`.

---

## Deployment Guide

### Production server

Run with multiple workers and without auto-reload:

```bash
uvicorn react_agent.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --no-access-log
```

### Environment variables in production

Never commit `.env`. Inject variables via your platform:

```bash
# Example — systemd or Docker
export OPENAI_API_KEY="sk-..."
export DATABASE_URL="postgresql://..."
export CHROMA_URL="http://chroma:8001"
```

### Reverse proxy (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 120s;   # agent may take time on tool calls
    }
}
```

### Docker (quick example)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8000
CMD ["uvicorn", "react_agent.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

```bash
docker build -t cavaleiro-agent .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e DATABASE_URL=$DATABASE_URL \
  -e CHROMA_URL=$CHROMA_URL \
  cavaleiro-agent
```

---

## Module Markers (`__init__.py`)

All packages have their module markers in place:

| File | Status |
|---|---|
| `react_agent/__init__.py` | ✅ |
| `react_agent/api/__init__.py` | ✅ |
| `scripts/__init__.py` | ✅ |

---

*Rio Branco Esporte Clube — O Maior do Espírito Santo* ⚔️🖤🤍
