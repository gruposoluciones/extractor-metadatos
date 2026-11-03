#!/usr/bin/env python3
"""Compila Extractor de Metadatos para Windows y macOS desde un único punto.

PyInstaller no compila de forma cruzada: el .exe se genera en Windows y el
binario de macOS, en macOS. Este script detecta la plataforma y produce el
paquete correspondiente (instalable y portable) más su archivo comprimido.
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
NAME = "ExtractorMetadatos"
APP_NAME = "Extractor de Metadatos"
BUNDLE = f"{APP_NAME}.app"

COLLECT_ALL = ("openpyxl", "docx", "pypdf", "defusedxml", "xlrd", "olefile", "charset_normalizer")
COLLECT_SUBMODULES = ("PIL",)
EXCLUDES = (
    "tkinter", "PIL.ImageTk", "numpy", "matplotlib", "pandas", "scipy", "pyarrow",
    "sqlalchemy", "psycopg", "psycopg2", "IPython", "jedi", "jinja2", "notebook", "pytest",
)
EXTRA_WINDOWS = (
    "README.md", "AGENTS.md",
    "instalar.ps1", "INSTALAR.bat", "DESINSTALAR.bat", "desinstalar.ps1",
)
EXTRA_MACOS = (
    "README.md", "AGENTS.md",
    "instalar.sh", "INSTALAR.command", "DESINSTALAR.command", "desinstalar.sh",
)


def extras_for_platform() -> tuple[str, ...]:
    """Devuelve los archivos de instalación que corresponden al sistema actual."""
    return EXTRA_MACOS if sys.platform == "darwin" else EXTRA_WINDOWS


def resolve(name: str) -> Path | None:
    """Localiza un archivo auxiliar en la raíz del proyecto o en scripts/."""
    for base in (ROOT, SCRIPTS):
        candidate = base / name
        if candidate.exists():
            return candidate
    return None

LAUNCHER = """#!/bin/sh
# Lanzador del paquete .app: inicia el servidor local y abre el navegador.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
exec "$HERE/../Resources/app/{name}" "$@"
"""

INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>{app}</string>
    <key>CFBundleDisplayName</key><string>{app}</string>
    <key>CFBundleIdentifier</key><string>com.diviac.extractormetadatos</string>
    <key>CFBundleVersion</key><string>2.0</string>
    <key>CFBundleShortVersionString</key><string>2.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>{name}</string>
    <key>CFBundleIconFile</key><string>icono</string>
    <key>LSMinimumSystemVersion</key><string>11.0</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
"""


def run(command: list[str]) -> None:
    """Ejecuta un comando mostrándolo y aborta si falla."""
    print(">>", " ".join(command), flush=True)
    subprocess.run(command, check=True, cwd=ROOT)


def ensure_icon() -> Path:
    """Genera o actualiza el .icns de macOS a partir del .ico."""
    ico = ROOT / "assets" / "icono.ico"
    icns = ROOT / "assets" / "icono.icns"
    needs_build = ico.exists() and (
        not icns.exists() or ico.stat().st_mtime > icns.stat().st_mtime
    )
    if needs_build:
        from PIL import Image

        image = Image.open(ico)
        image.load()
        icns.parent.mkdir(parents=True, exist_ok=True)
        image.save(icns, format="ICNS")
        print(f"icono .icns actualizado: {icns.name}")
    return icns


def freeze(onefile: bool) -> None:
    """Congela la aplicación con PyInstaller para la plataforma actual."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        raise SystemExit("Falta PyInstaller. Instálalo con: python -m pip install pyinstaller")

    icon = ensure_icon() if sys.platform == "darwin" else ROOT / "assets" / "icono.ico"
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--noupx",
        "--name", NAME,
        "--onefile" if onefile else "--onedir",
        "--console",
        "--icon", str(icon),
    ]
    for module in COLLECT_ALL:
        command += ["--collect-all", module]
    for module in COLLECT_SUBMODULES:
        command += ["--collect-submodules", module]
    for module in EXCLUDES:
        command += ["--exclude-module", module]
    command += ["--paths", str(ROOT / "src"), "--specpath", str(BUILD)]
    command.append(str(SCRIPTS / "entry.py"))
    run(command)


def copy_extras(target: Path) -> None:
    """Copia documentación y scripts de instalación junto al ejecutable."""
    target.mkdir(parents=True, exist_ok=True)
    for name in extras_for_platform():
        source = resolve(name)
        if source:
            shutil.copy2(source, target / name)


def zip_tree(
    source: Path,
    dest: Path,
    arc_root: str | None = None,
    executables: frozenset[str] | set[str] = frozenset(),
) -> None:
    """Comprime un árbol fijando permisos POSIX (necesario para el .app de macOS).

    Los permisos se deducen del contenido y no del sistema de archivos, porque
    al compilar en Windows `chmod` no marca el bit de ejecución.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            arcname = str(Path(arc_root) / relative if arc_root else relative).replace("\\", "/")
            info = zipfile.ZipInfo(arcname)
            info.date_time = time.localtime(path.stat().st_mtime)[:6]
            if path.is_dir():
                info.filename = arcname.rstrip("/") + "/"
                info.external_attr = (0o755 << 16) | 0x10
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, b"")
                continue
            executable = (
                arcname in executables
                or arcname.endswith((".sh", ".command"))
                or "/Contents/MacOS/" in arcname
            )
            info.external_attr = ((0o755 if executable else 0o644) << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            with path.open("rb") as source_file, archive.open(info, "w") as target_file:
                shutil.copyfileobj(source_file, target_file)


def build_app_bundle(payload: Path) -> Path:
    """Envuelve el ejecutable en un paquete .app con lanzador e icono."""
    bundle = DIST / BUNDLE
    if bundle.exists():
        shutil.rmtree(bundle)
    macos = bundle / "Contents" / "MacOS"
    resources = bundle / "Contents" / "Resources"
    macos.mkdir(parents=True)
    resources.mkdir(parents=True)

    shutil.copytree(payload, resources / "app")

    launcher = macos / NAME
    launcher.write_text(LAUNCHER.format(name=NAME), encoding="utf-8")
    launcher.chmod(0o755)

    icon = ensure_icon()
    if icon.exists():
        shutil.copy2(icon, resources / "icono.icns")
    (bundle / "Contents" / "Info.plist").write_text(
        INFO_PLIST.format(app=APP_NAME, name=NAME), encoding="utf-8"
    )
    return bundle


def make_dmg(app: Path) -> Path | None:
    """Crea un .dmg con la app y los scripts, si hdiutil está disponible."""
    if not shutil.which("hdiutil"):
        return None
    staging = BUILD / "dmg"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copytree(app, staging / BUNDLE, symlinks=True)
    for name in EXTRA_MACOS:
        if name.endswith((".sh", ".command")):
            source = resolve(name)
            if source:
                shutil.copy2(source, staging / name)
    link = staging / "Applications"
    if not link.exists():
        link.symlink_to("/Applications")
    dmg = DIST / f"{NAME}-{sys.platform}.dmg"
    if dmg.exists():
        dmg.unlink()
    run(["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", str(staging),
         "-ov", "-format", "UDZO", str(dmg)])
    return dmg


def build_windows(onefile: bool) -> list[Path]:
    """Empaqueta para Windows: carpeta con el .exe y ZIP portable."""
    if onefile:
        executable = DIST / f"{NAME}.exe"
        if not executable.exists():
            raise SystemExit(f"No se generó el ejecutable esperado: {executable}")
        staging = BUILD / "zip"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        shutil.copy2(executable, staging / f"{NAME}.exe")
        for name in EXTRA_WINDOWS:
            source = resolve(name)
            if source:
                shutil.copy2(source, staging / name)
        copy_extras(DIST)
        archive = DIST / f"{NAME}-portable-windows.zip"
        zip_tree(staging, archive)
        return [executable, archive]

    executable = DIST / NAME / f"{NAME}.exe"
    if not executable.exists():
        raise SystemExit(f"No se generó el ejecutable esperado: {executable}")
    copy_extras(DIST / NAME)
    archive = DIST / f"{NAME}-portable-windows.zip"
    zip_tree(DIST / NAME, archive)
    return [executable, archive]


def build_macos(onefile: bool) -> list[Path]:
    """Empaqueta para macOS: carpeta, .app, ZIP portable y DMG si es posible."""
    if onefile:
        binary = DIST / NAME
        if not binary.exists():
            raise SystemExit(f"No se generó el binario esperado: {binary}")
        payload = BUILD / "payload"
        if payload.exists():
            shutil.rmtree(payload)
        payload.mkdir(parents=True)
        shutil.copy2(binary, payload / NAME)
    else:
        payload = DIST / NAME
        binary = payload / NAME
        if not binary.exists():
            raise SystemExit(f"No se generó el binario esperado: {binary}")
    for script in ("instalar.sh", "INSTALAR.command", "DESINSTALAR.command", "desinstalar.sh"):
        path = resolve(script)
        if path:
            path.chmod(0o755)

    copy_extras(payload)
    bundle = build_app_bundle(payload)

    archive = DIST / f"{NAME}-portable-macos.zip"
    staging = BUILD / "zip"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copytree(bundle, staging / BUNDLE, symlinks=True)
    for name in EXTRA_MACOS:
        source = resolve(name)
        if source:
            shutil.copy2(source, staging / name)
    zip_tree(
        staging,
        archive,
        executables={
            f"{BUNDLE}/Contents/MacOS/{NAME}",
            f"{BUNDLE}/Contents/Resources/app/{NAME}",
        },
    )

    result = [bundle, archive]
    dmg = make_dmg(bundle)
    if dmg:
        result.append(dmg)
    return result


def check() -> int:
    """Comprueba el entorno de compilación sin compilar."""
    ok = True
    print(f"Plataforma: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python    : {sys.version.split()[0]}")
    try:
        import PyInstaller

        print(f"PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller: FALTA -> python -m pip install pyinstaller")
        ok = False
    for module in COLLECT_ALL:
        try:
            __import__(module)
        except ImportError:
            print(f"Dependencia ausente: {module}")
            ok = False
    icon = ROOT / "assets" / "icono.ico"
    print(f"Icono     : {'sí' if icon.exists() else 'NO'}")
    if sys.platform == "darwin":
        print(f"hdiutil   : {'sí' if shutil.which('hdiutil') else 'no (se omitirá el .dmg)'}")
    print("Entorno correcto." if ok else "Faltan dependencias.")
    return 0 if ok else 1


def main() -> int:
    """Punto de entrada de la compilación."""
    parser = argparse.ArgumentParser(description="Compila Extractor de Metadatos.")
    parser.add_argument("--onefile", action="store_true", help="Un único ejecutable")
    parser.add_argument("--check", action="store_true", help="Solo verifica el entorno")
    parser.add_argument("--install", action="store_true", help="Instala las dependencias antes de compilar")
    args = parser.parse_args()

    if args.check:
        return check()
    if args.install:
        run([sys.executable, "-m", "pip", "install", "--quiet", "-r", "requirements.txt"])
        run([sys.executable, "-m", "pip", "install", "--quiet", "pyinstaller"])

    for folder in (BUILD, DIST):
        if folder.exists():
            shutil.rmtree(folder)

    freeze(args.onefile)
    artifacts = build_macos(args.onefile) if sys.platform == "darwin" else build_windows(args.onefile)

    print("\n" + "=" * 60)
    for path in artifacts:
        size = path.stat().st_size if path.is_file() else sum(
            item.stat().st_size for item in path.rglob("*") if item.is_file()
        )
        print(f"{size / 1_048_576:8.1f} MB  {path.relative_to(ROOT)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
