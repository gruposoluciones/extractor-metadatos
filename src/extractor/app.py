#!/usr/bin/env python3
"""Punto de entrada único del ejecutable: interfaz web por omisión, CLI con rutas."""

from __future__ import annotations

import sys

from . import cli, web

WEB_FLAGS = ("web", "--port", "--no-browser")


def _console_title() -> None:
    """Fija el título de la ventana de consola en Windows."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleTitleW(f"{web.APP_NAME} - {web.ORGANIZATION}")
        except Exception:
            pass


def main() -> int:
    """Abre la interfaz web sin argumentos; delega en la CLI cuando recibe rutas."""
    args = sys.argv[1:]
    if not args or args[0] in WEB_FLAGS:
        if args and args[0] == "web":
            sys.argv = [sys.argv[0], *args[1:]]
        return web.main()
    return cli.main()


def _report_failure(code: int) -> None:
    """Avisa del fallo por el medio visible en cada plataforma."""
    if sys.platform == "darwin":
        try:
            import subprocess

            message = f"El programa terminó con el código {code}."
            subprocess.run(
                ["osascript", "-e",
                 f'display alert "{web.APP_NAME}" message "{message}" as critical'],
                check=False,
            )
            return
        except Exception:
            pass
    try:
        input(f"\nFinalizado con código {code}. Pulsa Enter para cerrar...")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    _console_title()
    try:
        code = main()
    except KeyboardInterrupt:
        code = 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 0
    if getattr(sys, "frozen", False) and code:
        _report_failure(code)
    raise SystemExit(code)
