# scripts/download_hf_models.py
from pathlib import Path
from sentence_transformers import SentenceTransformer, CrossEncoder

# Carpeta base: app/
BASE_DIR = Path(__file__).resolve().parent.parent
HF_MODELS_DIR = BASE_DIR / "hf_models"

EMBEDDER_DIR = HF_MODELS_DIR / "all-MiniLM-L6-v2"
RERANKER_DIR = HF_MODELS_DIR / "ms-marco-MiniLM-L-6-v2"


def main():
    HF_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print(">> Descargando y guardando modelos en", HF_MODELS_DIR)

    # 1) EMBEDDER
    print("\nDescargando modelo 1/2: sentence-transformers/all-MiniLM-L6-v2 ...")
    embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDER_DIR.mkdir(parents=True, exist_ok=True)
    embedder.save(str(EMBEDDER_DIR))
    print("✅ Modelo de embeddings guardado en:", EMBEDDER_DIR)

    # 2) RERANKER
    print("\nDescargando modelo 2/2: cross-encoder/ms-marco-MiniLM-L-6-v2 ...")
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    RERANKER_DIR.mkdir(parents=True, exist_ok=True)
    reranker.save(str(RERANKER_DIR))
    print("✅ Modelo de re-ranking guardado en:", RERANKER_DIR)

    print("\n🎉 Modelos descargados y guardados localmente. Ya puedes usar RAG sin internet.")


if __name__ == "__main__":
    main()
