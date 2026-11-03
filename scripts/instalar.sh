#!/bin/sh
# Instala Extractor de Metadatos en el perfil del usuario (macOS, sin sudo).
set -eu

APP="Extractor de Metadatos.app"
AQUI="$(cd "$(dirname "$0")" && pwd)"
DESTINO="$HOME/Applications"

ORIGEN=""
for candidato in "$AQUI" "$AQUI/../dist" "$AQUI/dist"; do
    if [ -d "$candidato/$APP" ]; then
        ORIGEN="$candidato/$APP"
        break
    fi
done

if [ -z "$ORIGEN" ]; then
    echo "No se encontró \"$APP\"." >&2
    echo "Ejecuta antes:  python3 scripts/build.py" >&2
    exit 1
fi

echo "Instalando desde: $ORIGEN"

# Evita borrar la propia carpeta si el instalador se ejecuta desde una instalación.
if [ "$(cd "$ORIGEN" && pwd)" = "$(cd "$DESTINO" 2>/dev/null && pwd || echo "")" ]; then
    echo "La aplicación ya está instalada en esa carpeta."
    exit 0
fi

# Cierra una instancia previa si está abierta.
pkill -f "Extractor de Metadatos.app/Contents" 2>/dev/null || true

mkdir -p "$DESTINO"
rm -rf "$DESTINO/$APP"
if command -v ditto >/dev/null 2>&1; then
    ditto "$ORIGEN" "$DESTINO/$APP"
else
    cp -R "$ORIGEN" "$DESTINO/$APP"
fi

# Elimina la marca de cuarentena si el paquete llegó por internet.
xattr -dr com.apple.quarantine "$DESTINO/$APP" 2>/dev/null || true

echo ""
echo "Instalado en: $DESTINO/$APP"
echo "Ábrelo desde Launchpad, Finder o Spotlight: «Extractor de Metadatos»."
