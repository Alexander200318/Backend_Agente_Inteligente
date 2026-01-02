# ============================================
# AUTENTICACIÓN JWT - DEPENDENCY PARA FASTAPI
# ============================================
# core/security.py
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import re
from core.config import settings
from datetime import datetime, timedelta
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ============================================
# CONTRASEÑAS
# ============================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashear contraseña"""
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validar fortaleza de contraseña según política configurada"""
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
    """Crear token JWT"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decodificar y validar token JWT"""
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
# AUTENTICACIÓN - DEPENDENCIES
# ============================================

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Obtener usuario actual desde el token JWT
    
    Returns:
        dict: Datos del usuario {id_usuario, username, email, rol, etc.}
    """
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        
        if not payload.get("id_usuario"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: falta id_usuario"
            )
        
        return payload
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar las credenciales"
        )


def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Verificar que el usuario actual esté activo"""
    if not current_user.get("activo", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacte al administrador"
        )
    return current_user


def require_role(allowed_roles: list[str]):
    """Dependency factory para verificar roles específicos"""
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("rol", "")
        
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de estos roles: {', '.join(allowed_roles)}"
            )
        
        return current_user
    
    return role_checker


# ============================================
# SANITIZACIÓN DE INPUTS
# ============================================

def sanitize_input(text: str, max_length: int = 100) -> str:
    """Sanitizar input del usuario para prevenir XSS"""
    if not text:
        return ""
    
    text = text.strip()
    text = re.sub(r'[<>\'"]', '', text)
    return text[:max_length]


def validate_username(username: str) -> tuple[bool, str]:
    """Validar formato de username"""
    if not username or not username.strip():
        return False, "El username no puede estar vacío"
    
    username = username.strip()
    
    if len(username) < 3:
        return False, "El username debe tener al menos 3 caracteres"
    
    if len(username) > 50:
        return False, "El username no puede exceder 50 caracteres"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "El username solo puede contener letras, números, guiones y guión bajo"
    
    return True, "Username válido"


def validate_email(email: str) -> tuple[bool, str]:
    """Validar formato de email"""
    if not email or not email.strip():
        return False, "El email no puede estar vacío"
    
    email = email.strip().lower()
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_regex, email):
        return False, "Formato de email inválido"
    
    if len(email) > 100:
        return False, "El email no puede exceder 100 caracteres"
    
    return True, "Email válido"

# ============================================
# VERIFICACIÓN DE ROLES MÚLTIPLES
# ============================================

def require_authenticated_user(current_user: dict = Depends(get_current_active_user)) -> dict:
    """
    Permitir cualquier usuario autenticado y activo.
    Uso: usuario = Depends(require_authenticated_user)
    """
    return current_user


def require_admin_funcionario_or_superadmin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Verificar que el usuario sea SuperAdmin, Admin o Funcionario.
    Básicamente, cualquier usuario autenticado con rol válido.
    Uso: usuario = Depends(require_admin_funcionario_or_superadmin)
    """
    # Verificar que tenga al menos uno de los roles válidos
    id_rol = current_user.get("id_rol")
    
    # Roles permitidos: 1=SuperAdmin, 2=Admin, 3=Funcionario
    if id_rol not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. No tienes permisos para realizar esta acción"
        )
    
    return current_user


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
    """Registrar eventos de seguridad en logs"""
    timestamp = datetime.now().isoformat()
    status_icon = "✅" if success else "❌"
    ip_info = f" - IP: {ip_address}" if ip_address else ""
    
    log_message = f"{status_icon} [{timestamp}] {event_type} - Usuario: {username}{ip_info} - {details}"
    print(log_message)


def should_lockout_user(intentos_fallidos: int) -> bool:
    """Determinar si un usuario debe ser bloqueado"""
    return intentos_fallidos >= settings.MAX_LOGIN_ATTEMPTS


def calculate_lockout_until() -> datetime:
    """Calcular fecha/hora hasta cuando un usuario estará bloqueado"""
    return datetime.now() + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)


def is_user_locked_out(fecha_bloqueo: Optional[datetime], lockout_duration_minutes: int = None) -> bool:
    """Verificar si un usuario sigue bloqueado"""
    if not fecha_bloqueo:
        return False
    
    duration = lockout_duration_minutes or settings.LOCKOUT_DURATION_MINUTES
    lockout_until = fecha_bloqueo + timedelta(minutes=duration)
    
    return datetime.now() < lockout_until


def mask_email(email: str) -> str:
    """Enmascarar email para logs (privacidad)"""
    if not email or '@' not in email:
        return "***"
    
    username, domain = email.split('@')
    masked_username = username[0] + '***' if len(username) > 1 else '***'
    return f"{masked_username}@{domain}"


def get_client_ip(request) -> str:
    """Obtener IP del cliente considerando proxies"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"

# ============================================
# CONFIGURACIÓN DE SLIDING EXPIRATION
# ============================================
SLIDING_TOKEN_RENEW_THRESHOLD_MINUTES = 5  # Renovar si quedan menos de 5 min
SLIDING_TOKEN_MAX_LIFETIME_HOURS = 8       # Máximo 8 horas de vida total

def should_renew_token(payload: dict) -> bool:
    """
    Determinar si un token debe renovarse.
    Se renueva si quedan menos de 5 minutos para expirar.
    """
    try:
        exp = payload.get("exp")
        if not exp:
            return False
        
        expiration_time = datetime.fromtimestamp(exp)
        time_remaining = expiration_time - datetime.utcnow()
        
        # Renovar si quedan menos de 5 minutos
        return time_remaining.total_seconds() < (SLIDING_TOKEN_RENEW_THRESHOLD_MINUTES * 60)
    except:
        return False


def create_sliding_token(data: dict, original_iat: Optional[int] = None) -> str:
    """
    Crear token con sliding expiration.
    Mantiene el 'iat' (issued at) original para controlar la vida máxima.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    
    # Si es un token renovado, mantener el iat original
    if original_iat:
        issued_at = datetime.fromtimestamp(original_iat)
        
        # Verificar que no exceda la vida máxima (8 horas)
        max_lifetime = timedelta(hours=SLIDING_TOKEN_MAX_LIFETIME_HOURS)
        if now - issued_at > max_lifetime:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión expirada. Por favor inicia sesión nuevamente"
            )
        
        to_encode["iat"] = original_iat
    else:
        # Token nuevo
        to_encode["iat"] = int(now.timestamp())
    
    # Establecer nueva expiración (30 minutos desde ahora)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = int(expire.timestamp())
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt