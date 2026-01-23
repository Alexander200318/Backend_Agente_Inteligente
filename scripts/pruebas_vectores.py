from database.database import SessionLocal
from rag.rag_service import RAGService

db = SessionLocal()
rag = RAGService(db)

# Reemplaza con tu ID de agente
id_agente = 6  # TU ID AQUÍ

# Buscar información (igual que hace el agente)
resultados = rag.search(
    id_agente=id_agente,
    query="Información general sobre la investigación aplicada y su importancia académica.",
    n_results=5,
    use_reranking=False,
    incluir_inactivos=True  # 🔥 IMPORTANTE
)

# Ver qué encuentra
for i, r in enumerate(resultados):
    print(f"\n--- Resultado {i+1} ---")
    print(f"ID: {r.get('id')}")
    print(f"Metadata: {r.get('metadata')}")
    print(f"Activo: {r.get('metadata', {}).get('activo')}")
    print(f"Score: {r.get('score')}")
    print(f"Documento: {r.get('document')[:200]}...")