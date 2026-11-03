#!/usr/bin/env python3
"""Módulo exclusivo de metadatos para archivos de imagen, en tres niveles de profundidad."""

from __future__ import annotations

import gzip
import io
import struct
import zipfile
from pathlib import Path
from typing import Any

# --- Taxonomía de extensiones: grupo -> {extensión: nombre de formato} ---

IMAGE_GROUPS: dict[str, dict[str, str]] = {
    "raster": {
        ".jpg": "JPEG", ".jpeg": "JPEG", ".jpe": "JPEG", ".jfif": "JPEG",
        ".jfi": "JPEG", ".jif": "JPEG", ".png": "PNG", ".gif": "GIF",
        ".bmp": "BMP", ".dib": "BMP", ".tif": "TIFF", ".tiff": "TIFF",
        ".webp": "WebP", ".ico": "ICO",
    },
    "moderno": {
        ".heic": "HEIF", ".heif": "HEIF", ".hif": "HEIF", ".heics": "HEIF",
        ".avci": "HEIF", ".avif": "AVIF", ".avifs": "AVIF", ".jxl": "JPEG XL",
        ".jp2": "JPEG 2000", ".j2k": "JPEG 2000", ".j2c": "JPEG 2000",
        ".jpf": "JPEG 2000", ".jpx": "JPEG 2000", ".jpm": "JPEG 2000",
        ".jxr": "JPEG XR", ".wdp": "JPEG XR", ".hdp": "JPEG XR",
        ".apng": "APNG", ".mng": "MNG", ".jng": "JNG", ".qoi": "QOI",
        ".bpg": "BPG", ".flif": "FLIF",
    },
    "vectorial": {
        ".svg": "SVG", ".svgz": "SVG", ".eps": "EPS", ".epsf": "EPS",
        ".epsi": "EPS", ".ps": "PostScript", ".ai": "Adobe Illustrator",
        ".cdr": "CorelDRAW", ".wmf": "WMF", ".wmz": "WMF", ".emf": "EMF",
        ".emz": "EMF", ".cgm": "CGM", ".odg": "OpenDocument Graphics",
        ".afdesign": "Affinity Designer", ".xar": "Xara", ".sketch": "Sketch",
        ".fig": "Figma", ".dxf": "DXF", ".dwg": "DWG",
    },
    "raw": {
        ".dng": "DNG", ".raw": "RAW", ".cr2": "Canon RAW 2", ".cr3": "Canon RAW 3",
        ".crw": "Canon RAW", ".nef": "Nikon NEF", ".nrw": "Nikon NRW",
        ".arw": "Sony ARW", ".srf": "Sony SRF", ".sr2": "Sony SR2",
        ".arq": "Sony ARQ", ".raf": "Fujifilm RAF", ".orf": "Olympus ORF",
        ".rw2": "Panasonic RW2", ".rwl": "Leica RWL", ".pef": "Pentax PEF",
        ".ptx": "Pentax PTX", ".srw": "Samsung SRW", ".x3f": "Sigma X3F",
        ".3fr": "Hasselblad 3FR", ".fff": "Hasselblad FFF", ".iiq": "Phase One IIQ",
        ".mos": "Leaf MOS", ".mrw": "Minolta MRW", ".dcr": "Kodak DCR",
        ".kdc": "Kodak KDC", ".k25": "Kodak K25", ".dcs": "Kodak DCS",
        ".erf": "Epson ERF", ".mef": "Mamiya MEF", ".bay": "Casio BAY",
        ".gpr": "GoPro GPR",
    },
    "capas": {
        ".psd": "Photoshop", ".psb": "Photoshop Large", ".xcf": "GIMP XCF",
        ".kra": "Krita", ".ora": "OpenRaster", ".afphoto": "Affinity Photo",
        ".pdn": "Paint.NET", ".clip": "Clip Studio Paint", ".procreate": "Procreate",
        ".pxm": "Pixelmator", ".pxd": "Pixelmator Pro", ".pspimage": "PaintShop Pro",
        ".cpt": "Corel Photo-Paint", ".sai": "PaintTool SAI", ".mdp": "MediBang Paint",
    },
    "escaneo": {
        ".djvu": "DjVu", ".djv": "DjVu", ".jb2": "JBIG2", ".jbig2": "JBIG2",
        ".pcx": "PCX", ".dcx": "PCX multipágina", ".mdi": "Microsoft Document Imaging",
        ".pcd": "Kodak Photo CD",
    },
    "cientifico": {
        ".exr": "OpenEXR", ".hdr": "Radiance HDR", ".pfm": "PFM", ".dpx": "DPX",
        ".cin": "Cineon", ".dcm": "DICOM", ".nii": "NIfTI", ".fits": "FITS",
        ".fit": "FITS", ".fts": "FITS", ".ecw": "ER Mapper ECW", ".sid": "MrSID",
        ".img": "ERDAS Imagine",
    },
    "textura": {
        ".dds": "DDS", ".tga": "TARGA", ".icb": "TARGA", ".vda": "TARGA",
        ".vst": "TARGA", ".ktx": "KTX", ".ktx2": "KTX2", ".pvr": "PowerVR",
        ".astc": "ASTC", ".basis": "Basis Universal", ".vtf": "Valve VTF",
    },
    "sistema": {
        ".rle": "BMP RLE", ".cur": "Cursor", ".ani": "Cursor animado",
        ".msp": "Microsoft Paint", ".icns": "Apple Icon", ".pict": "PICT",
        ".pct": "PICT", ".pic": "PICT", ".mac": "MacPaint", ".pntg": "MacPaint",
        ".xbm": "X BitMap", ".xpm": "X PixMap", ".xwd": "X Window Dump",
        ".pbm": "PBM", ".pgm": "PGM", ".ppm": "PPM", ".pnm": "PNM", ".pam": "PAM",
        ".ras": "Sun Raster", ".sun": "Sun Raster", ".sgi": "SGI RGB",
        ".rgb": "SGI RGB", ".rgba": "SGI RGBA", ".bw": "SGI BW",
        ".cut": "Dr. Halo", ".wpg": "WordPerfect Graphics", ".iff": "IFF/ILBM",
        ".ilbm": "IFF/ILBM", ".lbm": "IFF/ILBM", ".neo": "Atari NEOchrome",
        ".pi1": "Atari Degas", ".pi2": "Atari Degas", ".pi3": "Atari Degas",
        ".pc1": "Atari Degas", ".pc2": "Atari Degas", ".pc3": "Atari Degas",
        ".koa": "Koala Painter", ".fli": "Autodesk Animator", ".flc": "Autodesk Animator",
    },
}

IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    ext for group in IMAGE_GROUPS.values() for ext in group
)
COMPOUND_SUFFIXES = (".9.png", ".nii.gz")

_MIME = {
    "JPEG": "image/jpeg", "PNG": "image/png", "GIF": "image/gif", "BMP": "image/bmp",
    "TIFF": "image/tiff", "WebP": "image/webp", "ICO": "image/x-icon",
    "HEIF": "image/heif", "AVIF": "image/avif", "JPEG XL": "image/jxl",
    "JPEG 2000": "image/jp2", "JPEG XR": "image/vnd.ms-photo", "QOI": "image/qoi",
    "SVG": "image/svg+xml", "EPS": "application/postscript",
    "PostScript": "application/postscript", "Adobe Illustrator": "application/illustrator",
    "DWG": "image/vnd.dwg", "DXF": "image/vnd.dxf", "OpenDocument Graphics": "application/vnd.oasis.opendocument.graphics",
    "DICOM": "application/dicom", "OpenEXR": "image/x-exr", "Radiance HDR": "image/vnd.radiance",
    "FITS": "image/fits", "KTX": "image/ktx", "KTX2": "image/ktx2", "DDS": "image/vnd-ms.dds",
    "TARGA": "image/x-tga", "PCX": "image/x-pcx", "DjVu": "image/vnd.djvu",
    "Photoshop": "image/vnd.adobe.photoshop", "GIMP XCF": "image/x-xcf",
    "Krita": "application/x-krita", "OpenRaster": "image/openraster", "TGA": "image/x-tga",
    "NIfTI": "application/x-nifti", "JBIG2": "image/jbig2", "PFM": "image/x-pfm",
    "DPX": "image/x-dpx", "Cineon": "image/x-cineon", "APNG": "image/apng",
    "MNG": "image/x-mng", "JNG": "image/x-jng", "BPG": "image/bpg", "FLIF": "image/flif",
    "X PixMap": "image/x-xpixmap", "X BitMap": "image/x-xbitmap",
    "Sun Raster": "image/x-sun-raster", "SGI RGB": "image/x-sgi", "Apple Icon": "image/icns",
    "IFF/ILBM": "image/x-ilbm", "Koala Painter": "image/x-koala",
    "Atari Degas": "image/x-degas", "PowerVR": "image/x-pvr", "Valve VTF": "image/x-vtf",
    "DNG": "image/x-adobe-dng", "Cursor": "image/x-icon", "Cursor animado": "image/x-icon",
}
_RAW_MIME = "image/x-raw"

# --- Firmas: identificación real del contenido, no solo de la extensión ---

_SIGNATURES: tuple[tuple[int, bytes, str], ...] = (
    (0, b"\xff\xd8\xff", "JPEG"),
    (0, b"\x89PNG\r\n\x1a\n", "PNG"),
    (0, b"GIF87a", "GIF"),
    (0, b"GIF89a", "GIF"),
    (0, b"BM", "BMP"),
    (0, b"II*\x00", "TIFF"),
    (0, b"MM\x00*", "TIFF"),
    (0, b"\x00\x00\x01\x00", "ICO"),
    (0, b"\x00\x00\x02\x00", "Cursor"),
    (0, b"qoif", "QOI"),
    (0, b"BPG\xfb", "BPG"),
    (0, b"FLIF", "FLIF"),
    (0, b"\xff\x0a", "JPEG XL"),
    (0, b"\x00\x00\x00\x0cjP  \r\n\x87\n", "JPEG 2000"),
    (0, b"II\xbc\x01", "JPEG XR"),
    (0, b"8BPS", "Photoshop"),
    (0, b"gimp xcf ", "GIMP XCF"),
    (0, b"PDN3", "Paint.NET"),
    (0, b"CSFCHUNK", "Clip Studio Paint"),
    (0, b"AT&TFORM", "DjVu"),
    (0, b"\x97JB2\r\n\x1a\n", "JBIG2"),
    (0, b"\x0a\x05\x01\x08", "PCX"),
    (0, b"\x3a\xde\x68\xb1", "PCX multipágina"),
    (0, b"v/1\x01", "OpenEXR"),
    (0, b"#?RADIANCE", "Radiance HDR"),
    (0, b"SDPX", "DPX"),
    (0, b"XPDS", "DPX"),
    (0, b"\x80\x2a\x5f\xd7", "Cineon"),
    (0, b"DDS ", "DDS"),
    (0, b"\xabKTX 11\xbb\r\n\x1a\n", "KTX"),
    (0, b"\xabKTX 20\xbb\r\n\x1a\n", "KTX2"),
    (0, b"PVR\x03", "PowerVR"),
    (0, b"\x13\xab\xa1\\", "ASTC"),
    (0, b"VTF\x00", "Valve VTF"),
    (0, b"\xffWPC", "WordPerfect Graphics"),
    (0, b"Y\xa6j\x95", "Sun Raster"),
    (0, b"\x01\xda", "SGI RGB"),
    (0, b"\x00\x11\xaf", "Autodesk Animator"),
    (0, b"icns", "Apple Icon"),
    (0, b"/* XPM */", "X PixMap"),
    (0, b"#define ", "X BitMap"),
    (0, b"\xd7\xcd\xc6\x9a", "WMF"),
    (0, b"\x01\x00\x09\x00", "WMF"),
    (0, b"SIMPLE  =", "FITS"),
    (0, b"xar!", "Xara"),
)

_TGA_EXT = {".tga", ".icb", ".vda", ".vst"}

_ISOBMFF_BRANDS = {
    b"heic": "HEIF", b"heix": "HEIF", b"hevc": "HEIF", b"hevx": "HEIF",
    b"mif1": "HEIF", b"msf1": "HEIF", b"heim": "HEIF", b"heis": "HEIF",
    b"avif": "AVIF", b"avis": "AVIF", b"jxl ": "JPEG XL", b"crx ": "Canon RAW 3",
}

_RAW_TIFF = {
    ".dng": "DNG", ".cr2": "Canon RAW 2", ".nef": "Nikon NEF", ".nrw": "Nikon NRW",
    ".arw": "Sony ARW", ".srf": "Sony SRF", ".sr2": "Sony SR2", ".orf": "Olympus ORF",
    ".rw2": "Panasonic RW2", ".rwl": "Leica RWL", ".pef": "Pentax PEF",
    ".ptx": "Pentax PTX", ".srw": "Samsung SRW", ".3fr": "Hasselblad 3FR",
    ".fff": "Hasselblad FFF", ".iiq": "Phase One IIQ", ".mos": "Leaf MOS",
    ".mrw": "Minolta MRW", ".dcr": "Kodak DCR", ".kdc": "Kodak KDC",
    ".k25": "Kodak K25", ".dcs": "Kodak DCS", ".erf": "Epson ERF",
    ".mef": "Mamiya MEF", ".bay": "Casio BAY", ".gpr": "GoPro GPR",
}

_ZIP_BASED = {
    "OpenDocument Graphics": "application/vnd.oasis.opendocument.graphics",
    "Krita": "application/x-krita",
    "OpenRaster": "image/openraster",
}


def _looks_like_tga(head: bytes) -> bool:
    """Valida la cabecera de 18 bytes de un TGA, que no tiene firma propia."""
    if len(head) < 18 or head[1] not in (0, 1) or head[2] not in (1, 2, 3, 9, 10, 11):
        return False
    width = head[12] | head[13] << 8
    height = head[14] | head[15] << 8
    return 0 < width <= 65535 and 0 < height <= 65535 and head[16] in (8, 15, 16, 24, 32)


def _effective_suffix(name: str) -> str:
    """Resuelve el sufijo real, incluidos los compuestos (.nii.gz, .9.png)."""
    lower = name.lower()
    if lower.endswith(".nii.gz"):
        return ".nii"
    if lower.endswith(".9.png"):
        return ".png"
    return Path(lower).suffix


def group_of(extension: str) -> str:
    """Devuelve el grupo taxonómico de una extensión."""
    for group, entries in IMAGE_GROUPS.items():
        if extension in entries:
            return group
    return "desconocido"


def is_image(name: str) -> bool:
    """Indica si el nombre corresponde a una imagen admitida, incluidos sufijos compuestos."""
    lower = name.lower()
    if lower.endswith(COMPOUND_SUFFIXES):
        return True
    return Path(lower).suffix in IMAGE_EXTENSIONS


def detect_image(path: Path) -> str | None:
    """Devuelve el formato si la firma del contenido corresponde a una imagen conocida."""
    fmt, source = _sniff(path)
    return fmt if source.startswith("firma") and fmt != "Desconocido" else None


def _head(path: Path, size: int, offset: int = 0) -> bytes:
    with path.open("rb") as stream:
        stream.seek(offset)
        return stream.read(size)


def _sniff_bytes(head: bytes) -> str | None:
    """Identifica un formato a partir de sus primeros bytes."""
    for offset, magic, fmt in _SIGNATURES:
        if head[offset:offset + len(magic)] == magic:
            return fmt
    return None


def _sniff(path: Path) -> tuple[str, str]:
    """Identifica el formato por firma; devuelve (formato, origen de la detección)."""
    head = _head(path, 512)
    name = path.name.lower()
    suffix = Path(name).suffix
    if suffix in _TGA_EXT and _looks_like_tga(head):
        return "TARGA", "extensión+estructura"
    if name.endswith(".9.png") and head.startswith(b"\x89PNG"):
        return "PNG", "firma (nine-patch)"
    if len(head) >= 12 and head[:4] == b"RIFF":
        kind = head[8:12]
        if kind == b"WEBP":
            return "WebP", "firma"
        if kind == b"ACON":
            return "Cursor animado", "firma"
        if kind == b"CDR":
            return "CorelDRAW", "firma"
    if len(head) >= 12 and head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in _ISOBMFF_BRANDS:
            return _ISOBMFF_BRANDS[brand], "firma"
    if head[:4] == b"FORM":
        subtype = head[8:12]
        if subtype in (b"ILBM", b"PBM "):
            return "IFF/ILBM", "firma"
    if head[:3] == b"\x00\x00\x00" and b"EHFA_HEADER_TAG" in head:
        return "ERDAS Imagine", "firma"
    for offset, magic, fmt in _SIGNATURES:
        if head[offset:offset + len(magic)] == magic:
            return fmt, "firma"
    if b"%!PS-Adobe" in head[:64] or b"%PDF" in head[:16]:
        if suffix == ".ai":
            return "Adobe Illustrator", "firma"
        if suffix in (".eps", ".epsf", ".epsi"):
            return "EPS", "firma"
        return "PostScript", "firma"
    stripped = head.lstrip()
    if stripped.startswith(b"<") and (b"<svg" in head.lower() or b"<!doctype svg" in head.lower()):
        return "SVG", "firma"
    if path.suffix.lower() == ".svgz" and head[:2] == b"\x1f\x8b":
        return "SVG", "firma (gzip)"
    if len(head) > 132 and head[128:132] == b"DICM":
        return "DICOM", "firma"
    if len(head) > 348 and head[344:348] in (b"n+1\x00", b"ni1\x00"):
        return "NIfTI", "firma"
    if path.suffix.lower() == ".gz" and name.endswith(".nii.gz"):
        with gzip.open(path, "rb") as stream:
            if stream.read(348)[344:348] in (b"n+1\x00", b"ni1\x00"):
                return "NIfTI", "firma (gzip)"
    extension_fmt = next(
        (fmt for entries in IMAGE_GROUPS.values() for ext, fmt in entries.items() if ext == Path(name).suffix),
        None,
    )
    return extension_fmt or "Desconocido", "extensión"


def _ratio(value: Any) -> float | None:
    try:
        return round(float(value), 6)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _exif_map(exif: Any) -> dict[str, Any]:
    """Extrae los campos EXIF de interés y normaliza valores."""
    if not exif:
        return {}
    tags = {
        271: "make", 272: "model", 274: "orientation", 305: "software",
        306: "datetime", 315: "artist", 33432: "copyright",
    }
    exif_ifd_tags = {
        33434: "exposure_time", 33437: "f_number", 34855: "iso",
        36867: "datetime_original", 36868: "datetime_digitized",
        37386: "focal_length", 42036: "lens_model",
    }
    result: dict[str, Any] = {}
    for tag, name in tags.items():
        value = exif.get(tag)
        if value not in (None, ""):
            result[name] = _clean(value)
    try:
        sub = exif.get_ifd(0x8769)
    except (KeyError, AttributeError):
        sub = {}
    for tag, name in exif_ifd_tags.items():
        value = sub.get(tag)
        if value not in (None, ""):
            result[name] = _clean(value)
    gps = _gps(exif)
    if gps:
        result["gps"] = gps
    return result


def _gps(exif: Any) -> dict[str, Any]:
    """Convierte las coordenadas EXIF GPS a grados decimales."""
    try:
        ifd = exif.get_ifd(0x8825)
    except (KeyError, AttributeError):
        return {}
    if not ifd:
        return {}

    def degrees(values: Any, ref: str) -> float | None:
        try:
            d, m, s = (float(v) for v in values)
            value = d + m / 60 + s / 3600
            return round(-value if ref in ("S", "W") else value, 6)
        except (TypeError, ValueError):
            return None

    lat = degrees(ifd.get(2), str(ifd.get(1, "N")))
    lon = degrees(ifd.get(4), str(ifd.get(3, "E")))
    result: dict[str, Any] = {}
    if lat is not None:
        result["latitude"] = lat
    if lon is not None:
        result["longitude"] = lon
    altitude = ifd.get(6)
    if altitude is not None:
        height = _ratio(altitude)
        if height is not None:
            result["altitude"] = height
    return result


def _clean(value: Any) -> Any:
    """Normaliza tipos de Pillow (racionales, tuplas de bytes) a JSON."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace").strip("\x00").strip()
    if isinstance(value, (tuple, list)):
        return [_clean(item) for item in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    converted = _ratio(value)
    return converted if converted is not None else str(value)


def _icc(profile: bytes | None) -> dict[str, Any]:
    """Resume el perfil ICC incrustado y obtiene su descripción legible."""
    if not profile:
        return {"present": False}
    info: dict[str, Any] = {"present": True, "bytes": len(profile)}
    try:
        from PIL import ImageCms

        info["description"] = ImageCms.getProfileDescription(
            ImageCms.ImageCmsProfile(io.BytesIO(profile))
        ).strip()
    except Exception:
        info["description"] = None
    return info


def _pillow(path: Path) -> dict[str, Any]:
    """Nivel 1: lectura completa mediante Pillow."""
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = 250_000_000
    with Image.open(path) as image:
        info = image.info or {}
        frames = int(getattr(image, "n_frames", 1) or 1)
        width, height = image.size
        document: dict[str, Any] = {
            "width": width,
            "height": height,
            "megapixels": round(width * height / 1_000_000, 3),
            "mode": image.mode,
            "bit_depth": int(getattr(image, "bits", 0) or _depth(image.mode)),
            "has_alpha": "A" in image.mode or "transparency" in info,
            "animated": frames > 1,
            "frames": frames,
            "compression": info.get("compression"),
            "icc_profile": _icc(info.get("icc_profile")),
        }
        if "dpi" in info:
            document["dpi"] = [round(float(v), 2) for v in info["dpi"]]
        if "progressive" in info:
            document["progressive"] = bool(info["progressive"])
        if "interlace" in info:
            document["interlaced"] = bool(info["interlace"]) or info["interlace"] in (1, 2)
        if frames > 1 and "duration" in info:
            document["frame_duration_ms"] = info["duration"]
        if "loop" in info:
            document["loop"] = info["loop"]
        if "sizes" in info:
            document["icon_sizes"] = [list(size) for size in info["sizes"]]
        if path.name.lower().endswith(".9.png"):
            document["nine_patch"] = True
        exif = _exif_map(image.getexif())
        if exif:
            document["exif"] = exif
        if image.format:
            document.setdefault("container_format", image.format)
        return document


def _depth(mode: str) -> int:
    """Estima la profundidad de bits a partir del modo de color."""
    table = {"1": 1, "L": 8, "LA": 8, "P": 8, "RGB": 8, "RGBA": 8,
             "CMYK": 8, "YCbCr": 8, "HSV": 8, "LAB": 8, "I": 32, "F": 32}
    return table.get(mode, 8)


def _svg(path: Path) -> dict[str, Any]:
    """Nivel 2: estructura de SVG/SVGZ sin renderizar."""
    from defusedxml import ElementTree

    raw = gzip.decompress(path.read_bytes()) if path.suffix.lower() == ".svgz" else path.read_bytes()
    root = ElementTree.fromstring(raw)
    tags = [element.tag.split("}")[-1] for element in root.iter()]
    document: dict[str, Any] = {
        "vector": True,
        "svg_version": root.get("version"),
        "declared_width": root.get("width"),
        "declared_height": root.get("height"),
        "view_box": root.get("viewBox"),
        "element_count": len(tags),
        "element_types": sorted(set(tags))[:25],
        "text_elements": tags.count("text"),
        "path_elements": tags.count("path"),
        "image_elements": tags.count("image"),
        "gradients": tags.count("linearGradient") + tags.count("radialGradient"),
        "has_script": "script" in tags,
        "external_references": sum(
            1 for element in root.iter()
            if any(str(v).startswith(("http://", "https://")) for v in element.attrib.values())
        ),
    }
    title = root.find("{http://www.w3.org/2000/svg}title")
    if title is not None and title.text:
        document["title"] = title.text.strip()
    width, height = root.get("width"), root.get("height")
    try:
        if width and width.replace(".", "").isdigit() and height and height.replace(".", "").isdigit():
            document["width"] = int(float(width))
            document["height"] = int(float(height))
        elif document["view_box"]:
            parts = [float(value) for value in document["view_box"].replace(",", " ").split()]
            if len(parts) == 4:
                document["width"] = int(parts[2])
                document["height"] = int(parts[3])
    except (TypeError, ValueError):
        pass
    return document


def _boxes(data: bytes, start: int, end: int, depth: int = 0) -> dict[str, Any]:
    """Recorre cajas ISOBMFF y devuelve brand, dimensiones y códecs."""
    found: dict[str, Any] = {}
    offset = start
    while offset + 8 <= end and depth < 6:
        size = int.from_bytes(data[offset:offset + 4], "big")
        kind = data[offset + 4:offset + 8]
        header = 8
        if size == 1 and offset + 16 <= end:
            size = int.from_bytes(data[offset + 8:offset + 16], "big")
            header = 16
        elif size == 0:
            size = end - offset
        if size < header or offset + size > end:
            break
        body = offset + header
        if kind == b"ftyp":
            found["brand"] = data[body:body + 4].decode("latin-1", "replace")
            found["compatible_brands"] = [
                data[body + i:body + i + 4].decode("latin-1", "replace")
                for i in range(8, size - header, 4)
            ][:8]
        elif kind == b"ispe" and "width" not in found and body + 12 <= end:
            found["width"] = int.from_bytes(data[body + 4:body + 8], "big")
            found["height"] = int.from_bytes(data[body + 8:body + 12], "big")
        elif kind in (b"meta", b"iprp", b"ipco", b"moov", b"trak", b"mdia"):
            inner = _boxes(data, body + 4 if kind == b"meta" else body, offset + size, depth + 1)
            for key, value in inner.items():
                found.setdefault(key, value)
        elif kind in (b"av01", b"hvc1", b"hev1", b"jxlp", b"jxlc"):
            found.setdefault("codec", kind.decode("latin-1"))
        offset += size
    return found


def _isobmff(path: Path) -> dict[str, Any]:
    """Nivel 2: HEIF/AVIF/JPEG XL/CR3 leídos como contenedor de cajas."""
    size = min(path.stat().st_size, 4 * 1024 * 1024)
    data = _head(path, size)
    found = _boxes(data, 0, len(data))
    document: dict[str, Any] = {"container": "ISOBMFF"}
    if found.get("brand"):
        document["brand"] = found["brand"]
    if found.get("compatible_brands"):
        document["compatible_brands"] = found["compatible_brands"]
    if found.get("codec"):
        document["codec"] = found["codec"]
    if found.get("width"):
        document["width"] = found["width"]
        document["height"] = found["height"]
        document["megapixels"] = round(found["width"] * found["height"] / 1_000_000, 3)
    return document


def _tiff_ifd(path: Path) -> dict[str, Any]:
    """Nivel 2: IFD TIFF, que también cubre la mayoría de RAW de cámara."""
    data = _head(path, 512 * 1024)
    if len(data) < 8:
        return {}
    endian = "little" if data[:2] == b"II" else "big"
    prefix = "<" if endian == "little" else ">"
    offset = struct.unpack(prefix + "I", data[4:8])[0]
    types = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}
    wanted = {
        256: "width", 257: "height", 258: "bit_depth", 259: "compression",
        262: "photometric", 271: "make", 272: "model", 274: "orientation",
        277: "samples_per_pixel", 282: "x_resolution", 283: "y_resolution",
        296: "resolution_unit", 305: "software", 306: "datetime",
        34665: "exif_ifd",
    }
    values: dict[str, Any] = {}
    seen = 0
    while offset and offset + 2 <= len(data) and seen < 3:
        count = struct.unpack(prefix + "H", data[offset:offset + 2])[0]
        entries = offset + 2
        for index in range(min(count, 128)):
            position = entries + index * 12
            if position + 12 > len(data):
                break
            tag, kind, amount = struct.unpack(prefix + "HHI", data[position:position + 8])
            if tag not in wanted:
                continue
            size = types.get(kind, 1) * amount
            if size <= 4:
                payload = data[position + 8:position + 8 + size]
            else:
                pointer = struct.unpack(prefix + "I", data[position + 8:position + 12])[0]
                payload = data[pointer:pointer + size]
            if not payload:
                continue
            if kind == 2:
                text = payload.decode("latin-1", "replace").strip("\x00").strip()
                if text:
                    values[wanted[tag]] = text
            elif kind in (3, 4) and amount == 1:
                values[wanted[tag]] = struct.unpack(prefix + ("H" if kind == 3 else "I"), payload)[0]
            elif kind == 5 and amount == 1:
                numerator, denominator = struct.unpack(prefix + "II", payload[:8])
                values[wanted[tag]] = round(numerator / denominator, 4) if denominator else None
        seen += 1
        pointer = offset + 2 + count * 12
        if pointer + 4 > len(data):
            break
        offset = struct.unpack(prefix + "I", data[pointer:pointer + 4])[0]
    exif_pointer = values.pop("exif_ifd", None)
    if exif_pointer and exif_pointer + 2 <= len(data):
        count = struct.unpack(prefix + "H", data[exif_pointer:exif_pointer + 2])[0]
        for index in range(min(count, 128)):
            position = exif_pointer + 2 + index * 12
            if position + 12 > len(data):
                break
            tag, kind, amount = struct.unpack(prefix + "HHI", data[position:position + 8])
            if tag not in (36867, 36868, 42036):
                continue
            size = types.get(kind, 1) * amount
            if size <= 4:
                payload = data[position + 8:position + 8 + size]
            else:
                pointer = struct.unpack(prefix + "I", data[position + 8:position + 12])[0]
                payload = data[pointer:pointer + size]
            text = payload.decode("latin-1", "replace").strip("\x00").strip()
            if text:
                values[{36867: "datetime_original", 36868: "datetime_digitized",
                        42036: "lens_model"}[tag]] = text
    if "width" in values and "height" in values:
        values["megapixels"] = round(values["width"] * values["height"] / 1_000_000, 3)
    values["byte_order"] = "little" if endian == "little" else "big"
    return values


def _dicom(path: Path) -> dict[str, Any]:
    """Nivel 2: cabecera DICOM elemental, sin exponer identificadores de paciente."""
    data = _head(path, 2 * 1024 * 1024)
    if data[128:132] != b"DICM":
        return {}
    tags = {
        (0x0008, 0x0060): "modality", (0x0008, 0x0020): "study_date",
        (0x0008, 0x1030): "study_description", (0x0008, 0x103E): "series_description",
        (0x0028, 0x0010): "rows", (0x0028, 0x0011): "columns",
        (0x0028, 0x0100): "bits_allocated", (0x0028, 0x0002): "samples_per_pixel",
    }
    text_tags = {1: 2, 4: 4}
    found: dict[str, Any] = {}
    offset = 132
    long_vr = {b"OB", b"OD", b"OF", b"OL", b"OV", b"OW", b"SQ", b"UC", b"UR", b"UT", b"UN"}
    while offset + 8 <= len(data) and len(found) < len(tags) + 2:
        group, element = struct.unpack("<HH", data[offset:offset + 4])
        vr = data[offset + 4:offset + 6]
        if vr in long_vr:
            if offset + 12 > len(data):
                break
            length = struct.unpack("<I", data[offset + 8:offset + 12])[0]
            body = offset + 12
        else:
            length = struct.unpack("<H", data[offset + 6:offset + 8])[0]
            body = offset + 8
        if (group, element) == (0x0010, 0x0010):
            found["patient_identity_present"] = length > 0
        elif (group, element) in tags:
            name = tags[(group, element)]
            raw = data[body:body + length]
            if name in ("rows", "columns", "bits_allocated", "samples_per_pixel"):
                if length == 2:
                    found[name] = struct.unpack("<H", raw)[0]
            else:
                found[name] = raw.decode("latin-1", "replace").strip("\x00 ").strip()
        if length == 0xFFFFFFFF or length > len(data):
            break
        offset = body + length
    if found.get("rows") and found.get("columns"):
        found["width"] = found["columns"]
        found["height"] = found["rows"]
        found["megapixels"] = round(found["rows"] * found["columns"] / 1_000_000, 3)
    found["transfer_syntax"] = "explícito VR little-endian"
    return found


def _nifti(path: Path) -> dict[str, Any]:
    """Nivel 2: cabecera NIfTI de 348 bytes."""
    data = gzip.decompress(path.read_bytes()[:4096]) if path.name.lower().endswith(".gz") else _head(path, 352)
    if len(data) < 348 or data[344:348] not in (b"n+1\x00", b"ni1\x00"):
        return {}
    dims = struct.unpack("<8h", data[40:56])
    datatype, bitpix = struct.unpack("<hh", data[70:74])
    pixdim = struct.unpack("<8f", data[76:108])
    names = {2: "uint8", 4: "int16", 8: "int32", 16: "float32", 64: "float64",
             256: "int8", 512: "uint16", 768: "uint32"}
    result: dict[str, Any] = {
        "dimensions": dims[0],
        "datatype": names.get(datatype, f"código {datatype}"),
        "bit_depth": bitpix,
        "voxel_size": [round(value, 4) for value in pixdim[1:dims[0] + 1]],
    }
    if dims[0] >= 2:
        result["width"] = dims[1]
        result["height"] = dims[2]
    if dims[0] >= 3:
        result["slices"] = dims[3]
    return result


def _fits(path: Path) -> dict[str, Any]:
    """Nivel 2: tarjetas de cabecera FITS."""
    block = _head(path, 2880 * 4)
    cards: dict[str, str] = {}
    for start in range(0, len(block) - 80, 80):
        card = block[start:start + 80].decode("latin-1", "replace")
        key = card[:8].strip()
        if key == "END":
            break
        if "=" in card[8:10]:
            cards.setdefault(key, card[10:].split("/")[0].strip().strip("'").strip())
    result: dict[str, Any] = {}
    for key, name in (("NAXIS", "dimensions"), ("NAXIS1", "width"), ("NAXIS2", "height"),
                      ("BITPIX", "bit_depth"), ("BSCALE", "bscale"), ("TELESCOP", "telescope"),
                      ("INSTRUME", "instrument"), ("DATE-OBS", "observation_date")):
        if key in cards:
            value = cards[key]
            result[name] = int(value) if value.lstrip("-").isdigit() else value
    return result


def _ktx(path: Path) -> dict[str, Any]:
    """Nivel 2: cabecera KTX/KTX2."""
    data = _head(path, 128)
    if data[:12] == b"\xabKTX 20\xbb\r\n\x1a\n" and len(data) >= 48:
        width, height = struct.unpack("<II", data[20:28])
        levels = struct.unpack("<I", data[40:44])[0]
        return {"width": width, "height": height, "mip_levels": levels, "version": 2}
    if len(data) >= 64:
        little = struct.unpack("<I", data[12:16])[0] == 0x04030201
        order = "<" if little else ">"
        width, height, depth = struct.unpack(order + "III", data[36:48])
        levels = struct.unpack(order + "I", data[56:60])[0]
        return {"width": width, "height": height or None, "depth": depth or None,
                "mip_levels": levels, "version": 1}
    return {}


def _dds(path: Path) -> dict[str, Any]:
    """Nivel 2: cabecera DDS."""
    data = _head(path, 128)
    if len(data) < 128:
        return {}
    height, width = struct.unpack("<II", data[12:20])
    mips, depth = struct.unpack("<II", data[28:36])
    fourcc = data[84:88]
    return {"width": width, "height": height, "depth": depth or None,
            "mip_levels": mips, "format_fourcc": fourcc.decode("latin-1", "replace").strip("\x00")}


def _pvr(path: Path) -> dict[str, Any]:
    """Nivel 2: cabecera PowerVR v3."""
    data = _head(path, 64)
    if len(data) < 48:
        return {}
    height, width, depth = struct.unpack("<III", data[20:32])
    surfaces, faces, mips = struct.unpack("<III", data[32:44])
    return {"width": width, "height": height, "depth": depth or None,
            "surfaces": surfaces, "faces": faces, "mip_levels": mips}


def _iff(path: Path) -> dict[str, Any]:
    """Nivel 2: cabecera IFF/ILBM de Amiga."""
    data = _head(path, 128)
    if data[:4] != b"FORM":
        return {}
    offset = 12
    while offset + 8 <= len(data):
        kind = data[offset:offset + 4]
        size = struct.unpack(">I", data[offset + 4:offset + 8])[0]
        if kind == b"BMHD" and offset + 20 <= len(data):
            width, height = struct.unpack(">HH", data[offset + 8:offset + 12])
            planes = data[offset + 16]
            mask = data[offset + 17]
            return {"width": width, "height": height, "bitplanes": planes,
                    "has_mask": mask == 1, "compression": data[offset + 18]}
        offset += 8 + size + (size % 2)
    return {}


def _retro(path: Path) -> dict[str, Any]:
    """Nivel 2: formatos retro de tamaño fijo (Koala, Degas, NEOchrome)."""
    size = path.stat().st_size
    suffix = path.suffix.lower()
    if suffix == ".koa" and size in (9002, 10003):
        return {"width": 160, "height": 200, "bit_depth": 8, "fixed_size_bytes": size}
    if suffix in (".pi1", ".pi2", ".pi3", ".pc1", ".pc2", ".pc3") and size == 32034:
        return {"width": 320, "height": 200, "bit_depth": 4, "fixed_size_bytes": size}
    if suffix == ".neo" and size == 32128:
        return {"width": 320, "height": 200, "bit_depth": 4, "fixed_size_bytes": size}
    return {}


def _postscript(path: Path) -> dict[str, Any]:
    """Nivel 2: cabecera DSC de EPS/PS/AI sin renderizar."""
    head = _head(path, 256 * 1024).decode("latin-1", "replace")
    result: dict[str, Any] = {}
    for key, name in (("%%Creator:", "creator"), ("%%Title:", "title"),
                      ("%%CreationDate:", "created"), ("%%Pages:", "pages"),
                      ("%%LanguageLevel:", "language_level")):
        for line in head.splitlines()[:200]:
            if line.startswith(key):
                result[name] = line[len(key):].strip()
                break
    bounding = next((line for line in head.splitlines()[:200] if "BoundingBox:" in line), "")
    if bounding:
        numbers = [part for part in bounding.split("BoundingBox:")[-1].split() if part.lstrip("-").isdigit()]
        if len(numbers) == 4:
            left, bottom, right, top = (int(value) for value in numbers)
            result["bounding_box"] = [left, bottom, right, top]
            result["width_pt"] = right - left
            result["height_pt"] = top - bottom
    result["postscript"] = True
    return result


def _cad(path: Path) -> dict[str, Any]:
    """Nivel 2: versión y extensión de dibujos DXF/DWG."""
    head = _head(path, 4096).decode("latin-1", "replace")
    result: dict[str, Any] = {}
    if head.startswith("AC"):
        result["version"] = head[:6].strip()
    for key in ("$ACADVER", "$INSUNITS", "$EXTMIN", "$EXTMAX"):
        if key in head:
            result.setdefault("header_vars", []).append(key)
    return result


def _xcf(path: Path) -> dict[str, Any]:
    """Nivel 2: cabecera XCF de GIMP."""
    data = _head(path, 32)
    if not data.startswith(b"gimp xcf "):
        return {}
    version = data[9:13].decode("latin-1", "replace").strip()
    candidates = (struct.unpack("<II", data[13:21]), struct.unpack(">II", data[13:21]))
    width, height = next(
        ((w, h) for w, h in candidates if 0 < w < 500_000 and 0 < h < 500_000), (0, 0)
    )
    return {"width": width, "height": height, "xcf_version": version or None}


def _zip_container(path: Path) -> dict[str, Any]:
    """Nivel 2: contenedores ZIP (ODG, KRA, ORA, Sketch, Figma, Pixelmator)."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        result: dict[str, Any] = {"zip_entries": len(names)}
        try:
            result["declared_mime"] = archive.read("mimetype").decode("latin-1").strip()
        except KeyError:
            pass
        preview = next(
            (name for name in ("mergedimage.png", "preview.png", "Thumbnails/thumbnail.png",
                               "previews/preview.png") if name in names),
            None,
        )
        result["has_preview"] = preview is not None
        layers = [name for name in names if name.startswith("layers/")]
        if layers:
            result["layer_files"] = len(layers)
        result["first_entries"] = names[:8]
        return result


def _guess(path: Path) -> dict[str, Any]:
    """Nivel 2 genérico: elige el lector adecuado al formato identificado."""
    name = path.name.lower()
    if name.endswith(COMPOUND_SUFFIXES) and name.endswith(".9.png"):
        return {}
    if path.suffix.lower() in (".svg", ".svgz"):
        return _svg(path)
    if name.endswith(".nii.gz") or path.suffix.lower() == ".nii":
        return _nifti(path)
    if path.suffix.lower() in (".dcm",):
        return _dicom(path)
    if path.suffix.lower() in (".fits", ".fit", ".fts"):
        return _fits(path)
    if path.suffix.lower() in (".ktx", ".ktx2"):
        return _ktx(path)
    if path.suffix.lower() == ".dds":
        return _dds(path)
    if path.suffix.lower() == ".pvr":
        return _pvr(path)
    if path.suffix.lower() in (".iff", ".ilbm", ".lbm"):
        return _iff(path)
    if path.suffix.lower() in (".eps", ".epsf", ".epsi", ".ps", ".ai"):
        return _postscript(path)
    if path.suffix.lower() in (".dxf", ".dwg"):
        return _cad(path)
    if path.suffix.lower() == ".xcf":
        return _xcf(path)
    if path.suffix.lower() in (".odg", ".kra", ".ora", ".sketch", ".fig", ".pxd",
                               ".afdesign", ".afphoto", ".procreate"):
        return _zip_container(path)
    if path.suffix.lower() in (".koa", ".pi1", ".pi2", ".pi3", ".pc1", ".pc2", ".pc3", ".neo"):
        return _retro(path)
    if path.suffix.lower() in (".wmz", ".emz"):
        try:
            inner = gzip.decompress(path.read_bytes()[:65536])[:64]
            return {"container": "gzip", "embedded_format": _sniff_bytes(inner)}
        except OSError:
            return {"container": "gzip", "embedded_format": None}
    head = _head(path, 12)
    if len(head) >= 8 and head[4:8] == b"ftyp":
        return _isobmff(path)
    if head[:2] in (b"II", b"MM"):
        return _tiff_ifd(path)
    return {}


def analyze_image(path: Path) -> dict[str, Any]:
    """Extrae metadatos de una imagen en el mayor nivel de detalle disponible."""
    fmt, source = _sniff(path)
    suffix = _effective_suffix(path.name)
    if fmt == "TIFF" and suffix in _RAW_TIFF:
        fmt = _RAW_TIFF[suffix]
    group = group_of(suffix)
    document: dict[str, Any] = {
        "format": fmt,
        "format_detail": suffix.lstrip(".") or fmt.lower(),
        "category": group,
        "mime_type": _MIME.get(fmt) or (_RAW_MIME if group == "raw" else None) or "application/octet-stream",
        "detected_by": source,
        "extraction": "solo_firma",
    }
    warnings: list[str] = []
    try:
        detail = _pillow(path)
        document.update({key: value for key, value in detail.items() if value is not None})
        document["extraction"] = "completa"
    except Exception as exc:
        warnings.append(f"lector completo no disponible: {type(exc).__name__}")
    try:
        extra = _guess(path) or {}
        if extra and document["extraction"] == "solo_firma":
            document["extraction"] = "parcial"
        for key, value in extra.items():
            if value is not None:
                document.setdefault(key, value)
    except Exception as inner:
        warnings.append(f"lector estructural falló: {type(inner).__name__}: {inner}")
    if warnings:
        document["warnings"] = warnings
    width, height = document.get("width"), document.get("height")
    if isinstance(width, int) and isinstance(height, int) and "megapixels" not in document:
        document["megapixels"] = round(width * height / 1_000_000, 3)
    return document
