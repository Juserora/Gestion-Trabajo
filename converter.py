"""
converter.py
============
Convierte el archivo de entrada (PDF nativo, PDF escaneado o imagen) en una
representación Base64 lista para enviarse a Claude en un bloque multimodal
`type: "image"`.

Tanto el PDF nativo como el escaneado se tratan igual: se renderizan a imagen,
de modo que Claude actúa como OCR multimodal en ambos casos.

Dependencia de sistema: pdf2image requiere que 'poppler' esté instalado
(ver README.md).
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Tuple, Union

from pdf2image import convert_from_bytes
from PIL import Image

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
MAX_FILE_SIZE_MB: int = 20                 # Tamaño máximo del archivo de entrada.
MAX_IMAGE_LONG_EDGE: int = 2048            # Lado más largo (px) de la imagen final.
PDF_RENDER_DPI: int = 150                  # Resolución de renderizado de páginas PDF.
MAX_BASE64_BYTES: int = 5 * 1024 * 1024    # Límite práctico por imagen (~5 MB).

FileInput = Union[str, Path, bytes]


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------
class FileTooLargeError(Exception):
    """El archivo de entrada supera el tamaño máximo permitido."""


class UnsupportedFileTypeError(Exception):
    """El formato del archivo no está soportado (solo PDF, PNG, JPEG)."""


class FileConversionError(Exception):
    """Error genérico durante la conversión del archivo a imagen/Base64."""


# ---------------------------------------------------------------------------
# Lectura y detección
# ---------------------------------------------------------------------------
def _read_bytes(file: FileInput) -> bytes:
    """Lee el archivo de entrada y devuelve sus bytes crudos."""
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
    """Valida que los bytes no superen el tamaño máximo permitido."""
    size_mb = len(data) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise FileTooLargeError(
            f"El archivo pesa {size_mb:.2f} MB y supera el máximo de "
            f"{MAX_FILE_SIZE_MB} MB permitido."
        )


def _detect_format(data: bytes) -> str:
    """
    Detecta el formato del archivo a partir de sus 'magic bytes'.
    Devuelve 'pdf', 'png' o 'jpeg'.
    """
    if data[:4] == b"%PDF":
        return "pdf"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    raise UnsupportedFileTypeError(
        "Formato no soportado. Solo se aceptan archivos PDF, PNG o JPEG."
    )


# ---------------------------------------------------------------------------
# Conversión de PDF
# ---------------------------------------------------------------------------
def _stack_images_vertically(images: "list[Image.Image]") -> Image.Image:
    """Apila una lista de imágenes verticalmente sobre fondo blanco."""
    width = max(img.width for img in images)
    height = sum(img.height for img in images)
    canvas = Image.new("RGB", (width, height), "white")
    offset_y = 0
    for img in images:
        canvas.paste(img, (0, offset_y))
        offset_y += img.height
    return canvas


def _pdf_to_image(data: bytes) -> Image.Image:
    """
    Renderiza todas las páginas del PDF y las combina verticalmente en una
    única imagen. Funciona tanto para PDF nativo como escaneado.
    """
    try:
        pages = convert_from_bytes(data, dpi=PDF_RENDER_DPI)
    except Exception as exc:  # pdf2image lanza errores genéricos / de poppler.
        raise FileConversionError(
            "No se pudo convertir el PDF a imagen. "
            f"¿Está 'poppler' instalado? Detalle: {exc}"
        ) from exc

    if not pages:
        raise FileConversionError("El PDF no contiene páginas procesables.")

    if len(pages) == 1:
        return pages[0].convert("RGB")

    return _stack_images_vertically([p.convert("RGB") for p in pages])


# ---------------------------------------------------------------------------
# Conversión de imagen
# ---------------------------------------------------------------------------
def _bytes_to_image(data: bytes) -> Image.Image:
    """Carga bytes de imagen (PNG/JPEG) en un objeto PIL.Image."""
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        return image.convert("RGB")
    except Exception as exc:
        raise FileConversionError(
            f"No se pudo abrir la imagen proporcionada: {exc}"
        ) from exc


def _resize_if_needed(image: Image.Image) -> Image.Image:
    """Reduce la imagen si su lado más largo supera MAX_IMAGE_LONG_EDGE."""
    long_edge = max(image.width, image.height)
    if long_edge <= MAX_IMAGE_LONG_EDGE:
        return image
    scale = MAX_IMAGE_LONG_EDGE / long_edge
    new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _encode_image(image: Image.Image) -> Tuple[str, str]:
    """
    Codifica la imagen en Base64. Intenta PNG (sin pérdida); si el resultado
    supera MAX_BASE64_BYTES, recurre a JPEG con compresión.
    Devuelve (base64_str, media_type).
    """
    # Intento 1: PNG (sin pérdida, ideal para texto).
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    raw = buffer.getvalue()
    if len(raw) <= MAX_BASE64_BYTES:
        return base64.b64encode(raw).decode("utf-8"), "image/png"

    # Intento 2: JPEG comprimido (para imágenes muy grandes).
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85, optimize=True)
    raw = buffer.getvalue()
    if len(raw) > MAX_BASE64_BYTES:
        raise FileConversionError(
            "La imagen resultante es demasiado grande incluso tras la "
            "compresión. Reduce la resolución o el número de páginas."
        )
    return base64.b64encode(raw).decode("utf-8"), "image/jpeg"


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def file_to_base64(file: FileInput) -> Tuple[str, str]:
    """
    Punto de entrada del módulo.

    Recibe una ruta (str/Path) o bytes de un PDF/PNG/JPEG y devuelve una tupla
    (base64_str, media_type) lista para el bloque multimodal de Claude.

    Lanza:
        FileTooLargeError        -> archivo demasiado grande.
        UnsupportedFileTypeError -> formato no soportado.
        FileConversionError      -> cualquier otro fallo de conversión.
    """
    data = _read_bytes(file)
    _check_size(data)
    fmt = _detect_format(data)

    if fmt == "pdf":
        image = _pdf_to_image(data)
    else:
        image = _bytes_to_image(data)

    image = _resize_if_needed(image)
    return _encode_image(image)
