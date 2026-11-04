"""Autenticación local y configuración segura del administrador inicial."""
import datetime
import hashlib
import hmac
import secrets
from typing import Optional, Tuple

from services.db_service import obtener_conexion


_ALGORITMO = "pbkdf2_sha256"
_ITERACIONES = 310_000
_LONGITUD_MINIMA = 12


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


def obtener_configuracion_administrador() -> Optional[dict]:
    """Retorna el administrador que requiere configuración inicial, si aplica."""
    conn = obtener_conexion()
    try:
        usuarios = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        administradores = conn.execute("""
            SELECT id, usuario, nombre, password
            FROM usuarios
            WHERE rol = 'admin' AND activo = 1
            ORDER BY CASE WHEN usuario = 'admin' THEN 0 ELSE 1 END, id
        """).fetchall()
    finally:
        conn.close()

    if not usuarios or not administradores:
        return {"id": None, "usuario": "admin", "nombre": "Administrador"}

    for admin in administradores:
        if admin[1] == "admin" and not admin[3].startswith(f"{_ALGORITMO}$"):
            return {"id": admin[0], "usuario": admin[1], "nombre": admin[2]}
    return None


def configurar_administrador(usuario: str, nombre: str, password: str) -> None:
    """Crea el primer administrador o reemplaza la credencial heredada conocida."""
    usuario = (usuario or "").strip()
    nombre = (nombre or "").strip()
    if not usuario or not nombre:
        raise ValueError("El usuario y el nombre del administrador son obligatorios.")
    if len(password) < _LONGITUD_MINIMA:
        raise ValueError(
            f"La contraseña debe tener al menos {_LONGITUD_MINIMA} caracteres."
        )

    conn = obtener_conexion()
    try:
        administradores_heredados = conn.execute("""
            SELECT id, password FROM usuarios
            WHERE usuario = 'admin' AND rol = 'admin' AND activo = 1
            ORDER BY id
        """).fetchall()
        admin_heredado = next(
            (
                admin for admin in administradores_heredados
                if not admin[1].startswith(f"{_ALGORITMO}$")
            ),
            None,
        )
        admin_existente = conn.execute("""
            SELECT id FROM usuarios WHERE usuario = ? AND id != ?
        """, (usuario, admin_heredado[0] if admin_heredado else -1)).fetchone()
        if admin_existente:
            raise ValueError("Ese nombre de usuario ya está registrado.")

        hash_nuevo = hash_password(password)
        if admin_heredado:
            conn.execute("""
                UPDATE usuarios
                SET usuario = ?, nombre = ?, password = ?
                WHERE id = ?
            """, (usuario, nombre, hash_nuevo, admin_heredado[0]))
        else:
            cantidad_admins = conn.execute(
                "SELECT COUNT(*) FROM usuarios WHERE rol = 'admin' AND activo = 1"
            ).fetchone()[0]
            if cantidad_admins:
                raise ValueError(
                    "Ya existe un administrador configurado; no se puede crear otro "
                    "desde la configuración inicial."
                )
            conn.execute("""
                INSERT INTO usuarios (usuario, password, nombre, rol, activo, fecha_creacion)
                VALUES (?, ?, ?, 'admin', 1, ?)
            """, (
                usuario, hash_nuevo, nombre, datetime.datetime.now().isoformat(),
            ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
