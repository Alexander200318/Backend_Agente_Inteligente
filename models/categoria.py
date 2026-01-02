from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base


class Categoria(Base):
    __tablename__ = "Categoria"

    # Primary Key
    id_categoria = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign Key: Agente
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
        index=True,
        nullable=True
    )

    # Apariencia / UI
    icono = Column(String(100), default="folder")
    color = Column(String(7), default="#667eea")
    orden = Column(Integer, default=0, index=True)

    # Estado
    activo = Column(Boolean, default=True, index=True)
    eliminado = Column(Boolean, default=False, index=True) 

    # Auditoría
    fecha_creacion = Column(DateTime, server_default=func.current_timestamp())
    creado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'))

    # ============================
    # 🔗 RELACIONES
    # ============================

    # Agente propietario
    agente = relationship("AgenteVirtual", back_populates="categorias")

    # Relación para jerarquía de categorías
    categoria_padre = relationship(
        "Categoria",
        remote_side=[id_categoria],
        backref="subcategorias"
    )

    # Contenidos asociados
    contenidos = relationship("UnidadContenido", back_populates="categoria")

    # Usuario creador
    creador = relationship("Usuario")

    def __repr__(self):
        return f"<Categoria(id={self.id_categoria}, nombre='{self.nombre}', agente_id={self.id_agente})>"
