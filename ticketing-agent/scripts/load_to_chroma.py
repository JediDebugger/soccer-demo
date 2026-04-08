"""Load pages_with_metadata.csv into ChromaDB using text-embedding-3-large embeddings."""

import os
from pathlib import Path

import pandas as pd
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv
from tqdm import tqdm

from scripts.chroma_client import get_chroma_client, get_or_create_collection

load_dotenv()

# --- Configuration ---
CSV_PATH = Path(__file__).parent.parent / "pages_with_metadata.csv"
COLLECTION_NAME = "riobranco_pages"
BATCH_SIZE = 50
EMBED_MODEL = "text-embedding-3-large"


def load_csv(path: Path) -> pd.DataFrame:
    """Load and return the pages CSV."""
    print(f"📄 Loading CSV from: {path}")
    df = pd.read_csv(path)
    print(f"   Total rows: {len(df)}")
    return df


def build_embedding_function() -> OpenAIEmbeddingFunction:
    """Build the OpenAI embedding function using text-embedding-3-large."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in environment variables.")
    return OpenAIEmbeddingFunction(api_key=api_key, model_name=EMBED_MODEL)


def load_to_chroma(df: pd.DataFrame) -> None:
    """Embed and load documents into ChromaDB in batches."""
    # Connect to ChromaDB and get collection
    client = get_chroma_client()
    embedding_fn = build_embedding_function()
    collection = get_or_create_collection(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )

    # Filter out rows with empty text_content
    total_rows = len(df)
    df_valid = df[df["text_content"].notna() & (df["text_content"].str.strip() != "")]
    skipped = total_rows - len(df_valid)

    print(f"\n🚀 Loading {len(df_valid)} documents into '{COLLECTION_NAME}' "
          f"(batch size: {BATCH_SIZE}, skipped: {skipped} empty rows)...\n")

    added = 0
    batches = [df_valid.iloc[i:i + BATCH_SIZE] for i in range(0, len(df_valid), BATCH_SIZE)]

    for batch in tqdm(batches, desc="Uploading batches"):
        ids = batch["id"].astype(str).tolist()
        documents = batch["text_content"].tolist()
        metadatas = [
            {
                "url": str(row.get("url", "")),
                "english_title": str(row.get("english_title", "")),
                "english_description": str(row.get("english_description", "")),
                "crawled_at": str(row.get("crawled_at", "")),
            }
            for _, row in batch.iterrows()
        ]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        added += len(ids)

    # Final summary
    final_count = collection.count()
    print("\n=== Load Summary ===")
    print(f"Total rows:    {total_rows}")
    print(f"Added:         {added}")
    print(f"Skipped:       {skipped}")
    print(f"Final count:   {final_count} docs in collection '{COLLECTION_NAME}'")


def main() -> None:
    df = load_csv(CSV_PATH)
    load_to_chroma(df)


if __name__ == "__main__":
    main()
