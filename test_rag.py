from database.database import SessionLocal
from models.unidad_contenido import UnidadContenido, EstadoContenidoEnum
from rag.rag_service import RAGService
from sqlalchemy import func

db = SessionLocal()

# 1. Verificar documentos en BD
print("=" * 60)
print("1️⃣  DOCUMENTOS EN BASE DE DATOS")
print("=" * 60)

total = db.query(func.count(UnidadContenido.id_contenido)).scalar()
activos = db.query(func.count(UnidadContenido.id_contenido)).filter(UnidadContenido.estado == EstadoContenidoEnum.activo).scalar()
inactivos = db.query(func.count(UnidadContenido.id_contenido)).filter(UnidadContenido.estado == EstadoContenidoEnum.inactivo).scalar()

print(f'Total: {total}')
print(f'Activos: {activos}')
print(f'Inactivos: {inactivos}')

# 2. Ver documentos con "carrera"
print("\n📝 Documentos con 'carrera':")
docs_bd = db.query(UnidadContenido).filter(UnidadContenido.contenido.ilike('%carrera%')).all()
print(f'Encontrados en BD: {len(docs_bd)}')
for doc in docs_bd:
    print(f'  - {doc.contenido[:80]}... [estado={doc.estado}] [id_agente={doc.id_agente}]')

# 3. Buscar en RAG sin filtro
print("\n" + "=" * 60)
print("2️⃣  BÚSQUEDA EN RAG (sin inactivos)")
print("=" * 60)
rag = RAGService(db)
docs_rag = rag.search(id_agente=1, query='carrera', incluir_inactivos=False)
print(f'Encontrados en RAG: {len(docs_rag)}')
for doc in docs_rag:
    meta = doc.get('metadata', {})
    print(f'  - {doc.get("document", "")[:80]}...')
    print(f'    Metadata: {meta}')

# 4. Buscar en RAG CON inactivos
print("\n" + "=" * 60)
print("3️⃣  BÚSQUEDA EN RAG (CON inactivos)")
print("=" * 60)
docs_rag_all = rag.search(id_agente=1, query='carrera', incluir_inactivos=True)
print(f'Encontrados en RAG: {len(docs_rag_all)}')
for doc in docs_rag_all:
    meta = doc.get('metadata', {})
    print(f'  - {doc.get("document", "")[:80]}...')
    print(f'    Metadata: {meta}')

db.close()
