"""Autenticación local y configuración segura del administrador inicial."""
import hashlib
import hmac
import secrets
from typing import Optional, Tuple

from services.db_service import obtener_conexion


_ALGORITMO = "pbkdf2_sha256"
_ITERACIONES = 310_000


def hash_password(password: str) -> str:
    """Genera un hash PBKDF2 con sal aleatoria para una contraseña."""
    sal = secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), sal, _ITERACIONES
    )
    return f"{_ALGORITMO}${_ITERACIONES}${sal.hex()}${derivado.hex()}"


def verificar_password(password: str, hash_guardado: str) -> Tuple[bool, bool]:
    """Devuelve (válida, necesita_migración) para hashes nuevos y SHA-256 heredados."""
    if not hash_guardado:
        return False, False
    if hash_guardado.startswith(f"{_ALGORITMO}$"):
        try:
            algoritmo, iteraciones, sal_hex, hash_hex = hash_guardado.split("$", 3)
            if algoritmo != _ALGORITMO:
                return False, False
            derivado = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(sal_hex),
                int(iteraciones),
            )
            return hmac.compare_digest(derivado.hex(), hash_hex), False
        except (ValueError, TypeError):
            return False, False

    hash_heredado = hashlib.sha256(password.encode("utf-8")).hexdigest()
    valido = hmac.compare_digest(hash_heredado, hash_guardado)
    return valido, valido


def autenticar(usuario: str, password: str) -> Optional[tuple]:
    """Autentica usuario activo y migra su hash SHA-256 tras un acceso válido."""
    conn = obtener_conexion()
    try:
        fila = conn.execute("""
            SELECT id, usuario, nombre, rol, password
            FROM usuarios
            WHERE usuario = ? AND activo = 1
        """, (usuario,)).fetchone()
        if not fila:
            return None

        valido, necesita_migracion = verificar_password(password, fila[4])
        if not valido:
            return None
        if necesita_migracion:
            conn.execute(
                "UPDATE usuarios SET password = ? WHERE id = ?",
                (hash_password(password), fila[0]),
            )
            conn.commit()
        return fila[:4]
    finally:
        conn.close()
