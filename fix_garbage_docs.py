from database.database import SessionLocal
from models.unidad_contenido import UnidadContenido, EstadoContenidoEnum

db = SessionLocal()

# Desactivar los documentos basura
docs = db.query(UnidadContenido).filter(UnidadContenido.id_contenido.in_([19, 28, 32])).all()

for doc in docs:
    doc.estado = EstadoContenidoEnum.inactivo
    print(f"Desactivando ID {doc.id_contenido}: {doc.titulo}")

db.commit()

# Limpiar ChromaDB
from rag.rag_service import RAGService
rag = RAGService(db)

print("\nRe-indexando agente 1...")
result = rag.reindex_agent(id_agente=1)
print(f"Resultado: {result}")

db.close()
print("\nDone!")
