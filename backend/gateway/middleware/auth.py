import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Header, HTTPException

try:
    from jose import JWTError, jwt
except Exception:  # pragma: no cover
    JWTError = Exception
    jwt = None


JWT_SECRET = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# Vida util del token emitido por el gateway (modelo de identidad simple, sin
# contrasena): por defecto 24h. Ajustable via JWT_TTL_SECONDS.
JWT_TTL_SECONDS = int(os.getenv("JWT_TTL_SECONDS", str(60 * 60 * 24)))


def validate_jwt_config() -> None:
    """Falla rapido y explicito si la configuracion JWT no permite validar
    criptograficamente los tokens. Se invoca en el arranque del servicio para
    evitar degradar silenciosamente a un modo inseguro."""
    if jwt is None:
        raise RuntimeError(
            "python-jose no esta instalado: el gateway no puede emitir ni "
            "validar JWT de forma segura."
        )
    if not JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET_KEY/JWT_SECRET/SECRET_KEY no configurado: el gateway "
            "no puede firmar ni verificar JWT. Configure un secreto antes de arrancar."
        )


def create_access_token(user_id: str | None = None, *, extra_claims: dict[str, Any] | None = None) -> dict[str, Any]:
    """Emite un JWT de corta duracion para un user_id (modelo de identidad
    simple sin contrasena). Si no se provee user_id, se genera un UUID.

    El gateway es emisor y verificador consistente: usa la misma libreria
    (python-jose) y el mismo JWT_SECRET/JWT_ALGORITHM que decode_access_token.
    """
    # No degradar a inseguro: si no se puede firmar, rechazar.
    if jwt is None or not JWT_SECRET:
        raise HTTPException(status_code=503, detail="Servicio de autenticación no disponible.")

    resolved_user_id = str(user_id or uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=JWT_TTL_SECONDS)
    claims: dict[str, Any] = {
        "sub": resolved_user_id,
        "user_id": resolved_user_id,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if extra_claims:
        claims.update(extra_claims)
    token = jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {
        "access_token": token,
        "user_id": resolved_user_id,
        "token_type": "bearer",
        "expires_in": JWT_TTL_SECONDS,
    }


def decode_access_token(token: str) -> dict[str, Any]:
    if not token:
        raise HTTPException(status_code=401, detail="Token ausente.")
    # Correccion de seguridad: si no hay forma de validar criptograficamente el
    # token (libreria ausente o secreto sin configurar), se RECHAZA la peticion
    # en vez de aceptarla de forma optimista. El antiguo fallback que devolvia
    # {"raw_token": token} aceptaba cualquier string como token valido sin
    # verificar firma ni expiracion.
    if jwt is None or not JWT_SECRET:
        raise HTTPException(status_code=401, detail="Servicio de autenticación no disponible.")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Token inválido.") from exc
    payload["raw_token"] = token
    return payload


async def get_bearer_token(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Authorization header inválido.")
    return decode_access_token(token)
