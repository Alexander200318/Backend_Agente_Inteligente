from database.database import SessionLocal
from models.unidad_contenido import UnidadContenido, EstadoContenidoEnum

db = SessionLocal()

print("DOCUMENTOS CON 'DOCENTES' O 'PROFESORES':\n")

docs = db.query(UnidadContenido).filter(
    UnidadContenido.contenido.ilike('%docent%'),
    UnidadContenido.estado == EstadoContenidoEnum.activo,
    UnidadContenido.eliminado == False
).all()

for doc in docs:
    print(f"ID {doc.id_contenido}: {doc.titulo}")
    print(f"   Agente: {doc.id_agente}")
    print(f"   Contenido: {doc.contenido[:100]}...\n")

if not docs:
    print("No hay documentos activos con 'docentes'")

db.close()
