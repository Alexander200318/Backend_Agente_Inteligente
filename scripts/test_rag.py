from rag.chroma_config import get_chroma_client, get_agent_collection

client = get_chroma_client()
collection = get_agent_collection(1)

collection.add(
    ids=["1"],
    documents=["hola este es un test"],
    metadatas=[{"tipo": "prueba"}]
)

print(collection.count())
print(client.list_collections())
