#!/bin/bash
# Doble clic en Finder para instalar la aplicación en macOS.
cd "$(dirname "$0")" || exit 1
chmod +x ./instalar.sh 2>/dev/null
./instalar.sh
echo ""
read -r -p "Pulsa Enter para cerrar..." _
