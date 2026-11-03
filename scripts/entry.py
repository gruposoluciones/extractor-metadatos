"""Punto de entrada para el empaquetado con PyInstaller (usa --paths src)."""

from __future__ import annotations

from extractor.app import main

if __name__ == "__main__":
    raise SystemExit(main())
