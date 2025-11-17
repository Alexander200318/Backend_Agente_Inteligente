"""
Modelos SQLAlchemy del sistema CallCenterAI
Importar todos los modelos para que SQLAlchemy los registre correctamente
"""

# Modelos base
from models.departamento import Departamento
from models.persona import Persona
from models.usuario import Usuario

# Roles y permisos
from models.rol import Rol
from models.usuario_rol import UsuarioRol

# Agentes virtuales
from models.agente_virtual import AgenteVirtual
from models.usuario_agente import UsuarioAgente
from models.departamento_agente import DepartamentoAgente

# Contenido y base de conocimiento
from models.categoria import Categoria
from models.unidad_contenido import UnidadContenido

# Visitantes y conversaciones
from models.visitante_anonimo import VisitanteAnonimo
from models.conversacion_sync import ConversacionSync

# Métricas
from models.metrica_diaria_agente import MetricaDiariaAgente
from models.metrica_contenido import MetricaContenido

# Notificaciones
from models.notificacion_usuario import NotificacionUsuario

# API e integración
from models.api_key import APIKey
from models.widget_config import WidgetConfig

# Configuración
from models.configuracion_sistema import ConfiguracionSistema

__all__ = [
    # Base
    "Departamento",
    "Persona",
    "Usuario",
    
    # Roles
    "Rol",
    "UsuarioRol",
    
    # Agentes
    "AgenteVirtual",
    "UsuarioAgente",
    "DepartamentoAgente",
    
    # Contenido
    "Categoria",
    "UnidadContenido",
    
    # Visitantes
    "VisitanteAnonimo",
    "ConversacionSync",
    
    # Métricas
    "MetricaDiariaAgente",
    "MetricaContenido",
    
    # Notificaciones
    "NotificacionUsuario",
    
    # API
    "APIKey",
    "WidgetConfig",
    
    # Sistema
    "ConfiguracionSistema"
]