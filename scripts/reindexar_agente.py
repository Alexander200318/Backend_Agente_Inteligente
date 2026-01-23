# scripts/reindexar_agente.py
import sys
sys.path.append('.')

from database.database import SessionLocal
from rag.rag_service import RAGService

db = SessionLocal()
rag = RAGService(db, use_cache=True)  # 🔥 DESACTIVAR CACHE

# Tu ID de agente
id_agente = 6

print(f"🔄 Re-indexando agente {id_agente}...")

resultado = rag.reindex_agent(id_agente)

print(f"\n✅ Resultado:")
print(f"   Total documentos indexados: {resultado['total_docs']}")
print(f"   Colección: {resultado['collection']}")
print(f"   Cache limpiado: {resultado['cache_cleared']}")

# 🔥 LIMPIAR CACHE MANUALMENTE
print(f"\n🧹 Limpiando cache de Redis...")
rag.clear_cache(id_agente)

# 🔥 CREAR NUEVA INSTANCIA SIN CACHE
rag_sin_cache = RAGService(db, use_cache=False)

# Ahora probar búsqueda
print(f"\n🔍 Probando búsqueda SIN CACHE...")
resultados = rag_sin_cache.search(
    id_agente=id_agente,
    query="Información general sobre la investigación aplicada",
    n_results=3,
    use_reranking=False,
    incluir_inactivos=False
)

print(f"\n📊 Encontrados: {len(resultados)} documentos")
for i, r in enumerate(resultados):
    meta = r.get('metadata', {})
    print(f"\n--- Resultado {i+1} ---")
    print(f"   Título: {meta.get('titulo', 'Sin título')}")
    print(f"   Activo: {meta.get('activo')}")
    print(f"   Score: {r.get('score'):.3f}")