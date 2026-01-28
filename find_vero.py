from database.database import SessionLocal
from models.unidad_contenido import UnidadContenido, EstadoContenidoEnum

db = SessionLocal()

docs = db.query(UnidadContenido).filter(
    UnidadContenido.contenido.ilike('%Verónica%'),
    UnidadContenido.estado == EstadoContenidoEnum.activo,
    UnidadContenido.eliminado == False
).all()

print(f"Documentos con 'Verónica': {len(docs)}\n")

for doc in docs:
    print(f"ID {doc.id_contenido}: {doc.titulo}")
    print(f"Agente: {doc.id_agente}")
    print(f"Contenido completo:\n{doc.contenido}\n")
    print("="*60)

db.close()
