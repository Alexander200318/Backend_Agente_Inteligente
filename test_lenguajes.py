from database.database import SessionLocal
from models.unidad_contenido import UnidadContenido
from rag.rag_service import RAGService

db = SessionLocal()

# Buscar documentos sobre lenguajes
print("Documentos en BD con 'lenguajes':")
docs_bd = db.query(UnidadContenido).filter(UnidadContenido.contenido.ilike('%lenguajes%')).all()
print(f"Encontrados: {len(docs_bd)}")
for doc in docs_bd:
    print(f"  ID {doc.id_contenido}: {doc.titulo[:60]}")
    print(f"    Estado: {doc.estado}")
    print()

# Buscar en RAG
rag = RAGService(db)
print("\nBusqueda RAG con 'lenguajes de programacion':")
docs_rag = rag.search(id_agente=1, query='lenguajes de programacion', incluir_inactivos=False)
print(f"Encontrados: {len(docs_rag)}")
for doc in docs_rag:
    meta = doc.get('metadata', {})
    print(f"  - {doc.get('document', '')[:80]}...")
    print(f"    ID Contenido: {meta.get('id_contenido')}")

db.close()
