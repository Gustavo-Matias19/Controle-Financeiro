
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status


SECRET_KEY = os.getenv("SECRET_KEY", "")

if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "Configure SECRET_KEY com pelo menos 32 caracteres no .env."
    )

ALGORITHM = "HS256"
ITERATIONS = 600_000


def hash_senha(senha: str) -> str:
    salt = os.urandom(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode(),
        salt,
        ITERATIONS
    )

    return (
        f"pbkdf2_sha256${ITERATIONS}$"
        f"{base64.b64encode(salt).decode()}$"
        f"{base64.b64encode(digest).decode()}"
    )


def conferir_senha(senha: str, armazenada: str) -> bool:
    try:
        algoritmo, ciclos, salt, digest = armazenada.split("$")

        if algoritmo != "pbkdf2_sha256":
            return False

        esperado = base64.b64decode(digest)

        calculado = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode(),
            base64.b64decode(salt),
            int(ciclos)
        )

        return hmac.compare_digest(calculado, esperado)

    except (ValueError, TypeError):
        return False


def criar_token(usuario_id: int) -> str:
    expiracao = datetime.now(timezone.utc) + timedelta(hours=2)

    return jwt.encode(
        {"sub": str(usuario_id), "exp": expiracao},
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def ler_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return int(payload["sub"])

    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )
