#!/bin/sh
# Desinstala Extractor de Metadatos del perfil del usuario (macOS).
set -eu

APP="Extractor de Metadatos.app"
DESTINO="$HOME/Applications/$APP"

pkill -f "Extractor de Metadatos.app/Contents" 2>/dev/null || true
sleep 1

if [ -d "$DESTINO" ]; then
    rm -rf "$DESTINO"
fi

echo "Desinstalación completada."
