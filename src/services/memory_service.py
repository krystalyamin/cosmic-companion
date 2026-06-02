"""
Persistent conversation and session memory using ChromaDB.
"""

import json
import uuid
from datetime import datetime, timezone

import chromadb
from chromadb.config import Settings


# ============================================================
# Configuration
# ============================================================

CHROMA_DB_PATH = "./chroma_db"

CHAT_COLLECTION_NAME = "chat_messages"
SESSION_COLLECTION_NAME = "session_data"


# ============================================================
# ChromaDB Client
# ============================================================

_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)


# ============================================================
# Collection Setup
# ============================================================

def initialize_chat_collection():
    """
    Create or load the ChromaDB collection.

    Returns:
        ChromaDB collection instance.
    """
    return _client.get_or_create_collection(
        name=CHAT_COLLECTION_NAME
    )


def initialize_session_collection():
    """
    Create or load the session storage collection.

    Returns:
        ChromaDB collection instance.
    """
    return _client.get_or_create_collection(
        name=SESSION_COLLECTION_NAME
    )


# ============================================================
# Save Chat Message
# ============================================================

def save_chat_message(
    session_id: str,
    role: str,
    message: str,
    metadata: dict | None = None
) -> None:
    """
    Store a chat message in ChromaDB.
    """

    collection = initialize_chat_collection()

    metadata = metadata or {}

    metadata.update({
        "session_id": session_id,
        "role": role,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[message],
        metadatas=[metadata]
    )


# ============================================================
# Retrieve Conversation History
# ============================================================

def get_chat_history(
    session_id: str,
    limit: int = 20
) -> list:
    """
    Retrieve ordered conversation history.

    Returns:
        [
            {
                "role": "...",
                "message": "...",
                "timestamp": "..."
            }
        ]
    """

    collection = initialize_chat_collection()

    results = collection.get(
        where={"session_id": session_id},
        include=["documents", "metadatas"]
    )

    messages = []

    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    for document, metadata in zip(documents, metadatas):
        messages.append({
            "role": metadata.get("role"),
            "message": document,
            "timestamp": metadata.get("timestamp")
        })

    messages.sort(key=lambda x: x["timestamp"])

    return messages[-limit:]


# ============================================================
# Semantic Search
# ============================================================

def search_relevant_memories(
    session_id: str,
    query: str,
    top_k: int = 5
) -> list:
    """
    Retrieve semantically similar messages from the same session.
    """

    collection = initialize_chat_collection()

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"session_id": session_id}
    )

    memories = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    for document, metadata in zip(documents, metadatas):
        memories.append({
            "role": metadata.get("role"),
            "message": document,
            "timestamp": metadata.get("timestamp")
        })

    return memories


# ============================================================
# Save Session Configuration
# ============================================================

def save_session_data(
    session_id: str,
    session_data: dict
) -> None:
    """
    Persist stargazing session settings.
    """

    collection = initialize_session_collection()

    existing = collection.get(
        where={"session_id": session_id}
    )

    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    collection.add(
        ids=[session_id],
        documents=[json.dumps(session_data)],
        metadatas=[{
            "session_id": session_id,
            "saved_at": datetime.now(timezone.utc).isoformat()
        }]
    )


# ============================================================
# Load Session Configuration
# ============================================================

def load_session_data(
    session_id: str
) -> dict:
    """
    Retrieve previously saved observation settings.
    """

    collection = initialize_session_collection()

    result = collection.get(
        ids=[session_id]
    )

    documents = result.get("documents", [])

    if not documents:
        return {}

    try:
        return json.loads(documents[0])
    except json.JSONDecodeError:
        return {}


# ============================================================
# Delete Session (Optional Utility)
# ============================================================

def delete_session(
    session_id: str
) -> None:
    """
    Remove a session and all associated chat history.
    """

    chat_collection = initialize_chat_collection()
    session_collection = initialize_session_collection()

    chat_results = chat_collection.get(
        where={"session_id": session_id}
    )

    if chat_results["ids"]:
        chat_collection.delete(
            ids=chat_results["ids"]
        )

    session_collection.delete(
        ids=[session_id]
    )


# ============================================================
# Health Check
# ============================================================

def test_memory_connection() -> bool:
    """
    Verify ChromaDB functionality.
    """

    try:
        initialize_chat_collection()
        initialize_session_collection()
        return True
    except Exception:
        return False