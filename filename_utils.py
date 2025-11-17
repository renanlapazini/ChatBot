"""Ferramentas para sanitizar nomes e caminhos de arquivos."""

import os
import re
import unicodedata

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}

_INVALID_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_MULTI_UNDERSCORE = re.compile(r"_+")
_DASH_LIKE = ("–", "—", "−", "―", "‐")


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _sanitize_part(part: str, fallback: str) -> str:
    if not part:
        return fallback

    part = _strip_accents(part)
    for dash in _DASH_LIKE:
        part = part.replace(dash, "-")

    part = part.replace(" ", "_")
    part = part.replace("/", "_").replace("\\", "_")
    part = _INVALID_CHARS.sub("_", part)
    part = _MULTI_UNDERSCORE.sub("_", part)
    part = part.strip("._-")
    return part or fallback


def _ensure_safe_length(name: str, max_length: int = 255) -> str:
    if len(name) <= max_length:
        return name
    base, ext = os.path.splitext(name)
    allowed = max_length - len(ext)
    if allowed <= 0:
        return name[:max_length]
    return f"{base[:allowed]}{ext}"


def sanitize_filename(name: str, default: str = "arquivo") -> str:
    """Converte o nome recebido em um formato seguro para armazenamento."""
    if not isinstance(name, str):
        name = str(name or "")
    name = name.strip()
    if not name:
        name = default

    base, ext = os.path.splitext(name)
    sanitized_base = _sanitize_part(base or default, default)
    sanitized_ext = _sanitize_part(ext.lstrip("."), "")

    sanitized = sanitized_base
    if sanitized_ext:
        sanitized = f"{sanitized}.{sanitized_ext}"

    leading = sanitized.split(".")[0].upper()
    if leading in WINDOWS_RESERVED_NAMES:
        sanitized = f"{sanitized}_file"

    sanitized = _ensure_safe_length(sanitized)
    return sanitized or default


def sanitize_storage_path(path: str) -> str:
    """Sanitiza cada segmento de um caminho estilo storage (separado por /)."""
    if not isinstance(path, str):
        path = str(path or "")

    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return sanitize_filename("")

    sanitized_parts = [sanitize_filename(segment) for segment in parts]
    return "/".join(sanitized_parts)


__all__ = [
    "sanitize_filename",
    "sanitize_storage_path",
]
