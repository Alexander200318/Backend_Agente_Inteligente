import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import SessionLocal
from models.agente_virtual import AgenteVirtual

db = SessionLocal()

agente = db.query(AgenteVirtual).filter(AgenteVirtual.id_agente == 3).first()

if agente:
    print(f"Agente: {agente.nombre_agente}")
    print(f"Modelo actual: {agente.modelo_ia}")
    
    agente.modelo_ia = "llama3"  # ✅ Cambiar a llama3
    db.commit()
    
    print(f"✅ Modelo actualizado a: llama3")
else:
    print("❌ Agente 3 no encontrado")

db.close()