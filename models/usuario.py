# usuario.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from database.database import Base
import enum
import re
from datetime import datetime

class EstadoUsuarioEnum(str, enum.Enum):
    activo = "activo"
    inactivo = "inactivo"
    suspendido = "suspendido"
    bloqueado = "bloqueado"

class Usuario(Base):
    __tablename__ = "Usuario"

    # Primary Key
    id_usuario = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Key a Persona
    id_persona = Column(Integer, ForeignKey('Persona.id_persona', ondelete='CASCADE'), nullable=False, index=True)
    
    # Credenciales
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    
    # Estado de cuenta
    estado = Column(Enum(EstadoUsuarioEnum), default=EstadoUsuarioEnum.activo, index=True)
    requiere_cambio_password = Column(Boolean, default=False)
    intentos_fallidos = Column(Integer, default=0)
    fecha_ultimo_intento_fallido = Column(DateTime)
    fecha_bloqueo = Column(DateTime)
    
    # Sesiones
    ultimo_acceso = Column(DateTime)
    ultimo_ip = Column(String(45))
    token_recuperacion = Column(String(255))
    token_expiracion = Column(DateTime)
    
    # Auditoría
    fecha_creacion = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    
    fecha_actualizacion = Column(
        DateTime, 
        default=None, 
        onupdate=func.now(),
        nullable=True
    )

    creado_por = Column(Integer, ForeignKey('Usuario.id_usuario', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    persona = relationship("Persona", back_populates="usuario", foreign_keys=[id_persona])
    roles = relationship(
        "UsuarioRol", 
        back_populates="usuario", 
        cascade="all, delete-orphan",
        foreign_keys="[UsuarioRol.id_usuario]"
    )
    agentes_asignados = relationship(
        "UsuarioAgente", 
        back_populates="usuario", 
        cascade="all, delete-orphan",
        foreign_keys="[UsuarioAgente.id_usuario]"
    )
    
    # Self-referential para creado_por
    creador = relationship("Usuario", remote_side=[id_usuario], foreign_keys=[creado_por])
    disponible = Column(Boolean, default=False)

    # 🔐 ============ CONSTRAINTS DE SEGURIDAD ============
    __table_args__ = (
        CheckConstraint('intentos_fallidos >= 0 AND intentos_fallidos <= 10', name='check_intentos_fallidos_range'),
        CheckConstraint("LENGTH(username) >= 3 AND LENGTH(username) <= 50", name='check_username_length'),
        CheckConstraint("LENGTH(email) >= 5 AND LENGTH(email) <= 150", name='check_email_length'),
        CheckConstraint("ultimo_ip IS NULL OR LENGTH(ultimo_ip) <= 45", name='check_ip_length'),
    )

    # 🔐 ============ UTILIDADES DE SEGURIDAD ============
    @staticmethod
    def _sanitize_input(text):
        """Sanitizar input contra XSS y SQL Injection"""
        if not text:
            return ''
        
        # Remover scripts, iframes, eventos inline
        text = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<iframe[^>]*>.*?<\/iframe>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<img[^>]*onerror[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]*>', '', text)
        
        # Remover caracteres SQL peligrosos
        text = text.replace("'", "").replace('"', "").replace(';', '').replace('--', '').replace('/*', '').replace('*/', '')
        
        return text.strip()

    @staticmethod
    def _detect_xss_attempt(text):
        """Detectar intentos de XSS"""
        if not text:
            return False
        
        xss_patterns = [
            r'<script[^>]*>.*?<\/script>',
            r'on\w+\s*=',
            r'<iframe',
            r'javascript:',
            r'eval\(',
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _detect_sql_injection(text):
        """Detectar inyección SQL (solo patrones peligrosos)"""
        if not text:
            return False
        
        sql_patterns = [
            r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|UNION|WHERE|FROM|BY)\b',
            r'\/\*[\s\S]*?\*\/',  # Comentarios SQL /* */
            r';\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)',  # ; seguido de SQL
            r"(['\"])\s*(OR|AND)\s*(['\"]\d+['\"]|true)\s*=",  # ' OR '1'='1'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _validate_email(email):
        """Validar formato de email"""
        if not email:
            return False
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        return bool(re.match(email_regex, email))

    @staticmethod
    def _validate_string_length(text, max_length):
        """Validar longitud de string"""
        if not text:
            return True
        return len(text) <= max_length

    @staticmethod
    def _log_security_event(event_type, details):
        """Log de eventos de seguridad"""
        timestamp = datetime.utcnow().isoformat()
        print(f"🔒 SECURITY EVENT [{timestamp}]: {event_type} - {details}")

    # 🔐 ============ VALIDACIONES DE CAMPOS ============
    
    @validates('username')
    def validate_username(self, key, username):
        """Validar username con las mismas reglas del frontend"""
        if not username:
            raise ValueError("El username es obligatorio")
        
        # Sanitizar
        username = self._sanitize_input(username)
        
        # Detectar XSS
        if self._detect_xss_attempt(username):
            self._log_security_event('XSS_ATTEMPT_IN_USERNAME', {'username': username[:50]})
            raise ValueError("⚠️ Contenido sospechoso detectado en username")
        
        # Detectar SQL Injection (sin validar guiones normales)
        if self._detect_sql_injection(username):
            self._log_security_event('SQL_INJECTION_ATTEMPT_IN_USERNAME', {'username': username[:50]})
            raise ValueError("⚠️ Caracteres sospechosos detectados en username")
        
        # Validar longitud (3-50 caracteres)
        if len(username) < 3:
            raise ValueError("El username debe tener al menos 3 caracteres")
        
        if not self._validate_string_length(username, 50):
            raise ValueError("El username no puede exceder 50 caracteres")
        
        # Validar formato (solo alfanumérico, guiones y guiones bajos)
        if not re.match(r'^[A-Za-z0-9_-]+$', username):
            raise ValueError("El username solo puede contener letras, números, guiones y guiones bajos")
        
        return username

    @validates('email')
    def validate_email_field(self, key, email):
        """Validar email con las mismas reglas del frontend"""
        if not email:
            raise ValueError("El email es obligatorio")
        
        # Sanitizar
        email = self._sanitize_input(email)
        
        # Detectar XSS
        if self._detect_xss_attempt(email):
            self._log_security_event('XSS_ATTEMPT_IN_EMAIL', {'email': email[:50]})
            raise ValueError("⚠️ Contenido sospechoso detectado en email")
        
        # Detectar SQL Injection
        if self._detect_sql_injection(email):
            self._log_security_event('SQL_INJECTION_ATTEMPT_IN_EMAIL', {'email': email[:50]})
            raise ValueError("⚠️ Caracteres sospechosos detectados en email")
        
        # Validar longitud (5-150 caracteres)
        if len(email) < 5:
            raise ValueError("El email debe tener al menos 5 caracteres")
        
        if not self._validate_string_length(email, 150):
            raise ValueError("El email no puede exceder 150 caracteres")
        
        # Validar formato
        if not self._validate_email(email):
            raise ValueError("El email no tiene un formato válido")
        
        return email.lower()  # Normalizar a minúsculas

    @validates('ultimo_ip')
    def validate_ip(self, key, ip):
        """Validar dirección IP"""
        if not ip:
            return ip
        
        # Sanitizar
        ip = self._sanitize_input(ip)
        
        # Validar longitud (máximo 45 para IPv6)
        if not self._validate_string_length(ip, 45):
            raise ValueError("La dirección IP no puede exceder 45 caracteres")
        
        # Validar formato básico IPv4 o IPv6
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
        
        if not (re.match(ipv4_pattern, ip) or re.match(ipv6_pattern, ip)):
            self._log_security_event('INVALID_IP_FORMAT', {'ip': ip})
            raise ValueError("Formato de dirección IP inválido")
        
        return ip

    @validates('intentos_fallidos')
    def validate_intentos_fallidos(self, key, intentos):
        """Validar intentos fallidos"""
        if intentos is None:
            return 0
        
        # Validar rango (0-10)
        if intentos < 0:
            return 0
        
        if intentos > 10:
            self._log_security_event('EXCESSIVE_FAILED_ATTEMPTS', {'intentos': intentos})
            # Auto-bloquear si supera el límite
            return 10
        
        return intentos

    @validates('token_recuperacion')
    def validate_token(self, key, token):
        """Validar token de recuperación"""
        if not token:
            return token
        
        # Sanitizar
        token = self._sanitize_input(token)
        
        # Validar longitud
        if not self._validate_string_length(token, 255):
            raise ValueError("El token de recuperación no puede exceder 255 caracteres")
        
        return token

    @validates('password')
    def validate_password_field(self, key, password):
        """Validar que el password no esté vacío (el hash ya viene procesado)"""
        if not password:
            raise ValueError("El password es obligatorio")
        
        # Validar longitud del hash (bcrypt = ~60 chars, argon2 puede ser más)
        if not self._validate_string_length(password, 255):
            raise ValueError("El hash del password excede el límite permitido")
        
        return password

    @validates('estado')
    def validate_estado(self, key, estado):
        """Validar estado del usuario"""
        if estado not in EstadoUsuarioEnum.__members__.values():
            raise ValueError(f"Estado inválido. Debe ser uno de: {', '.join([e.value for e in EstadoUsuarioEnum])}")
        
        return estado

    # 🔐 ============ MÉTODOS DE SEGURIDAD ADICIONALES ============
    
    def incrementar_intentos_fallidos(self):
        """Incrementar contador de intentos fallidos"""
        self.intentos_fallidos = (self.intentos_fallidos or 0) + 1
        self.fecha_ultimo_intento_fallido = func.now()
        
        # Auto-bloquear después de 5 intentos
        if self.intentos_fallidos >= 5:
            self.estado = EstadoUsuarioEnum.bloqueado
            self.fecha_bloqueo = func.now()
            self._log_security_event('USER_AUTO_BLOCKED', {
                'id_usuario': self.id_usuario,
                'username': self.username,
                'intentos': self.intentos_fallidos
            })

    def resetear_intentos_fallidos(self):
        """Resetear contador de intentos fallidos"""
        self.intentos_fallidos = 0
        self.fecha_ultimo_intento_fallido = None

    def puede_intentar_login(self):
        """Verificar si el usuario puede intentar login"""
        if self.estado == EstadoUsuarioEnum.bloqueado:
            return False
        
        if self.intentos_fallidos >= 5:
            return False
        
        return True

    def registrar_acceso(self, ip_address):
        """Registrar último acceso del usuario"""
        # Validar IP antes de guardar
        if ip_address:
            ip_address = self._sanitize_input(ip_address)
            if len(ip_address) > 45:
                ip_address = ip_address[:45]
        
        self.ultimo_acceso = func.now()
        self.ultimo_ip = ip_address
        self.resetear_intentos_fallidos()
        
        self._log_security_event('USER_LOGIN_SUCCESS', {
            'id_usuario': self.id_usuario,
            'username': self.username,
            'ip': ip_address
        })

    def __repr__(self):
        return f"<Usuario(id={self.id_usuario}, username='{self.username}', email='{self.email}', estado='{self.estado.value}')>"