"""
Script completo para poblar TODAS las tablas con datos de prueba
"""
from database.database import SessionLocal
from services.usuario_service import UsuarioService
from schemas.usuario_schemas import UsuarioCreate
from schemas.persona_schemas import PersonaCreate
from models import *
from datetime import date, datetime, timedelta
import json
import secrets

def generar_api_key():
    """Generar API key aleatoria"""
    return secrets.token_urlsafe(48)

def seed_completo():
    """Ejecutar seed completo de todas las entidades"""
    db = SessionLocal()
    print("=" * 80)
    print("SEED COMPLETO - CallCenterAI")
    print("=" * 80)
    
    try:
        # 1. DEPARTAMENTOS
        print("\n📂 [1/10] Creando Departamentos...")
        deptos = []
        departamentos_data = [
            {"nombre": "Tecnologías de la Información", "codigo": "TI", "email": "ti@inst.edu.ec", "facultad": "Ingeniería"},
            {"nombre": "Admisiones", "codigo": "ADM", "email": "admisiones@inst.edu.ec", "facultad": "Administración"},
            {"nombre": "Bienestar Estudiantil", "codigo": "BE", "email": "bienestar@inst.edu.ec"},
            {"nombre": "Recursos Humanos", "codigo": "RRHH", "email": "rrhh@inst.edu.ec"}
        ]
        for d in departamentos_data:
            depto = Departamento(**d, activo=True)
            db.add(depto)
            db.commit()
            db.refresh(depto)
            deptos.append(depto)
            print(f"  ✅ {depto.nombre}")
        
        # 2. USUARIOS Y PERSONAS
        print("\n👥 [2/10] Creando Usuarios...")
        service = UsuarioService(db)
        usuarios = []
        
        usuarios_data = [
            {
                "username": "admin", "email": "admin@inst.edu.ec", "password": "Admin123",
                "persona": {"cedula": "0123456789", "nombre": "Admin", "apellido": "Sistema",
                           "tipo_persona": "administrativo", "email_personal": "admin@gmail.com",
                           "fecha_nacimiento": date(1990, 1, 1), "cargo": "Administrador",
                           "id_departamento": deptos[0].id_departamento}
            },
            {
                "username": "jperez", "email": "juan.perez@inst.edu.ec", "password": "Password123",
                "persona": {"cedula": "0923456789", "nombre": "Juan", "apellido": "Pérez",
                           "tipo_persona": "docente", "email_personal": "juan@gmail.com",
                           "fecha_nacimiento": date(1985, 5, 15), "cargo": "Profesor Titular",
                           "id_departamento": deptos[1].id_departamento}
            },
            {
                "username": "mgarcia", "email": "maria.garcia@inst.edu.ec", "password": "Maria123",
                "persona": {"cedula": "0987654321", "nombre": "María", "apellido": "García",
                           "tipo_persona": "administrativo", "email_personal": "maria@gmail.com",
                           "fecha_nacimiento": date(1992, 8, 20), "cargo": "Coordinadora",
                           "id_departamento": deptos[1].id_departamento}
            }
        ]
        
        for u_data in usuarios_data:
            persona_schema = PersonaCreate(**u_data["persona"])
            usuario_schema = UsuarioCreate(username=u_data["username"], email=u_data["email"],
                                          password=u_data["password"], persona=persona_schema)
            u = service.crear_usuario(usuario_schema)
            usuarios.append(u)
            print(f"  ✅ {u.username}")
        
        # 3. ROLES
        print("\n🔐 [3/10] Creando Roles...")
        roles = []
        roles_data = [
            {"nombre_rol": "Super Administrador", "nivel_jerarquia": 1, "puede_gestionar_usuarios": True,
             "puede_gestionar_departamentos": True, "puede_gestionar_roles": True,
             "puede_configurar_sistema": True, "creado_por": usuarios[0].id_usuario},
            {"nombre_rol": "Administrador", "nivel_jerarquia": 2, "puede_gestionar_usuarios": True,
             "puede_ver_todas_metricas": True, "creado_por": usuarios[0].id_usuario},
            {"nombre_rol": "Gestor de Contenido", "nivel_jerarquia": 3,
             "creado_por": usuarios[0].id_usuario},
        ]
        for r in roles_data:
            rol = Rol(**r)
            db.add(rol)
            db.commit()
            db.refresh(rol)
            roles.append(rol)
            print(f"  ✅ {rol.nombre_rol}")
        
        # 4. ASIGNAR ROLES A USUARIOS
        print("\n🎭 [4/10] Asignando Roles...")
        UsuarioRol(id_usuario=usuarios[0].id_usuario, id_rol=roles[0].id_rol,
                   asignado_por=usuarios[0].id_usuario).save(db)
        UsuarioRol(id_usuario=usuarios[1].id_usuario, id_rol=roles[2].id_rol,
                   asignado_por=usuarios[0].id_usuario).save(db)
        print(f"  ✅ 2 roles asignados")
        
        # 5. AGENTES VIRTUALES
        print("\n🤖 [5/10] Creando Agentes Virtuales...")
        agentes = []
        agentes_data = [
            {
                "nombre_agente": "Alex - Asistente General",
                "tipo_agente": "router",
                "area_especialidad": "Atención General",
                "descripcion": "Agente router que deriva a especialistas",
                "color_tema": "#3B82F6",
                "mensaje_bienvenida": "¡Hola! Soy Alex, ¿en qué puedo ayudarte?",
                "id_departamento": deptos[0].id_departamento,
                "creado_por": usuarios[0].id_usuario,
                "activo": True
            },
            {
                "nombre_agente": "Sofia - Admisiones",
                "tipo_agente": "especializado",
                "area_especialidad": "Admisiones",
                "descripcion": "Especialista en procesos de admisión",
                "color_tema": "#10B981",
                "mensaje_bienvenida": "Hola, soy Sofia. Te ayudaré con admisiones.",
                "id_departamento": deptos[1].id_departamento,
                "creado_por": usuarios[0].id_usuario,
                "activo": True
            },
            {
                "nombre_agente": "Luis - Soporte TI",
                "tipo_agente": "especializado",
                "area_especialidad": "Tecnología",
                "descripcion": "Soporte técnico y sistemas",
                "color_tema": "#8B5CF6",
                "mensaje_bienvenida": "¡Hola! Soy Luis, tu asistente técnico.",
                "id_departamento": deptos[0].id_departamento,
                "creado_por": usuarios[0].id_usuario,
                "activo": True
            }
        ]
        for a in agentes_data:
            agente = AgenteVirtual(**a)
            db.add(agente)
            db.commit()
            db.refresh(agente)
            agentes.append(agente)
            print(f"  ✅ {agente.nombre_agente}")
        
        # 6. ASIGNAR USUARIOS A AGENTES
        print("\n👤 [6/10] Asignando Usuarios a Agentes...")
        UsuarioAgente(id_usuario=usuarios[1].id_usuario, id_agente=agentes[1].id_agente,
                     puede_crear_contenido=True, puede_editar_contenido=True,
                     asignado_por=usuarios[0].id_usuario).save(db)
        print(f"  ✅ 1 asignación creada")
        
        # 7. CATEGORÍAS
        print("\n📁 [7/10] Creando Categorías...")
        categorias = []
        categorias_data = [
            {"nombre": "Requisitos", "id_agente": agentes[1].id_agente, "orden": 1,
             "creado_por": usuarios[0].id_usuario},
            {"nombre": "Fechas Importantes", "id_agente": agentes[1].id_agente, "orden": 2,
             "creado_por": usuarios[0].id_usuario},
            {"nombre": "Problemas Comunes", "id_agente": agentes[2].id_agente, "orden": 1,
             "creado_por": usuarios[0].id_usuario},
        ]
        for c in categorias_data:
            cat = Categoria(**c)
            db.add(cat)
            db.commit()
            db.refresh(cat)
            categorias.append(cat)
            print(f"  ✅ {cat.nombre}")
        
        # 8. CONTENIDOS
        print("\n📄 [8/10] Creando Contenidos...")
        contenidos_data = [
            {
                "titulo": "Requisitos de Admisión 2025",
                "contenido": "Para ingresar necesitas: cédula, certificado de bachillerato...",
                "resumen": "Documentación necesaria para admisión",
                "id_agente": agentes[1].id_agente,
                "id_categoria": categorias[0].id_categoria,
                "id_departamento": deptos[1].id_departamento,
                "estado": "activo",
                "prioridad": 10,
                "creado_por": usuarios[1].id_usuario,
                "publicado_por": usuarios[0].id_usuario,
                "fecha_publicacion": datetime.now()
            },
            {
                "titulo": "Fechas del Proceso de Admisión",
                "contenido": "Inscripciones: 1-15 enero. Examen: 20 enero...",
                "resumen": "Cronograma del proceso de admisión",
                "id_agente": agentes[1].id_agente,
                "id_categoria": categorias[1].id_categoria,
                "id_departamento": deptos[1].id_departamento,
                "estado": "activo",
                "prioridad": 9,
                "creado_por": usuarios[1].id_usuario
            }
        ]
        contenidos = []
        for cont in contenidos_data:
            c = UnidadContenido(**cont)
            db.add(c)
            db.commit()
            db.refresh(c)
            contenidos.append(c)
            print(f"  ✅ {c.titulo}")
        
        # 9. VISITANTES Y CONVERSACIONES
        print("\n👁️  [9/10] Creando Visitantes...")
        visitantes = []
        for i in range(3):
            v = VisitanteAnonimo(
                identificador_sesion=f"session_{secrets.token_hex(16)}",
                ip_origen=f"192.168.1.{i+10}",
                dispositivo="desktop",
                navegador="Chrome",
                pais="Ecuador",
                ciudad="Cuenca",
                total_conversaciones=1
            )
            db.add(v)
            db.commit()
            db.refresh(v)
            visitantes.append(v)
            
            # Crear conversación
            conv = ConversacionSync(
                mongodb_conversation_id=secrets.token_hex(12),
                id_visitante=v.id_visitante,
                id_agente_inicial=agentes[0].id_agente,
                id_agente_actual=agentes[1].id_agente,
                estado="finalizada",
                total_mensajes=5
            )
            db.add(conv)
            db.commit()
        print(f"  ✅ {len(visitantes)} visitantes y conversaciones")
        
        # 10. WIDGETS Y API KEYS
        print("\n🔧 [10/10] Creando Widgets y API Keys...")
        widget = WidgetConfig(
            id_agente=agentes[0].id_agente,
            nombre_widget="Widget Principal",
            sitio_web="https://www.institucion.edu.ec",
            dominio_permitido="institucion.edu.ec",
            creado_por=usuarios[0].id_usuario
        )
        db.add(widget)
        
        api_key = APIKey(
            key_value=generar_api_key(),
            key_name="API Key Producción",
            id_agente=agentes[0].id_agente,
            tipo_integracion="wordpress",
            creado_por=usuarios[0].id_usuario
        )
        db.add(api_key)
        db.commit()
        print(f"  ✅ Widget y API Key creados")
        
        # ESTADÍSTICAS FINALES
        print("\n" + "=" * 80)
        print("✅ SEED COMPLETADO EXITOSAMENTE")
        print("=" * 80)
        print(f"📊 Departamentos:    {len(deptos)}")
        print(f"👥 Usuarios:         {len(usuarios)}")
        print(f"🔐 Roles:            {len(roles)}")
        print(f"🤖 Agentes:          {len(agentes)}")
        print(f"📁 Categorías:       {len(categorias)}")
        print(f"📄 Contenidos:       {len(contenidos)}")
        print(f"👁️  Visitantes:       {len(visitantes)}")
        print("=" * 80)
        
        db.close()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        db.close()

# Helper para guardar modelos
def save_model(model, db):
    db.add(model)
    db.commit()
    db.refresh(model)
    return model

# Agregar método save a todos los modelos
from database.database import Base
Base.save = lambda self, db: save_model(self, db)

if __name__ == "__main__":
    seed_completo()