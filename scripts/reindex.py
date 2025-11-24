# scripts/reindex.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from database.database import SessionLocal
from rag.rag_service import RAGService
from models.agente_virtual import AgenteVirtual

def main():
    db: Session = SessionLocal()
    rag = RAGService(db, use_cache=True)
    
    # 🔥 Usar agente 3
    id_agente = 3
    
    print(f"🔄 Reindexando agente {id_agente}...")
    resultado = rag.reindex_agent(id_agente)
    print("✅ Resultado:", resultado)
    
    db.close()

if __name__ == "__main__":
    main()