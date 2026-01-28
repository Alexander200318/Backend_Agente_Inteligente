from database.database import SessionLocal
from models.agente_virtual import AgenteVirtual
from models.unidad_contenido import UnidadContenido, EstadoContenidoEnum

db = SessionLocal()

print("AGENTES Y SUS DOCUMENTOS ACTIVOS:\n")

agentes = db.query(AgenteVirtual).filter(AgenteVirtual.activo == True).all()

for agente in agentes:
    # Contar documentos activos
    docs_count = db.query(UnidadContenido).filter(
        UnidadContenido.id_agente == agente.id_agente,
        UnidadContenido.estado == EstadoContenidoEnum.activo,
        UnidadContenido.eliminado == False
    ).count()
    
    print(f"ID {agente.id_agente}: {agente.nombre_agente}")
    print(f"   Documentos activos: {docs_count}")
    print()

db.close()
