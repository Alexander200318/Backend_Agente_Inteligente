#!/usr/bin/env python
from sentence_transformers import SentenceTransformer, CrossEncoder

try:
    print("Intentando cargar embedder...")
    embedder = SentenceTransformer('/app/hf_models/all-MiniLM-L6-v2')
    print("✅ Embedder cargado exitosamente")
except Exception as e:
    print(f"❌ Error con embedder: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\nIntentando cargar reranker...")
    reranker = CrossEncoder('/app/hf_models/ms-marco-MiniLM-L-6-v2')
    print("✅ Reranker cargado exitosamente")
except Exception as e:
    print(f"❌ Error con reranker: {e}")
    import traceback
    traceback.print_exc()
