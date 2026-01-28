from database.database import SessionLocal
from models.unidad_contenido import UnidadContenido

db = SessionLocal()

# Ver TODOS los documentos con "carrera"
docs = db.query(UnidadContenido).filter(UnidadContenido.contenido.ilike('%carrera%')).all()
print(f"Total documentos con 'carrera': {len(docs)}\n")

for doc in docs:
    print(f"ID {doc.id_contenido}:")
    print(f"  Título: {doc.titulo[:80]}")
    print(f"  Estado: {doc.estado}")
    print(f"  Eliminado: {doc.eliminado}")
    print()

db.close()
