import json
from unittest.mock import MagicMock

import pytest

from extractor import DocumentExtractor, ExtractionError, IllegibleDocumentError
from schemas import IdentidadSchema


def make_response(text: str) -> MagicMock:
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

INVALID_PAYLOAD = {"tipo_documento": "Cédula de ciudadanía"}

FAKE_IMAGE_B64 = "ZmFrZS1pbWFnZQ=="
FAKE_MEDIA_TYPE = "image/png"


def test_extraction_success_first_attempt():
    client = MagicMock()
    client.messages.create.return_value = make_response(json.dumps(VALID_PAYLOAD))

    result = DocumentExtractor(client=client).extract(FAKE_IMAGE_B64, FAKE_MEDIA_TYPE, IdentidadSchema)

    assert isinstance(result, IdentidadSchema)
    assert result.numero_documento == "1020304050"
    assert result.nombres == "Juan Sebastián"
    assert client.messages.create.call_count == 1


def test_extraction_retry_then_success():
    client = MagicMock()
    client.messages.create.side_effect = [
        make_response(json.dumps(INVALID_PAYLOAD)),
        make_response(json.dumps(VALID_PAYLOAD)),
    ]

    result = DocumentExtractor(client=client).extract(FAKE_IMAGE_B64, FAKE_MEDIA_TYPE, IdentidadSchema)

    assert isinstance(result, IdentidadSchema)
    assert result.apellidos == "Rodríguez Ramírez"
    assert client.messages.create.call_count == 2


def test_extraction_fails_after_retry():
    client = MagicMock()
    client.messages.create.side_effect = [
        make_response(json.dumps(INVALID_PAYLOAD)),
        make_response(json.dumps(INVALID_PAYLOAD)),
    ]

    with pytest.raises(ExtractionError):
        DocumentExtractor(client=client).extract(FAKE_IMAGE_B64, FAKE_MEDIA_TYPE, IdentidadSchema)

    assert client.messages.create.call_count == 2


def test_extraction_strips_markdown_fences():
    fenced = "```json\n" + json.dumps(VALID_PAYLOAD) + "\n```"
    client = MagicMock()
    client.messages.create.return_value = make_response(fenced)

    result = DocumentExtractor(client=client).extract(FAKE_IMAGE_B64, FAKE_MEDIA_TYPE, IdentidadSchema)

    assert result.numero_documento == "1020304050"
    assert client.messages.create.call_count == 1


def test_extraction_illegible_document():
    client = MagicMock()
    client.messages.create.return_value = make_response('{"_document_illegible": true}')

    with pytest.raises(IllegibleDocumentError):
        DocumentExtractor(client=client).extract(FAKE_IMAGE_B64, FAKE_MEDIA_TYPE, IdentidadSchema)

    assert client.messages.create.call_count == 1
