"""ChromaDB client utilities for local Docker testing and production."""

import os
from typing import Optional
from urllib.parse import urlparse

import chromadb
from chromadb.api.types import EmbeddingFunction


def get_chroma_client() -> chromadb.HttpClient:
    """Create and return a ChromaDB HTTP client.

    Reads CHROMA_URL from environment with fallback to http://localhost:8000.
    Tests the connection via heartbeat() before returning.

    Returns:
        Connected ChromaDB HttpClient instance

    Raises:
        Exception: If the connection to ChromaDB fails
    """
    chroma_url = os.getenv("CHROMA_URL", "http://localhost:8000")

    parsed = urlparse(chroma_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8000

    client = chromadb.HttpClient(host=host, port=port)

    try:
        client.heartbeat()
        print(f"✅ Connected to ChromaDB at {chroma_url}")
    except Exception as e:
        print(f"❌ Failed to connect to ChromaDB at {chroma_url}: {e}")
        raise

    return client


def get_or_create_collection(
    client: chromadb.HttpClient,
    collection_name: str,
    embedding_function: Optional[EmbeddingFunction] = None,
) -> chromadb.Collection:
    """Get an existing ChromaDB collection or create it if it doesn't exist.

    Args:
        client: Connected ChromaDB HttpClient instance
        collection_name: Name of the collection to get or create
        embedding_function: Optional embedding function (e.g., OpenAI embeddings).
                            Uses ChromaDB default if not provided.

    Returns:
        ChromaDB Collection instance
    """
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
    )
    print(f"✅ Collection '{collection_name}' ready")
    return collection
