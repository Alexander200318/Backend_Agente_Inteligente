from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class Rol(Base):
    __tablename__ = "Rol"

    # Primary Key
    id_rol = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Información básica
    nombre_rol = Column(String(50), unique=True, nullable=False)
    descripcion = Column(Text)
    nivel_jerarquia = Column(
        Integer, 
        default=3, 
        comment='1=Super Admin, 2=Admin, 3=Funcionario, 4=Usuario básico'
    )
    
    # Permisos globales del sistema
    puede_gestionar_usuarios = Column(Boolean, default=False)
    puede_gestionar_departamentos = Column(Boolean, default=False)
    puede_gestionar_roles = Column(Boolean, default=False)
    puede_ver_todas_metricas = Column(Boolean, default=False)
    puede_exportar_datos_globales = Column(Boolean, default=False)
    puede_configurar_sistema = Column(Boolean, default=False)
    puede_gestionar_api_keys = Column(Boolean, default=False)
    
    # Estado
    activo = Column(Boolean, default=True, index=True)
    
    # Auditoría
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    creado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    
    # Relationships
    usuarios_rol = relationship("UsuarioRol", back_populates="rol", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Rol(id={self.id_rol}, nombre='{self.nombre_rol}', nivel={self.nivel_jerarquia})>"