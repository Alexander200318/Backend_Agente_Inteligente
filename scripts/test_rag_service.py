# test_rag_service.py
from sqlalchemy.orm import Session
from database.database import SessionLocal
from rag.rag_service import RAGService
from models.categoria import Categoria
from models.unidad_contenido import UnidadContenido

def main():
    db: Session = SessionLocal()

    rag = RAGService(db)

    # 1) Obtenemos una categoría existente
    categoria = db.query(Categoria).first()
    if not categoria:
        print("No hay categorías activas.")
        return

    print("Categoria encontrada:", categoria.nombre)

    # 2) Obtenemos una unidad de contenido existente
    unidad = db.query(UnidadContenido).first()
    if not unidad:
        print("No hay unidades de contenido.")
        return

    print("Unidad encontrada:", unidad.titulo)

    # 3) Indexamos la unidad
    print("Ingestando unidad...")
    r = rag.ingest_unidad(unidad, categoria)
    print("Resultado:", r)

    # 4) Hacemos una búsqueda
    print("\nBuscando algo sobre:", unidad.titulo)
    results = rag.search(categoria.id_agente, unidad.titulo)
    print(results)

if __name__ == "__main__":
    main()
