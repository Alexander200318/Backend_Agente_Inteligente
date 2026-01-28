from database.database import SessionLocal
from models.unidad_contenido import UnidadContenido, EstadoContenidoEnum

db = SessionLocal()

docs = db.query(UnidadContenido).filter(
    UnidadContenido.id_agente == 1,
    UnidadContenido.estado == EstadoContenidoEnum.activo,
    UnidadContenido.eliminado == False
).all()

print("ACTIVOS para agente 1:", len(docs))
for doc in docs:
    print(f"  - ID {doc.id_contenido}: {doc.titulo}")

db.close()
