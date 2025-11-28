# core/security.py
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from typing import Optional
import re
from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================
# CONTRASEÑAS
# ============================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar contraseña
    
    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash de la contraseña
        
    Returns:
        bool: True si la contraseña coincide
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashear contraseña
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        str: Hash de la contraseña
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validar fortaleza de contraseña según política configurada
    
    Args:
        password: Contraseña a validar
        
    Returns:
        tuple: (es_valida, mensaje_error)
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"La contraseña debe tener al menos {settings.PASSWORD_MIN_LENGTH} caracteres"
    
    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        return False, "La contraseña debe contener al menos una letra mayúscula"
    
    if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        return False, "La contraseña debe contener al menos una letra minúscula"
    
    if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        return False, "La contraseña debe contener al menos un número"
    
    if settings.PASSWORD_REQUIRE_SPECIAL_CHAR and not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/@]', password):
        return False, "La contraseña debe contener al menos un carácter especial (!@#$%^&*...)"
    
    return True, "Contraseña válida"


# ============================================
# JWT TOKENS
# ============================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crear token JWT
    
    Args:
        data: Datos a incluir en el token (user_id, username, email, etc.)
        expires_delta: Tiempo de expiración personalizado
        
    Returns:
        str: Token JWT firmado
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decodificar y validar token JWT
    
    Args:
        token: Token JWT a validar
        
    Returns:
        dict: Datos del token decodificado
        
    Raises:
        HTTPException: Si el token es inválido o expiró
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado. Por favor inicia sesión nuevamente"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )


# ============================================
# SANITIZACIÓN DE INPUTS
# ============================================

def sanitize_input(text: str, max_length: int = 100) -> str:
    """
    Sanitizar input del usuario para prevenir XSS y otros ataques
    
    Args:
        text: Texto a sanitizar
        max_length: Longitud máxima permitida
        
    Returns:
        str: Texto sanitizado
    """
    if not text:
        return ""
    
    # Remover espacios al inicio y final
    text = text.strip()
    
    # Remover caracteres potencialmente peligrosos para XSS
    text = re.sub(r'[<>\'"]', '', text)
    
    # Limitar longitud para prevenir ataques de overflow
    return text[:max_length]


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validar formato de username
    
    Args:
        username: Username a validar
        
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    if not username or not username.strip():
        return False, "El username no puede estar vacío"
    
    username = username.strip()
    
    if len(username) < 3:
        return False, "El username debe tener al menos 3 caracteres"
    
    if len(username) > 50:
        return False, "El username no puede exceder 50 caracteres"
    
    # Solo letras, números, guiones y guión bajo
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "El username solo puede contener letras, números, guiones y guión bajo"
    
    return True, "Username válido"


def validate_email(email: str) -> tuple[bool, str]:
    """
    Validar formato de email
    
    Args:
        email: Email a validar
        
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    if not email or not email.strip():
        return False, "El email no puede estar vacío"
    
    email = email.strip().lower()
    
    # Regex para validar email
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_regex, email):
        return False, "Formato de email inválido"
    
    if len(email) > 100:
        return False, "El email no puede exceder 100 caracteres"
    
    return True, "Email válido"


# ============================================
# LOGGING DE SEGURIDAD
# ============================================

def log_security_event(
    event_type: str, 
    username: str, 
    details: str, 
    success: bool = True,
    ip_address: Optional[str] = None
):
    """
    Registrar eventos de seguridad en logs
    
    Args:
        event_type: Tipo de evento (LOGIN, LOGOUT, PASSWORD_CHANGE, etc.)
        username: Usuario relacionado con el evento
        details: Detalles adicionales del evento
        success: Si la operación fue exitosa
        ip_address: Dirección IP del cliente (opcional)
    """
    timestamp = datetime.now().isoformat()
    status_icon = "✅" if success else "❌"
    ip_info = f" - IP: {ip_address}" if ip_address else ""
    
    log_message = f"{status_icon} [{timestamp}] {event_type} - Usuario: {username}{ip_info} - {details}"
    print(log_message)
    
    # TODO: Aquí podrías guardar en una tabla de auditoría en la BD
    # Ejemplo:
    # audit_log = AuditLog(
    #     event_type=event_type,
    #     username=username,
    #     details=details,
    #     success=success,
    #     ip_address=ip_address,
    #     timestamp=datetime.now()
    # )
    # db.add(audit_log)
    # db.commit()


# ============================================
# VALIDACIÓN DE INTENTOS DE LOGIN
# ============================================

def should_lockout_user(intentos_fallidos: int) -> bool:
    """
    Determinar si un usuario debe ser bloqueado
    
    Args:
        intentos_fallidos: Número de intentos fallidos
        
    Returns:
        bool: True si debe ser bloqueado
    """
    return intentos_fallidos >= settings.MAX_LOGIN_ATTEMPTS


def calculate_lockout_until() -> datetime:
    """
    Calcular fecha/hora hasta cuando un usuario estará bloqueado
    
    Returns:
        datetime: Fecha/hora de fin del bloqueo
    """
    return datetime.now() + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)


def is_user_locked_out(fecha_bloqueo: Optional[datetime], lockout_duration_minutes: int = None) -> bool:
    """
    Verificar si un usuario sigue bloqueado
    
    Args:
        fecha_bloqueo: Fecha en que fue bloqueado
        lockout_duration_minutes: Duración del bloqueo (usa config por defecto si no se proporciona)
        
    Returns:
        bool: True si aún está bloqueado
    """
    if not fecha_bloqueo:
        return False
    
    duration = lockout_duration_minutes or settings.LOCKOUT_DURATION_MINUTES
    lockout_until = fecha_bloqueo + timedelta(minutes=duration)
    
    return datetime.now() < lockout_until


# ============================================
# UTILIDADES DE SEGURIDAD
# ============================================

def mask_email(email: str) -> str:
    """
    Enmascarar email para logs (privacidad)
    
    Args:
        email: Email a enmascarar
        
    Returns:
        str: Email enmascarado (ej: j***@example.com)
    """
    if not email or '@' not in email:
        return "***"
    
    username, domain = email.split('@')
    masked_username = username[0] + '***' if len(username) > 1 else '***'
    return f"{masked_username}@{domain}"


def get_client_ip(request) -> str:
    """
    Obtener IP del cliente considerando proxies
    
    Args:
        request: Request de FastAPI
        
    Returns:
        str: Dirección IP del cliente
    """
    # Verificar headers de proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback a la IP directa
    return request.client.host if request.client else "unknown"