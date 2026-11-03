"""Interfaz de línea de comandos del extractor de metadatos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import __version__
from .engine import discover_files, extract_file, write_results


def build_parser() -> argparse.ArgumentParser:
    """Construye el analizador de argumentos de la CLI."""
    parser = argparse.ArgumentParser(
        prog="extractor-metadatos",
        description="Extrae metadatos de archivos XLSX, XLS, DOCX, DOC, TXT, PDF e imágenes.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="Archivos o directorios que se analizarán.")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Busca archivos también en subdirectorios."
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("json", "csv"),
        default="json",
        help="Formato del resultado (por defecto: json).",
    )
    parser.add_argument("-o", "--output", type=Path, help="Guarda el resultado en este archivo.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ejecuta la extracción por lotes y devuelve el código de salida."""
    args = build_parser().parse_args(argv)
    files, discovery_errors = discover_files(args.paths, args.recursive)
    results = [extract_file(path) for path in files]
    for error in discovery_errors:
        print(f"Error: {error}", file=sys.stderr)
    for result in results:
        if result["error"]:
            print(f"Error al procesar {result['file']}: {result['error']}", file=sys.stderr)
    try:
        write_results(results, args.format, args.output)
    except OSError as exc:
        print(f"Error al guardar el resultado: {exc}", file=sys.stderr)
        return 2
    return 1 if discovery_errors or any(result["error"] for result in results) else 0
