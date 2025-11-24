# scripts/test_rag_with_cache.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from database.database import SessionLocal
from rag.rag_service import RAGService
import time

def test_rag_cache():
    db: Session = SessionLocal()
    rag = RAGService(db, use_cache=True)
    
    id_agente = 3  # 🔥 Cambiado a agente 3
    query = "¿Cómo cambiar mi contraseña?"  # Ajusta según tu contenido
    
    print("=" * 60)
    print("🧪 PRUEBA DE CACHÉ RAG")
    print("=" * 60)
    
    # Primera búsqueda (MISS)
    print("\n1️⃣  Primera búsqueda (debería ser CACHE MISS):")
    start = time.time()
    results1 = rag.search(id_agente, query, n_results=3, use_reranking=True)
    print(f"\n   📄 Documento encontrado:")
    print(f"   Título: {results1[0]['metadata'].get('titulo', 'N/A')}")
    print(f"   Tipo: {results1[0]['metadata'].get('tipo', 'N/A')}")
    print(f"   Score: {results1[0].get('score', 'N/A')}")
    print(f"   Preview: {results1[0]['document'][:200]}...")
    time1 = time.time() - start
    print(f"   ⏱️  Tiempo: {time1:.3f}s")
    print(f"   📊 Resultados: {len(results1)}")
    if results1:
        print(f"   📄 Primer resultado: {results1[0]['metadata'].get('titulo', 'N/A')}")
    
    # Segunda búsqueda (HIT)
    print("\n2️⃣  Segunda búsqueda (debería ser CACHE HIT):")
    start = time.time()
    results2 = rag.search(id_agente, query, n_results=3, use_reranking=True)
    time2 = time.time() - start
    print(f"   ⏱️  Tiempo: {time2:.3f}s")
    print(f"   📊 Resultados: {len(results2)}")
    
    # Comparación
    if time2 > 0:
        print(f"\n📈 Mejora de velocidad: {time1/time2:.1f}x más rápido con caché")
    
    # Estadísticas
    print("\n📊 Estadísticas del caché:")
    stats = rag.get_cache_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Limpiar caché
    print("\n🗑️  Limpiando caché...")
    rag.clear_cache(id_agente)
    
    db.close()
    print("\n✅ Prueba completada")

if __name__ == "__main__":
    test_rag_cache()