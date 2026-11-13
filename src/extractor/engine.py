#!/usr/bin/env python3
"""Extrae metadatos de archivos XLSX, XLS, DOCX, DOC, TXT y PDF."""

from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import os
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .imagenes import COMPOUND_SUFFIXES, IMAGE_EXTENSIONS, analyze_image, detect_image, is_image

DOCUMENT_EXTENSIONS = {".xlsx", ".xls", ".doc", ".docx", ".txt", ".pdf"}
OFFICE_EXTENSIONS = {".xlsx", ".xls", ".doc", ".docx"}
SUPPORTED_EXTENSIONS = DOCUMENT_EXTENSIONS | set(IMAGE_EXTENSIONS)


def json_value(value: Any) -> Any:
    """Convierte valores de bibliotecas de documentos a tipos serializables."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def nonempty_fields(source: Any, fields: dict[str, str]) -> dict[str, Any]:
    """Copia solo los atributos con contenido, renombrados según el contrato."""
    result: dict[str, Any] = {}
    for output_name, source_name in fields.items():
        value = getattr(source, source_name, None)
        if value not in (None, ""):
            result[output_name] = json_value(value)
    return result


def is_supported_name(name: str) -> bool:
    """Indica si el nombre tiene extensión admitida, incluidos sufijos compuestos."""
    lower = name.lower()
    return lower.endswith(COMPOUND_SUFFIXES) or Path(lower).suffix in SUPPORTED_EXTENSIONS


def sha256_digest(path: Path) -> str:
    """Calcula el SHA-256 del archivo por bloques, sin cargarlo en memoria."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_metadata(path: Path) -> dict[str, Any]:
    """Obtiene nombre, tipo MIME, tamaño, huella SHA-256 y fechas del archivo."""
    stat = path.stat()
    # st_birthtime es la creación real donde existe; en Windows se usa ctime.
    created = getattr(stat, "st_birthtime", stat.st_ctime)
    return {
        "name": path.name,
        "extension": path.suffix.lower(),
        "mime_type": mimetypes.guess_type(path.name)[0],
        "size_bytes": stat.st_size,
        "sha256": sha256_digest(path),
        "created": datetime.fromtimestamp(created).astimezone().isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
    }


def office_metadata(path: Path) -> dict[str, Any]:
    """Extrae propiedades de XLSX, DOCX, XLS (binario o SpreadsheetML) y DOC."""
    suffix = path.suffix.lower()

    if suffix == ".xlsx":
        try:
            from openpyxl import load_workbook
            from openpyxl.utils.exceptions import InvalidFileException
        except ImportError as exc:
            raise RuntimeError(
                "Falta openpyxl. Instala las dependencias con 'pip install -r metadatos/requirements.txt'."
            ) from exc
        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
            try:
                result = nonempty_fields(
                    workbook.properties,
                    {
                        "title": "title",
                        "subject": "subject",
                        "creator": "creator",
                        "keywords": "keywords",
                        "description": "description",
                        "last_modified_by": "lastModifiedBy",
                        "created": "created",
                        "modified": "modified",
                        "category": "category",
                        "revision": "revision",
                        "identifier": "identifier",
                        "language": "language",
                    },
                )
                sheets = [
                    {
                        "name": sheet.title,
                        "visibility": sheet.sheet_state,
                        "rows": sheet.max_row,
                        "columns": sheet.max_column,
                    }
                    for sheet in workbook.worksheets
                ]
                result.update(
                    {
                        "sheet_count": len(sheets),
                        "hidden_sheet_count": sum(
                            1 for sheet in sheets if sheet["visibility"] != "visible"
                        ),
                        "sheets": sheets,
                        "defined_name_count": len(workbook.defined_names),
                    }
                )
                return result
            finally:
                workbook.close()
        except (
            OSError,
            ValueError,
            KeyError,
            zipfile.BadZipFile,
            ET.ParseError,
            InvalidFileException,
        ) as exc:
            raise RuntimeError(f"No se pudo leer el archivo XLSX: {exc}") from exc

    if suffix == ".docx":
        try:
            from docx import Document
            from docx.opc.exceptions import PackageNotFoundError
        except ImportError as exc:
            raise RuntimeError(
                "Falta python-docx. Instala las dependencias con 'pip install -r metadatos/requirements.txt'."
            ) from exc
        try:
            document = Document(path)
            properties = document.core_properties
            result = nonempty_fields(
                properties,
                {
                    "title": "title",
                    "subject": "subject",
                    "author": "author",
                    "keywords": "keywords",
                    "comments": "comments",
                    "last_modified_by": "last_modified_by",
                    "created": "created",
                    "modified": "modified",
                    "category": "category",
                    "revision": "revision",
                    "identifier": "identifier",
                    "language": "language",
                },
            )
            paragraphs = document.paragraphs
            table_text = [
                cell.text
                for table in document.tables
                for row in table.rows
                for cell in row.cells
            ]
            result.update(
                {
                    "paragraph_count": len(paragraphs),
                    "nonempty_paragraph_count": sum(
                        bool(paragraph.text.strip()) for paragraph in paragraphs
                    ),
                    "heading_count": sum(
                        1
                        for paragraph in paragraphs
                        if paragraph.style is not None
                        and paragraph.style.name.startswith("Heading")
                    ),
                    "table_count": len(document.tables),
                    "table_characters": sum(len(text) for text in table_text),
                    "section_count": len(document.sections),
                    "text_characters": sum(len(paragraph.text) for paragraph in paragraphs)
                    + sum(len(text) for text in table_text),
                    "section_layouts": [
                        {
                            "width_inches": round(section.page_width / 914400, 2),
                            "height_inches": round(section.page_height / 914400, 2),
                            "orientation": "landscape"
                            if section.page_width > section.page_height
                            else "portrait",
                        }
                        for section in document.sections
                    ],
                    "headers_present": any(
                        paragraph.text.strip()
                        for section in document.sections
                        for paragraph in section.header.paragraphs
                    ),
                    "footers_present": any(
                        paragraph.text.strip()
                        for section in document.sections
                        for paragraph in section.footer.paragraphs
                    ),
                }
            )
            return result
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError, PackageNotFoundError) as exc:
            raise RuntimeError(f"No se pudo leer el archivo DOCX: {exc}") from exc

    if suffix == ".xls":
        with path.open("rb") as source:
            signature = source.read(256).lstrip(b"\xef\xbb\xbf \t\r\n")
        if signature.startswith(b"<?xml") or signature.startswith(b"<Workbook"):
            return spreadsheetml_metadata(path)
        return binary_xls_metadata(path)

    return binary_doc_metadata(path)


def binary_doc_metadata(path: Path) -> dict[str, Any]:
    """Analiza propiedades OLE2 de documentos Word heredados (.doc)."""
    try:
        import olefile
    except ImportError as exc:
        raise RuntimeError(
            "Falta olefile. Instala las dependencias con 'pip install -r metadatos/requirements.txt'."
        ) from exc
    try:
        with olefile.OleFileIO(path) as document:
            result = nonempty_fields(
                document.get_metadata(),
                {
                    "title": "title",
                    "subject": "subject",
                    "author": "author",
                    "keywords": "keywords",
                    "comments": "comments",
                    "template": "template",
                    "last_modified_by": "last_saved_by",
                    "revision": "revision_number",
                    "created": "create_time",
                    "modified": "last_saved_time",
                    "creating_application": "creating_application",
                    "pages": "num_pages",
                    "words": "num_words",
                    "characters": "num_chars",
                },
            )
            streams = document.listdir()
            result["compound_streams"] = [
                {"path": "/".join(stream), "size_bytes": document.get_size(stream)}
                for stream in streams
            ]
            result["compound_stream_count"] = len(streams)
            return result
    except OSError as exc:
        raise RuntimeError(f"No se pudo leer el archivo Office antiguo: {exc}") from exc


def binary_xls_metadata(path: Path) -> dict[str, Any]:
    """Analiza hojas y visibilidad de libros Excel BIFF heredados (.xls)."""
    try:
        import xlrd
        from xlrd.biffh import XLRDError
    except ImportError as exc:
        raise RuntimeError(
            "Falta xlrd. Instala las dependencias con 'pip install -r metadatos/requirements.txt'."
        ) from exc
    try:
        workbook = xlrd.open_workbook(path, on_demand=True)
        try:
            sheets = [
                {
                    "name": sheet.name,
                    "visibility": "visible" if sheet.visibility == 0 else "hidden",
                    "rows": sheet.nrows,
                    "columns": sheet.ncols,
                }
                for sheet in workbook.sheets()
            ]
            return {
                "sheet_count": len(sheets),
                "hidden_sheet_count": sum(1 for sheet in sheets if sheet["visibility"] != "visible"),
                "sheets": sheets,
                "date_mode": workbook.datemode,
            }
        finally:
            workbook.release_resources()
    except (OSError, XLRDError, ValueError) as exc:
        raise RuntimeError(f"No se pudo leer el archivo XLS: {exc}") from exc


def spreadsheetml_metadata(path: Path) -> dict[str, Any]:
    """Lee propiedades y hojas de libros XLS guardados como SpreadsheetML."""
    try:
        from defusedxml import ElementTree
    except ImportError as exc:
        raise RuntimeError(
            "Falta defusedxml. Instala las dependencias con 'pip install -r metadatos/requirements.txt'."
        ) from exc
    namespace = "urn:schemas-microsoft-com:office:office"
    property_names = {
        "title": "Title",
        "subject": "Subject",
        "author": "Author",
        "keywords": "Keywords",
        "description": "Description",
        "last_modified_by": "LastAuthor",
        "created": "Created",
        "modified": "LastSaved",
        "revision": "Revision",
        "category": "Category",
        "company": "Company",
        "manager": "Manager",
    }
    properties: dict[str, Any] = {}
    sheets: list[dict[str, Any]] = []
    properties_tag = f"{{{namespace}}}DocumentProperties"
    spreadsheet_namespace = "urn:schemas-microsoft-com:office:spreadsheet"
    worksheet_tag = f"{{{spreadsheet_namespace}}}Worksheet"
    table_tag = f"{{{spreadsheet_namespace}}}Table"
    name_attribute = f"{{{spreadsheet_namespace}}}Name"
    rows_attribute = f"{{{spreadsheet_namespace}}}ExpandedRowCount"
    columns_attribute = f"{{{spreadsheet_namespace}}}ExpandedColumnCount"
    property_tags = {
        f"{{{namespace}}}{xml_name}": output_name
        for xml_name, output_name in property_names.items()
    }
    in_properties = False
    try:
        for event, element in ElementTree.iterparse(path, events=("start", "end")):
            if event == "start" and element.tag == properties_tag:
                in_properties = True
            elif event == "start" and element.tag == worksheet_tag:
                sheets.append(
                    {
                        "name": element.attrib.get(name_attribute, ""),
                        "visibility": "visible",
                        "rows": None,
                        "columns": None,
                    }
                )
            elif event == "start" and element.tag == table_tag and sheets:
                sheets[-1]["rows"] = element.attrib.get(rows_attribute)
                sheets[-1]["columns"] = element.attrib.get(columns_attribute)
            elif event == "end":
                if in_properties and element.tag in property_tags and element.text:
                    properties[property_tags[element.tag]] = element.text.strip()
                elif element.tag == properties_tag:
                    in_properties = False
                element.clear()
    except (OSError, ElementTree.ParseError) as exc:
        raise RuntimeError(f"No se pudo leer el XLS SpreadsheetML: {exc}") from exc
    properties["sheet_count"] = len(sheets)
    properties["hidden_sheet_count"] = 0
    properties["sheets"] = sheets
    return properties


def pdf_metadata(path: Path) -> dict[str, Any]:
    """Extrae diccionario /Info, tamaño de páginas y adjuntos de un PDF."""
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        raise RuntimeError(
            "Falta pypdf. Instala las dependencias con 'pip install -r metadatos/requirements.txt'."
        ) from exc
    try:
        reader = PdfReader(path)
        metadata = reader.metadata
        result: dict[str, Any] = {
            "pages": len(reader.pages),
            "encrypted": reader.is_encrypted,
            "pdf_version": reader.pdf_header,
        }
        if metadata is not None:
            fields = {
                "title": "/Title",
                "author": "/Author",
                "subject": "/Subject",
                "creator": "/Creator",
                "producer": "/Producer",
                "created": "/CreationDate",
                "modified": "/ModDate",
                "keywords": "/Keywords",
                "trapped": "/Trapped",
            }
            for output_name, pdf_name in fields.items():
                value = metadata.get(pdf_name)
                if value not in (None, ""):
                    result[output_name] = json_value(value)
        page_sizes: dict[str, int] = {}
        landscape_pages = 0
        rotated_pages = 0
        for page in reader.pages:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            size_key = f"{width:.1f} x {height:.1f} pt"
            page_sizes[size_key] = page_sizes.get(size_key, 0) + 1
            if width > height:
                landscape_pages += 1
            if page.get("/Rotate", 0) % 360:
                rotated_pages += 1
        result["page_sizes"] = page_sizes
        result["landscape_pages"] = landscape_pages
        result["rotated_pages"] = rotated_pages
        result["attachment_count"] = len(reader.attachments)
        return result
    except (OSError, ValueError, EOFError, PdfReadError) as exc:
        raise RuntimeError(f"No se pudo leer el archivo PDF: {exc}") from exc


def extract_file(path: Path) -> dict[str, Any]:
    """Devuelve el objeto canónico de metadatos para un archivo dado."""
    compound = ".nii" if path.name.lower().endswith(".nii.gz") else None
    result: dict[str, Any] = {
        "file": str(path.resolve()),
        "format": (compound or path.suffix.lower()).lstrip("."),
        "filesystem": {},
        "document": {},
        "error": None,
    }
    try:
        result["filesystem"] = file_metadata(path)
        extension = path.suffix.lower()
        if extension in OFFICE_EXTENSIONS:
            result["document"] = office_metadata(path)
        elif extension == ".pdf":
            result["document"] = pdf_metadata(path)
        elif extension == ".txt":
            result["document"] = text_metadata(path)
        elif is_image(path.name) or detect_image(path):
            document = analyze_image(path)
            result["document"] = document
            if document.get("mime_type"):
                result["filesystem"]["mime_type"] = document["mime_type"]
            if not result["format"]:
                result["format"] = document.get("format_detail") or "imagen"
        else:
            raise ValueError(f"Formato no compatible: {extension or '(sin extensión)'}")
    except (OSError, ValueError, RuntimeError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def text_metadata(path: Path) -> dict[str, Any]:
    """Detecta codificación y cuenta líneas, palabras y caracteres de un TXT."""
    try:
        from charset_normalizer import from_bytes
    except ImportError as exc:
        raise RuntimeError(
            "Falta charset-normalizer. Instala las dependencias con 'pip install -r metadatos/requirements.txt'."
        ) from exc
    data = path.read_bytes()
    if not data:
        return {
            "encoding": "utf-8",
            "characters": 0,
            "words": 0,
            "lines": 0,
            "nonempty_lines": 0,
            "has_bom": False,
        }
    detected = from_bytes(data).best()
    if detected is None:
        raise RuntimeError("No se pudo determinar la codificación del archivo TXT.")
    text = str(detected)
    return {
        "encoding": detected.encoding,
        "characters": len(text),
        "words": len(text.split()),
        "lines": len(text.splitlines()),
        "nonempty_lines": sum(bool(line.strip()) for line in text.splitlines()),
        "has_bom": data.startswith((b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")),
    }


def discover_files(inputs: list[Path], recursive: bool) -> tuple[list[Path], list[str]]:
    """Expande rutas de entrada en archivos válidos y errores legibles."""
    files: list[Path] = []
    errors: list[str] = []

    def on_walk_error(error: OSError) -> None:
        errors.append(f"{error.filename or 'directorio'}: {error}")

    for input_path in inputs:
        if not input_path.exists():
            errors.append(f"{input_path}: la ruta no existe.")
        elif input_path.is_file():
            if input_path.name.startswith("~$"):
                continue
            files.append(input_path)
        elif input_path.is_dir():
            if recursive:
                for root, _, names in os.walk(input_path, onerror=on_walk_error):
                    files.extend(
                        Path(root) / name
                        for name in names
                        if not name.startswith("~$")
                        and is_supported_name(name)
                    )
            else:
                try:
                    files.extend(
                        child
                        for child in input_path.iterdir()
                        if child.is_file()
                        and not child.name.startswith("~$")
                        and is_supported_name(child.name)
                    )
                except OSError as exc:
                    errors.append(f"{input_path}: {exc}")
        else:
            errors.append(f"{input_path}: no es un archivo ni un directorio.")
    return files, errors


def write_results(results: list[dict[str, Any]], output_format: str, output_path: Path | None) -> None:
    """Escribe los resultados en JSON o CSV, a consola o a archivo."""
    if output_format == "json":
        text = json.dumps(results, ensure_ascii=False, indent=2) + "\n"
        if output_path is None:
            sys.stdout.write(text)
        else:
            output_path.write_text(text, encoding="utf-8")
        return
    fieldnames = ["file", "format", "size_bytes", "sha256", "created", "modified", "document_metadata", "error"]
    if output_path is None:
        stream = sys.stdout
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(csv_row(result))
        return
    with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(csv_row(result))


def csv_row(result: dict[str, Any]) -> dict[str, Any]:
    """Aplana un resultado a una fila tabular de siete columnas."""
    filesystem = result["filesystem"]
    return {
        "file": result["file"],
        "format": result["format"],
        "size_bytes": filesystem.get("size_bytes", ""),
        "sha256": filesystem.get("sha256", ""),
        "created": filesystem.get("created", ""),
        "modified": filesystem.get("modified", ""),
        "document_metadata": json.dumps(result["document"], ensure_ascii=False),
        "error": result["error"] or "",
    }
