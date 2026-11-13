"""Pruebas de extracción XMP en imágenes y documentos PDF."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extractor.engine import extract_file

XMP = b"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description rdf:about=""
 xmlns:xmp="http://ns.adobe.com/xap/1.0/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmp:ModifyDate="2026-11-01T10:20:30Z"
 xmp:CreateDate="2026-10-31T08:00:00Z"
 xmp:CreatorTool="Extractor">
<dc:title><rdf:Alt><rdf:li xml:lang="x-default">Informe</rdf:li></rdf:Alt></dc:title>
</rdf:Description></rdf:RDF></x:xmpmeta>"""


class XmpTest(unittest.TestCase):
    """Comprueba que las fechas y el título XMP llegan al contrato."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="xmp_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_xmp_en_jpeg(self) -> None:
        from PIL import Image

        path = self.tmp / "foto.jpg"
        Image.new("RGB", (10, 10)).save(path, xmp=XMP)
        document = extract_file(path)["document"]
        self.assertEqual(document["xmp"]["modify_date"], "2026-11-01T10:20:30Z")
        self.assertEqual(document["xmp"]["title"], "Informe")

    def test_xmp_en_pdf(self) -> None:
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, NameObject

        path = self.tmp / "informe.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        stream = DecodedStreamObject()
        stream.set_data(XMP)
        stream[NameObject("/Type")] = NameObject("/Metadata")
        stream[NameObject("/Subtype")] = NameObject("/XML")
        writer._root_object[NameObject("/Metadata")] = writer._add_object(stream)
        with path.open("wb") as handle:
            writer.write(handle)
        document = extract_file(path)["document"]
        self.assertEqual(document["xmp"]["title"], "Informe")
        self.assertEqual(document["xmp"]["modified"], "2026-11-01T10:20:30")


if __name__ == "__main__":
    unittest.main()
