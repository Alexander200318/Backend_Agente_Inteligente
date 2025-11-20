# rag/chroma_config.py
from chromadb import PersistentClient
from pathlib import Path

_chroma_instance = None


class ChromaDBConfig:
    def __init__(self, persist_directory: str = "vectorstore/chroma"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.client = PersistentClient(path=str(self.persist_directory))

    def get_or_create_collection(self, name: str, metadata: dict = None):
        # Chroma 0.5+ exige metadata obligatoria
        safe_metadata = metadata or {"collection": name}

        return self.client.get_or_create_collection(
            name=name,
            metadata=safe_metadata
        )

    def list_collections(self):
        return self.client.list_collections()


def get_chroma_client():
    global _chroma_instance
    if _chroma_instance is None:
        _chroma_instance = ChromaDBConfig()
    return _chroma_instance.client


def get_agent_collection(agent_id: int):
    global _chroma_instance
    if _chroma_instance is None:
        _chroma_instance = ChromaDBConfig()

    collection_name = f"agente_{agent_id}"
    return _chroma_instance.get_or_create_collection(
        collection_name,
        metadata={"agent_id": agent_id}
    )
