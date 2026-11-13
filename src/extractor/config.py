"""Constantes de identidad y límites compartidos por el motor y las interfaces."""

from __future__ import annotations

__version__ = "2.0.0"

APP_NAME = "Extractor de Metadatos"
ORGANIZATION = "DIVIAC"
AUTHORS = "PeBe & DeepSeek"

MAX_FILE_SIZE = 40 * 1024 * 1024
MAX_REQUEST_SIZE = MAX_FILE_SIZE + 256 * 1024
MAX_CONCURRENT_REQUESTS = 4
REQUEST_TIMEOUT_SECONDS = 30
