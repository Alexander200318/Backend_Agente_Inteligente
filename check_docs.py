from database.database import SessionLocal
from models.unidad_contenido import UnidadContenido

db = SessionLocal()

docs = db.query(UnidadContenido).filter(UnidadContenido.id_contenido.in_([19, 28, 32])).all()

for doc in docs:
    print(f"ID {doc.id_contenido}: {doc.titulo}")
    print(f"Contenido: {doc.contenido[:200]}")
    print(f"Estado: {doc.estado}")
    print()

db.close()
