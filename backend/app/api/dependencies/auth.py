from fastapi import HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import verify_jwt_token
from app.core.config import settings
from app.database.connection import get_db

bearer_scheme = HTTPBearer(auto_error=False)

def obtener_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Extrae y valida el token JWT del header Authorization.
    Lanza 401 si el token es ausente o inválido.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    # Verificamos la firma y expiración usando la utilidad del proyecto.
    try:
        payload = verify_jwt_token(token, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    # Devolvemos el token para casos donde el endpoint necesita solo el string.
    return token

# Dependency to obtain DB session with the test DB when needed (used in tests).
async def get_test_db() -> Session:
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()
