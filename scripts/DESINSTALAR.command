#!/bin/bash
# Doble clic en Finder para desinstalar la aplicación en macOS.
cd "$(dirname "$0")" || exit 1
chmod +x ./desinstalar.sh 2>/dev/null
./desinstalar.sh
echo ""
read -r -p "Pulsa Enter para cerrar..." _
