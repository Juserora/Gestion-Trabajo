from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Union

from convertidor import (
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
from esquemas import SCHEMA_MAP

FileInput = Union[str, bytes]


def extract_document(file: FileInput, document_type: str, client=None) -> dict:
    key = document_type.strip().lower()
    schema = SCHEMA_MAP.get(key)
    if schema is None:
        opciones = ", ".join(sorted(SCHEMA_MAP.keys()))
        raise ValueError(f"'{document_type}' no es un tipo válido. Opciones: {opciones}.")

    image_base64, media_type = file_to_base64(file)
    extractor = DocumentExtractor(client=client)
    result = extractor.extract(image_base64, media_type, schema)
    return result.model_dump()


def _build_error_response(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


def run_cli(argv: Optional["list[str]"] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extrae datos estructurados de facturas, contratos y documentos de identidad."
    )
    parser.add_argument("file", help="Ruta del archivo (PDF, PNG o JPEG).")
    parser.add_argument("document_type", choices=sorted(SCHEMA_MAP.keys()), help="Tipo de documento.")
    args = parser.parse_args(argv)

    try:
        data = extract_document(args.file, args.document_type)
        print(json.dumps({"success": True, "document_type": args.document_type, "data": data}, ensure_ascii=False, indent=2))
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
    except Exception as exc:
        error = _build_error_response("UNEXPECTED_ERROR", str(exc))

    print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
