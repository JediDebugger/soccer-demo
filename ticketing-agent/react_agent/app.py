"""FastAPI application entry point for the Cavaleiro Capa Preta ticketing agent."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from langgraph.checkpoint.postgres import PostgresSaver

from react_agent.api.chat import router as chat_router
from react_agent.graph import workflow

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent  # ticketing-agent/
TEMPLATES_DIR = BASE_DIR / "react_agent" / "templates"
STATIC_DIR = BASE_DIR / "static"

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events.

    The PostgresSaver context manager is used correctly here so that:
    - A real PostgresSaver instance is created (not a generator object)
    - checkpointer.setup() runs once on startup to create the checkpoint tables
    - The connection is held open for the full server lifetime
    - The connection closes cleanly on shutdown
    """
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "")

    logger.info("🟢 Cavaleiro Capa Preta agent is starting up...")

    if database_url:
        with PostgresSaver.from_conn_string(database_url) as checkpointer:
            checkpointer.setup()  # creates langgraph checkpoint tables if needed
            app.state.graph = workflow.compile(checkpointer=checkpointer)
            app.state.graph.name = "CavaleiroCapePretoAgent"
            logger.info("✅ PostgreSQL checkpointer initialized. Conversation persistence active.")
            yield
        logger.info("🔴 PostgreSQL connection closed. Até logo!")
    else:
        # No DATABASE_URL — run without persistence (dev / testing)
        logger.warning("⚠️  DATABASE_URL not set. Running without conversation persistence.")
        app.state.graph = workflow.compile()
        app.state.graph.name = "CavaleiroCapePretoAgent"
        yield
        logger.info("🔴 Cavaleiro Capa Preta agent is shutting down. Até logo!")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Cavaleiro Capa Preta — Rio Branco Ticketing Agent",
    description="LangGraph RAG agent for the Rio Branco Esporte Clube website.",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------------------------
# Jinja2 Templates
# ---------------------------------------------------------------------------

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/demo", response_class=HTMLResponse, tags=["UI"])
async def demo(request: Request):
    """Serve the chat demo UI (index.html from templates/)."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health", tags=["Health"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "agent": "Cavaleiro Capa Preta"}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(chat_router, prefix="/agent", tags=["Chat"])
