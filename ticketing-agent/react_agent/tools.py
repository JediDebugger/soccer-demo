"""LangGraph tools for the Cavaleiro Capa Preta agent."""

import os
from typing import Optional

import psycopg2
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from langchain_core.tools import tool

from scripts.chroma_client import get_chroma_client, get_or_create_collection

# ---------------------------------------------------------------------------
# ChromaDB Singleton Pool
# ---------------------------------------------------------------------------

COLLECTION_NAME = "riobranco_pages"
_chroma_collection = None


def _get_collection():
    """Return a cached ChromaDB collection, initialising it on first call."""
    global _chroma_collection
    if _chroma_collection is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment variables.")
        embedding_fn = OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-large",
        )
        client = get_chroma_client()
        _chroma_collection = get_or_create_collection(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embedding_fn,
        )
    return _chroma_collection


# ---------------------------------------------------------------------------
# Tool: search_website
# ---------------------------------------------------------------------------


@tool
def search_website(query: str) -> str:
    """Search the Rio Branco official website using semantic similarity.

    Returns the top 3 most relevant pages with their title, a content
    snippet, and the source URL.

    Args:
        query: The search query in Portuguese.

    Returns:
        A formatted string with the top 3 results, or an error message.
    """
    try:
        collection = _get_collection()
        results = collection.query(query_texts=[query], n_results=3)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not documents:
            return "Nenhum resultado encontrado para a sua busca."

        formatted_results = []
        for doc, meta in zip(documents, metadatas):
            title = meta.get("english_title", "Sem título")
            url = meta.get("url", "URL não disponível")
            snippet = doc[:300].strip().replace("\n", " ")
            if len(doc) > 300:
                snippet += "..."
            formatted_results.append(
                f"Título: {title}\nConteúdo: {snippet}\nURL: {url}"
            )

        return "\n\n---\n\n".join(formatted_results)

    except Exception as e:
        return f"Erro ao buscar informações no site: {str(e)}"


# ---------------------------------------------------------------------------
# Tool: collect_customer_info
# ---------------------------------------------------------------------------


@tool
def collect_customer_info(
    name: str,
    email: str,
    phone: Optional[str] = None,
    address: Optional[str] = None,
) -> str:
    """Save a customer lead into the PostgreSQL leads table.

    Collects contact information from users interested in sponsorship,
    commercial partnerships, membership, or any other club-related enquiries.

    Args:
        name: Full name of the customer (required).
        email: Email address of the customer (required, must be unique).
        phone: Phone number (optional).
        address: Postal address (optional).

    Returns:
        A confirmation message or an error description.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return "Erro de configuração: DATABASE_URL não definida no ambiente."

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO leads (name, email, phone, address)
            VALUES (%s, %s, %s, %s)
            """,
            (name, email, phone or None, address or None),
        )
        conn.commit()
        return (
            f"Contato registrado com sucesso! Obrigado, {name}. "
            "Nossa equipe entrará em contato em breve."
        )

    except psycopg2.errors.UniqueViolation:
        return (
            f"O e-mail '{email}' já está registrado em nosso banco de dados. "
            "Nossa equipe já tem o seu contato!"
        )
    except psycopg2.Error as e:
        return f"Erro ao salvar contato no banco de dados: {str(e)}"
    except Exception as e:
        return f"Erro inesperado ao registrar contato: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Tools list — import this into graph.py to bind tools with the LLM
# ---------------------------------------------------------------------------

tools = [search_website, collect_customer_info]
