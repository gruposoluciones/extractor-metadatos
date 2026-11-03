"""Pruebas del módulo de imágenes en sus tres niveles de extracción."""

from __future__ import annotations

import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

# Permite ejecutar las pruebas sin instalar el paquete.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extractor import imagenes
from extractor.engine import extract_file


def be32(value: int) -> bytes:
    """Empaqueta un entero de 32 bits en big-endian."""
    return struct.pack(">I", value)


def make_isobmff(path: Path, brand: bytes, width: int, height: int) -> None:
    """Fabrica un contenedor ISOBMFF mínimo con ftyp y una caja ispe."""
    ispe = be32(20) + b"ispe" + b"\x00" * 4 + be32(width) + be32(height)
    ipco = be32(8 + len(ispe)) + b"ipco" + ispe
    iprp = be32(8 + len(ipco)) + b"iprp" + ipco
    meta = be32(8 + 4 + len(iprp)) + b"meta" + b"\x00" * 4 + iprp
    ftyp = be32(8 + 8 + 8) + b"ftyp" + brand + be32(0) + b"mif1" + brand
    path.write_bytes(ftyp + meta)


class ImagesTest(unittest.TestCase):
    """Comprueba los niveles completa, parcial y solo_firma."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="img_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_nivel_completo_con_pillow(self) -> None:
        from PIL import Image

        path = self.tmp / "foto.png"
        Image.new("RGB", (32, 20), (1, 2, 3)).save(path)
        document = extract_file(path)["document"]
        self.assertEqual(document["format"], "PNG")
        self.assertEqual(document["extraction"], "completa")
        self.assertEqual((document["width"], document["height"]), (32, 20))
        self.assertFalse(document["animated"])

    def test_nivel_parcial_heic(self) -> None:
        path = self.tmp / "foto.heic"
        make_isobmff(path, b"heic", 100, 50)
        document = extract_file(path)["document"]
        self.assertEqual(document["format"], "HEIF")
        self.assertEqual(document["extraction"], "parcial")
        self.assertEqual((document["width"], document["height"]), (100, 50))

    def test_svg_con_script_y_dimensiones(self) -> None:
        path = self.tmp / "dibujo.svg"
        path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="20">'
            "<script>alert(1)</script></svg>",
            encoding="utf-8",
        )
        document = extract_file(path)["document"]
        self.assertEqual(document["format"], "SVG")
        self.assertTrue(document["has_script"])
        self.assertEqual(document["width"], 10)

    def test_la_firma_prevalece_sobre_la_extension(self) -> None:
        from PIL import Image

        path = self.tmp / "disfrazada.jpg"
        Image.new("RGB", (8, 8)).save(path, format="PNG")
        self.assertEqual(extract_file(path)["document"]["format"], "PNG")

    def test_nine_patch(self) -> None:
        from PIL import Image

        path = self.tmp / "icono.9.png"
        Image.new("RGBA", (9, 9)).save(path)
        self.assertTrue(extract_file(path)["document"]["nine_patch"])

    def test_nivel_solo_firma(self) -> None:
        path = self.tmp / "imagen.bpg"
        path.write_bytes(b"BPG\xfb" + b"\x00" * 16)
        document = extract_file(path)["document"]
        self.assertEqual(document["format"], "BPG")
        self.assertEqual(document["extraction"], "solo_firma")

    def test_registro_de_extensiones(self) -> None:
        self.assertGreaterEqual(len(imagenes.IMAGE_EXTENSIONS), 170)
        for extension in (".heic", ".cr2", ".svg", ".psd", ".dcm", ".ktx"):
            self.assertIn(extension, imagenes.IMAGE_EXTENSIONS)
        self.assertEqual(imagenes.group_of(".cr2"), "raw")
        self.assertEqual(imagenes.group_of(".svg"), "vectorial")
        self.assertEqual(imagenes.group_of(".kra"), "capas")


if __name__ == "__main__":
    unittest.main()
