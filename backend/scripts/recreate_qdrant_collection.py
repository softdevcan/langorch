"""
Script to recreate Qdrant collection with correct vector dimensions
Run this when changing embedding providers with different dimensions
"""
import asyncio
import sys
import os
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    os.system("chcp 65001 > nul")

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.qdrant_client import qdrant_store
from app.core.config import settings
from qdrant_client.models import Distance


async def recreate_collection(vector_size: int = 768):
    """
    Recreate Qdrant collection with new vector dimensions

    Args:
        vector_size: Dimension of embedding vectors (768 for nomic-embed-text, 1536 for OpenAI)
    """
    print(f"[*] Recreating Qdrant collection: {settings.QDRANT_COLLECTION_NAME}")
    print(f"    Vector size: {vector_size}")
    print(f"    Qdrant: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    print()

    try:
        # Get client
        client = qdrant_store._ensure_client()

        # Check if collection exists
        collections = client.get_collections().collections
        collection_exists = any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections)

        if collection_exists:
            print(f"[!] Collection '{settings.QDRANT_COLLECTION_NAME}' already exists")

            # Get collection info
            collection_info = client.get_collection(settings.QDRANT_COLLECTION_NAME)
            current_size = collection_info.config.params.vectors.size
            point_count = collection_info.points_count

            print(f"    Current vector size: {current_size}")
            print(f"    Current point count: {point_count}")
            print()

            if current_size == vector_size:
                print(f"[+] Collection already has correct vector size ({vector_size})")
                return

            # Confirm deletion
            response = input(f"[?] Delete collection and recreate with vector size {vector_size}? (yes/no): ")
            if response.lower() != "yes":
                print("[-] Operation cancelled")
                return

            # Delete collection
            print(f"[*] Deleting collection '{settings.QDRANT_COLLECTION_NAME}'...")
            client.delete_collection(settings.QDRANT_COLLECTION_NAME)
            print(f"[+] Collection deleted")
            print()

        # Create new collection
        print(f"[*] Creating collection '{settings.QDRANT_COLLECTION_NAME}'...")
        success = await qdrant_store.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vector_size=vector_size,
            distance=Distance.COSINE,
        )

        if success:
            print(f"[+] Collection created successfully!")
            print(f"    Collection: {settings.QDRANT_COLLECTION_NAME}")
            print(f"    Vector size: {vector_size}")
            print(f"    Distance metric: COSINE")
            print()
            print("[+] Done! You can now upload documents with the new embedding model.")
        else:
            print(f"[-] Failed to create collection")

    except Exception as e:
        print(f"[-] Error: {e}")
        raise


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Recreate Qdrant collection with new vector dimensions"
    )
    parser.add_argument(
        "--vector-size",
        type=int,
        default=768,
        help="Vector dimension (768 for nomic-embed-text, 1536 for OpenAI, etc.)",
    )

    args = parser.parse_args()

    await recreate_collection(vector_size=args.vector_size)


if __name__ == "__main__":
    asyncio.run(main())
