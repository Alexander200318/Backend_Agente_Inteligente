from fastapi import HTTPException, status

class BaseAPIException(HTTPException):
    """Excepción base para todas las excepciones de la API"""
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundException(BaseAPIException):
    """Recurso no encontrado"""
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            detail=f"{resource} con identificador '{identifier}' no encontrado",
            status_code=status.HTTP_404_NOT_FOUND
        )

class AlreadyExistsException(BaseAPIException):
    """El recurso ya existe"""
    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            detail=f"{resource} con {field} '{value}' ya existe",
            status_code=status.HTTP_409_CONFLICT
        )

class ValidationException(BaseAPIException):
    """Error de validación de negocio"""
    def __init__(self, detail: str):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class UnauthorizedException(BaseAPIException):
    """Usuario no autorizado"""
    def __init__(self, detail: str = "No autorizado"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class ForbiddenException(BaseAPIException):
    """Acceso prohibido"""
    def __init__(self, detail: str = "Acceso denegado"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )

class DatabaseException(BaseAPIException):
    """Error de base de datos"""
    def __init__(self, detail: str = "Error en la base de datos"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class BaseException(HTTPException):
    """Excepción base personalizada"""
    def __init__(self, detail: str, status_code: int):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundException(BaseException):
    """Recurso no encontrado"""
    def __init__(self, entity: str = "Recurso", id_value = None):
        if id_value:
            detail = f"{entity} con ID {id_value} no encontrado"
        else:
            detail = f"{entity} no encontrado"
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class AlreadyExistsException(BaseException):
    """Recurso ya existe"""
    def __init__(self, entity: str, field: str, value):
        detail = f"{entity} con {field} '{value}' ya existe"
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)

class ValidationException(BaseException):
    """Error de validación de negocio"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)

class ConflictException(BaseException):
    """Conflicto con recurso existente"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)

class DatabaseException(BaseException):
    """Error de base de datos"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UnauthorizedException(BaseException):
    """No autorizado"""
    def __init__(self, detail: str = "No autorizado"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)

class ForbiddenException(BaseException):
    """Acceso prohibido"""
    def __init__(self, detail: str = "Acceso prohibido"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)

class BaseAPIException(Exception):
    """Excepción base para todas las excepciones personalizadas de la API"""
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail)


class NotFoundException(BaseAPIException):
    """Excepción cuando un recurso no se encuentra (404)"""
    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class BadRequestException(BaseAPIException):
    """Excepción para peticiones incorrectas (400)"""
    def __init__(self, detail: str = "Petición incorrecta"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class UnauthorizedException(BaseAPIException):
    """Excepción para autenticación fallida (401)"""
    def __init__(self, detail: str = "No autorizado"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(BaseAPIException):
    """Excepción cuando el usuario no tiene permisos (403)"""
    def __init__(self, detail: str = "Acceso prohibido"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class ConflictException(BaseAPIException):
    """Excepción para conflictos de datos (409)"""
    def __init__(self, detail: str = "Conflicto con el estado actual del recurso"):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class ValidationException(BaseAPIException):
    """Excepción para errores de validación (422)"""
    def __init__(self, detail: str = "Error de validación"):
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class DatabaseException(BaseAPIException):
    """Excepción para errores de base de datos (500)"""
    def __init__(self, detail: str = "Error en la base de datos"):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)