"""
Modelos SQLAlchemy del sistema CallCenterAI
Importar todos los modelos para que SQLAlchemy los registre correctamente
IMPORTANTE: El orden de importación importa para las relaciones
"""

# 1. Modelos base (sin dependencias)
from models.departamento import Departamento
from models.persona import Persona

# 2. Usuario (depende de Persona y Departamento)
from models.usuario import Usuario

# 3. Roles (dependen de Usuario)
from models.rol import Rol
from models.usuario_rol import UsuarioRol

# 4. Agentes virtuales
from models.agente_virtual import AgenteVirtual
from models.usuario_agente import UsuarioAgente
from models.departamento_agente import DepartamentoAgente

# 5. Contenido y base de conocimiento
from models.categoria import Categoria
from models.unidad_contenido import UnidadContenido

# 6. Visitantes y conversaciones
from models.visitante_anonimo import VisitanteAnonimo
from models.conversacion_sync import ConversacionSync

# 7. Métricas
from models.metrica_diaria_agente import MetricaDiariaAgente
from models.metrica_contenido import MetricaContenido

# 8. Notificaciones
from models.notificacion_usuario import NotificacionUsuario

# 9. API e integración
from models.api_key import APIKey
from models.widget_config import WidgetConfig

# 10. Configuración
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