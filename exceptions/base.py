from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Excepción base para todas las excepciones de la API"""
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(BaseAPIException):
    """Recurso no encontrado"""
    def __init__(self, resource: str, identifier: str | int | None = None):
        if identifier is None:
            # Si solo se pasa un argumento, se trata como mensaje directo
            detail = resource
        else:
            # Si se pasan dos argumentos, formatea el mensaje
            detail = f"{resource} con identificador '{identifier}' no encontrado"
        super().__init__(
            detail=detail,
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


class ConflictException(BaseAPIException):
    """Conflicto con recurso existente"""
    def __init__(self, detail: str):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_409_CONFLICT
        )


class BadRequestException(BaseAPIException):
    """Excepción para peticiones incorrectas"""
    def __init__(self, detail: str = "Petición incorrecta"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class DatabaseException(BaseAPIException):
    """Error de base de datos"""
    def __init__(self, detail: str = "Error en la base de datos"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )