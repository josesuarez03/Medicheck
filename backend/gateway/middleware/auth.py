import os
from typing import Any

from fastapi import Header, HTTPException

try:
    from jose import JWTError, jwt
except Exception:  # pragma: no cover
    JWTError = Exception
    jwt = None


JWT_SECRET = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    if not token:
        raise HTTPException(status_code=401, detail="Token ausente.")
    if jwt is None or not JWT_SECRET:
        return {"raw_token": token}
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
