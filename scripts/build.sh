#!/bin/sh
# Compila Extractor de Metadatos en macOS delegando en build.py.
set -eu
cd "$(dirname "$0")"
exec python3 build.py "$@"
