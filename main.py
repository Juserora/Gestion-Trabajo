"""
main.py
=======
Punto de entrada del Document Extraction Pipeline.

Unifica los módulos `converter`, `schemas` y `extractor` en una sola función
(`extract_document`) y expone una interfaz de línea de comandos (CLI).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Union

from converter import (
    FileConversionError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    file_to_base64,
)
from extractor import (
    DocumentExtractor,
    ExtractionError,
    IllegibleDocumentError,
)
from schemas import SCHEMA_MAP

FileInput = Union[str, bytes]


def extract_document(
    file: FileInput,
    document_type: str,
    client=None,
) -> dict:
    """
    Ejecuta el pipeline completo de extracción.

    Args:
        file: Ruta del archivo o bytes (PDF, PNG o JPEG).
        document_type: Tipo de documento ('factura', 'contrato', 'identidad').
        client: (Opcional) cliente de Anthropic ya configurado. Útil para tests.

    Returns:
        dict con los campos extraídos y validados.

    Lanza:
        ValueError               -> tipo de documento no soportado.
        FileTooLargeError        -> archivo demasiado grande.
        UnsupportedFileTypeError -> formato de archivo no soportado.
        FileConversionError      -> fallo al convertir el archivo.
        IllegibleDocumentError   -> documento ilegible.
        ExtractionError          -> fallo de extracción tras el reintento.
    """
    key = document_type.strip().lower()
    schema = SCHEMA_MAP.get(key)
    if schema is None:
        soportados = ", ".join(sorted(SCHEMA_MAP.keys()))
        raise ValueError(
            f"Tipo de documento no soportado: '{document_type}'. "
            f"Tipos válidos: {soportados}."
        )

    # 1. Convertir el archivo a imagen Base64.
    image_base64, media_type = file_to_base64(file)

    # 2. Extraer y validar con el LLM.
    extractor = DocumentExtractor(client=client)
    result = extractor.extract(image_base64, media_type, schema)

    return result.model_dump()


def _build_error_response(code: str, message: str) -> dict:
    """Construye una respuesta de error estructurada para la CLI."""
    return {"success": False, "error": {"code": code, "message": message}}


def run_cli(argv: Optional["list[str]"] = None) -> int:
    """Interfaz de línea de comandos. Devuelve un código de salida (0 = éxito)."""
    parser = argparse.ArgumentParser(
        description="Document Extraction Pipeline: extrae datos estructurados "
        "de facturas, contratos y documentos de identidad usando Claude."
    )
    parser.add_argument("file", help="Ruta del archivo (PDF, PNG o JPEG).")
    parser.add_argument(
        "document_type",
        choices=sorted(SCHEMA_MAP.keys()),
        help="Tipo de documento a extraer.",
    )
    args = parser.parse_args(argv)

    try:
        data = extract_document(args.file, args.document_type)
        output = {"success": True, "document_type": args.document_type, "data": data}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    except ValueError as exc:
        error = _build_error_response("INVALID_DOCUMENT_TYPE", str(exc))
    except FileTooLargeError as exc:
        error = _build_error_response("FILE_TOO_LARGE", str(exc))
    except UnsupportedFileTypeError as exc:
        error = _build_error_response("UNSUPPORTED_FILE_TYPE", str(exc))
    except FileConversionError as exc:
        error = _build_error_response("FILE_CONVERSION_ERROR", str(exc))
    except IllegibleDocumentError as exc:
        error = _build_error_response("ILLEGIBLE_DOCUMENT", str(exc))
    except ExtractionError as exc:
        error = _build_error_response("EXTRACTION_FAILED", str(exc))
    except Exception as exc:  # Red de seguridad para errores inesperados.
        error = _build_error_response("UNEXPECTED_ERROR", str(exc))

    print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
