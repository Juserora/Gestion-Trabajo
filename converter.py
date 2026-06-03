from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Tuple, Union

from pdf2image import convert_from_bytes
from PIL import Image

MAX_FILE_SIZE_MB: int = 20
MAX_IMAGE_LONG_EDGE: int = 2048
PDF_RENDER_DPI: int = 150
MAX_BASE64_BYTES: int = 5 * 1024 * 1024

FileInput = Union[str, Path, bytes]


class FileTooLargeError(Exception):
    pass


class UnsupportedFileTypeError(Exception):
    pass


class FileConversionError(Exception):
    pass


def _read_bytes(file: FileInput) -> bytes:
    if isinstance(file, (bytes, bytearray)):
        return bytes(file)
    path = Path(file)
    if not path.exists():
        raise FileConversionError(f"El archivo no existe: {path}")
    if not path.is_file():
        raise FileConversionError(f"La ruta no es un archivo: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise FileConversionError(f"No se pudo leer el archivo: {exc}") from exc


def _check_size(data: bytes) -> None:
    size_mb = len(data) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise FileTooLargeError(
            f"El archivo pesa {size_mb:.2f} MB y supera el máximo de {MAX_FILE_SIZE_MB} MB."
        )


def _detect_format(data: bytes) -> str:
    if data[:4] == b"%PDF":
        return "pdf"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    raise UnsupportedFileTypeError("Formato no soportado. Solo se aceptan archivos PDF, PNG o JPEG.")


def _stack_images_vertically(images: "list[Image.Image]") -> Image.Image:
    width = max(img.width for img in images)
    height = sum(img.height for img in images)
    canvas = Image.new("RGB", (width, height), "white")
    offset_y = 0
    for img in images:
        canvas.paste(img, (0, offset_y))
        offset_y += img.height
    return canvas


def _pdf_to_image(data: bytes) -> Image.Image:
    try:
        pages = convert_from_bytes(data, dpi=PDF_RENDER_DPI)
    except Exception as exc:
        raise FileConversionError(
            f"No se pudo convertir el PDF. ¿Está poppler instalado? Detalle: {exc}"
        ) from exc

    if not pages:
        raise FileConversionError("El PDF no contiene páginas procesables.")

    if len(pages) == 1:
        return pages[0].convert("RGB")

    return _stack_images_vertically([p.convert("RGB") for p in pages])


def _bytes_to_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        return image.convert("RGB")
    except Exception as exc:
        raise FileConversionError(f"No se pudo abrir la imagen: {exc}") from exc


def _resize_if_needed(image: Image.Image) -> Image.Image:
    long_edge = max(image.width, image.height)
    if long_edge <= MAX_IMAGE_LONG_EDGE:
        return image
    scale = MAX_IMAGE_LONG_EDGE / long_edge
    new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _encode_image(image: Image.Image) -> Tuple[str, str]:
    # PNG primero (sin pérdida, mejor para texto); fallback a JPEG si es muy grande
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    raw = buffer.getvalue()
    if len(raw) <= MAX_BASE64_BYTES:
        return base64.b64encode(raw).decode("utf-8"), "image/png"

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85, optimize=True)
    raw = buffer.getvalue()
    if len(raw) > MAX_BASE64_BYTES:
        raise FileConversionError(
            "La imagen es demasiado grande incluso tras la compresión. Reduce la resolución."
        )
    return base64.b64encode(raw).decode("utf-8"), "image/jpeg"


def file_to_base64(file: FileInput) -> Tuple[str, str]:
    data = _read_bytes(file)
    _check_size(data)
    fmt = _detect_format(data)

    image = _pdf_to_image(data) if fmt == "pdf" else _bytes_to_image(data)
    image = _resize_if_needed(image)
    return _encode_image(image)
