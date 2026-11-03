"""Pruebas del contrato de datos, el hash y el descubrimiento de archivos."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Permite ejecutar las pruebas sin instalar el paquete.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extractor.engine import csv_row, discover_files, extract_file


def make_docx(path: Path) -> None:
    """Genera un DOCX de prueba con título, encabezado y párrafo."""
    from docx import Document

    document = Document()
    document.core_properties.title = "Prueba"
    document.core_properties.author = "Autora"
    document.add_heading("Titulo", level=1)
    document.add_paragraph("Texto de prueba")
    document.save(path)


def make_xlsx(path: Path) -> None:
    """Genera un XLSX de prueba con una hoja oculta."""
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.active["A1"] = 1
    workbook.create_sheet("Oculta").sheet_state = "hidden"
    workbook.save(path)


def make_pdf(path: Path) -> None:
    """Genera un PDF de prueba de una página."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with path.open("wb") as stream:
        writer.write(stream)


class ContractTest(unittest.TestCase):
    """Verifica la forma del objeto de salida y las reglas de RF-01 y RF-07."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="meta_"))
        self.text = self.tmp / "nota.txt"
        self.text.write_text("Linea uno\nLinea dos\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_claves_del_contrato(self) -> None:
        record = extract_file(self.text)
        self.assertEqual(set(record), {"file", "format", "filesystem", "document", "error"})
        self.assertEqual(
            set(record["filesystem"]),
            {"name", "extension", "mime_type", "size_bytes", "sha256", "created", "modified"},
        )
        self.assertIsNone(record["error"])

    def test_sha256_coincide_con_hashlib(self) -> None:
        record = extract_file(self.text)
        self.assertEqual(
            record["filesystem"]["sha256"],
            hashlib.sha256(self.text.read_bytes()).hexdigest(),
        )

    def test_inspeccion_no_destructiva(self) -> None:
        antes = (self.text.stat().st_mtime_ns, hashlib.sha256(self.text.read_bytes()).hexdigest())
        extract_file(self.text)
        despues = (self.text.stat().st_mtime_ns, hashlib.sha256(self.text.read_bytes()).hexdigest())
        self.assertEqual(antes, despues)

    def test_documentos_soportados(self) -> None:
        docx = self.tmp / "informe.docx"
        xlsx = self.tmp / "libro.xlsx"
        pdf = self.tmp / "documento.pdf"
        make_docx(docx)
        make_xlsx(xlsx)
        make_pdf(pdf)

        record = extract_file(docx)
        self.assertEqual(record["format"], "docx")
        self.assertEqual(record["document"]["author"], "Autora")
        self.assertGreaterEqual(record["document"]["heading_count"], 1)

        record = extract_file(xlsx)
        self.assertEqual(record["document"]["sheet_count"], 2)
        self.assertEqual(record["document"]["hidden_sheet_count"], 1)

        record = extract_file(pdf)
        self.assertEqual(record["document"]["pages"], 1)
        self.assertFalse(record["document"]["encrypted"])

    def test_extension_no_admitida_aisla_el_error(self) -> None:
        raro = self.tmp / "dato.bin"
        raro.write_bytes(b"\x00\x01")
        record = extract_file(raro)
        self.assertEqual(record["document"], {})
        self.assertIn("Formato no compatible", record["error"])

    def test_descubrimiento_filtra_extensiones_y_temporales(self) -> None:
        (self.tmp / "~$bloqueado.docx").write_bytes(b"x")
        (self.tmp / "otro.bin").write_bytes(b"x")
        files, errors = discover_files([self.tmp], recursive=True)
        nombres = {path.name for path in files}
        self.assertIn("nota.txt", nombres)
        self.assertNotIn("otro.bin", nombres)
        self.assertNotIn("~$bloqueado.docx", nombres)
        self.assertEqual(errors, [])

    def test_descubrimiento_reporta_ruta_inexistente(self) -> None:
        _, errors = discover_files([self.tmp / "no_existe"], recursive=False)
        self.assertEqual(len(errors), 1)
        self.assertIn("no existe", errors[0])

    def test_csv_respeta_las_columnas_del_contrato(self) -> None:
        record = extract_file(self.text)
        fila = csv_row(record)
        self.assertEqual(
            list(fila),
            ["file", "format", "size_bytes", "sha256", "created", "modified",
             "document_metadata", "error"],
        )
        self.assertEqual(json.loads(fila["document_metadata"]), record["document"])


if __name__ == "__main__":
    unittest.main()
