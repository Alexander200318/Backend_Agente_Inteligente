#!/usr/bin/env python3
"""Script para verificar y limpiar RAG/Cache"""

import sys
sys.path.insert(0, '/root')

from database.database import SessionLocal
from config.redis_config import get_redis_client
from rag.rag_service import RAGService

# Limpiar Redis
print("🧹 Limpiando Redis...")
try:
    redis = get_redis_client()
    keys = redis.keys("*")
    if keys:
        redis.delete(*keys)
        print(f"✅ {len(keys)} claves eliminadas de Redis")
    else:
        print("ℹ️  Redis está vacío")
except Exception as e:
    print(f"⚠️  Error con Redis: {e}")

# Limpiar caché de RAG
print("\n🧹 Limpiando caché de embeddings...")
db = SessionLocal()
rag = RAGService(db, use_cache=True)
rag.clear_embedding_cache()
print("✅ Caché de embeddings limpiado")

# Listar colecciones de ChromaDB
print("\n📋 Verificando colecciones de ChromaDB...")
try:
    collections = rag.chroma.client.list_collections()
    print(f"✅ {len(collections)} colecciones encontradas:")
    for col in collections:
        count = col.count()
        print(f"   - {col.name}: {count} documentos")
except Exception as e:
    print(f"❌ Error listando colecciones: {e}")

print("\n✅ Limpieza completada. El próximo request hará búsqueda fresca.")
