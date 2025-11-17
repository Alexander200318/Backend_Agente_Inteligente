from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base

class Categoria(Base):
    __tablename__ = "Categoria"

    # Primary Key
    id_categoria = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Key
    id_agente = Column(
        Integer, 
        ForeignKey('Agente_Virtual.id_agente', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Información básica
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    
    # Jerarquía
    id_categoria_padre = Column(
        Integer, 
        ForeignKey('Categoria.id_categoria', ondelete='SET NULL'),
        index=True
    )
    
    # Apariencia
    icono = Column(String(100))
    color = Column(String(7))
    orden = Column(Integer, default=0, index=True)
    
    # Estado
    activo = Column(Boolean, default=True, index=True)
    
    # Auditoría
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    creado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))
    
    # Relationships
    agente = relationship("AgenteVirtual", back_populates="categorias")
    categoria_padre = relationship("Categoria", remote_side=[id_categoria], backref="subcategorias")
    contenidos = relationship("UnidadContenido", back_populates="categoria")
    creador = relationship("Usuario")

    def __repr__(self):
        return f"<Categoria(id={self.id_categoria}, nombre='{self.nombre}', agente_id={self.id_agente})>"