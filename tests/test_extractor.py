"""
tests/test_extractor.py
========================
Pruebas unitarias para la lógica de extracción y auto-corrección.

Se simula (mock) el cliente de Anthropic para no realizar llamadas reales a la
API. Se cubren los tres escenarios principales exigidos:
  1. Éxito en el primer intento.
  2. Reintento exitoso (primer JSON inválido, segundo válido).
  3. Fallo definitivo (ambos intentos inválidos).
Más dos pruebas extra para los casos de error especificados.

Ejecutar desde la raíz del proyecto con:  python -m pytest
"""

import json
from unittest.mock import MagicMock

import pytest

from extractor import DocumentExtractor, ExtractionError, IllegibleDocumentError
from schemas import IdentidadSchema


# ---------------------------------------------------------------------------
# Utilidades de apoyo
# ---------------------------------------------------------------------------
def make_response(text: str) -> MagicMock:
    """Crea un objeto de respuesta simulado con un único bloque de texto."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


VALID_PAYLOAD = {
    "tipo_documento": "Cédula de ciudadanía",
    "numero_documento": "1020304050",
    "nombres": "Juan Sebastián",
    "apellidos": "Rodríguez Ramírez",
    "fecha_nacimiento": "2005-01-01",
    "sexo": "M",
    "nacionalidad": "Colombiana",
    "fecha_expedicion": "2023-01-15",
    "fecha_vencimiento": "2033-01-15",
}

# JSON inválido: faltan campos obligatorios (numero_documento, nombres, apellidos).
INVALID_PAYLOAD = {"tipo_documento": "Cédula de ciudadanía"}

# Imagen ficticia (no se procesa porque el cliente está simulado).
FAKE_IMAGE_B64 = "ZmFrZS1pbWFnZQ=="
FAKE_MEDIA_TYPE = "image/png"


# ---------------------------------------------------------------------------
# 1. Éxito en el primer intento
# ---------------------------------------------------------------------------
def test_extraction_success_first_attempt():
    client = MagicMock()
    client.messages.create.return_value = make_response(json.dumps(VALID_PAYLOAD))

    extractor = DocumentExtractor(client=client)
    result = extractor.extract(FAKE_IMAGE_B64, FAKE_MEDIA_TYPE, IdentidadSchema)

    assert isinstance(result, IdentidadSchema)
    assert result.numero_documento == "1020304050"
    assert result.nombres == "Juan Sebastián"
    # La API debe haberse llamado UNA sola vez (sin reintento).
    assert client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# 2. Reintento exitoso (1er JSON inválido, 2do válido)
# ---------------------------------------------------------------------------
def test_extraction_retry_then_success():
    client = MagicMock()
    client.messages.create.side_effect = [
        make_response(json.dumps(INVALID_PAYLOAD)),  # 1er intento: inválido
        make_response(json.dumps(VALID_PAYLOAD)),     # 2do intento: válido
    ]

    extractor = DocumentExtractor(client=client)
    result = extractor.extract(FAKE_IMAGE_B64, FAKE_MEDIA_TYPE, IdentidadSchema)

    assert isinstance(result, IdentidadSchema)
    assert result.apellidos == "Rodríguez Ramírez"
    # La API debe haberse llamado DOS veces (intento + reintento).
    assert client.messages.create.call_count == 2


# ---------------------------------------------------------------------------
# 3. Fallo definitivo tras el reintento
# ---------------------------------------------------------------------------
def test_extraction_fails_after_retry():
    client = MagicMock()
    client.messages.create.side_effect = [
        make_response(json.dumps(INVALID_PAYLOAD)),  # 1er intento: inválido
        make_response(json.dumps(INVALID_PAYLOAD)),  # 2do intento: inválido
    ]

    extractor = DocumentExtractor(client=client)
    with pytest.raises(ExtractionError):
        extractor.extract(FAKE_IMAGE_B64, FAKE_MEDIA_TYPE, IdentidadSchema)

    # Confirma que se intentó exactamente dos veces (un único reintento).
    assert client.messages.create.call_count == 2


# ---------------------------------------------------------------------------
# 4. (Extra) JSON envuelto en cercas Markdown se parsea correctamente
# ---------------------------------------------------------------------------
def test_extraction_strips_markdown_fences():
    fenced = "```json\n" + json.dumps(VALID_PAYLOAD) + "\n```"
    client = MagicMock()
    client.messages.create.return_value = make_response(fenced)

    extractor = DocumentExtractor(client=client)
    result = extractor.extract(FAKE_IMAGE_B64, FAKE_MEDIA_TYPE, IdentidadSchema)

    assert result.numero_documento == "1020304050"
    assert client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# 5. (Extra) Documento ilegible -> IllegibleDocumentError sin reintento
# ---------------------------------------------------------------------------
def test_extraction_illegible_document():
    client = MagicMock()
    client.messages.create.return_value = make_response('{"_document_illegible": true}')

    extractor = DocumentExtractor(client=client)
    with pytest.raises(IllegibleDocumentError):
        extractor.extract(FAKE_IMAGE_B64, FAKE_MEDIA_TYPE, IdentidadSchema)

    # No debe reintentar ante un documento ilegible.
    assert client.messages.create.call_count == 1
