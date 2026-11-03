"""Extractor de Metadatos: motor de extracción y aplicaciones de consola y web."""

from __future__ import annotations

from .config import APP_NAME, AUTHORS, ORGANIZATION, __version__
from .engine import SUPPORTED_EXTENSIONS, extract_file

__all__ = [
    "APP_NAME",
    "AUTHORS",
    "ORGANIZATION",
    "SUPPORTED_EXTENSIONS",
    "__version__",
    "extract_file",
]
