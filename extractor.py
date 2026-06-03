from __future__ import annotations

import json
import re
from typing import Optional, Type

import anthropic
from pydantic import BaseModel, ValidationError

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 4096

ILLEGIBLE_SENTINEL = "_document_illegible"


class JSONExtractionError(Exception):
    pass


class IllegibleDocumentError(Exception):
    pass


class ExtractionError(Exception):
    pass


class DocumentExtractor:

    def __init__(
        self,
        client: Optional[anthropic.Anthropic] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.client = client or anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    def extract(self, image_base64: str, media_type: str, schema: Type[BaseModel]) -> BaseModel:
        prompt = self._build_extraction_prompt(schema)
        raw_response = self._call_claude(image_base64, media_type, prompt)

        try:
            return self._parse_and_validate(raw_response, schema)
        except (ValidationError, json.JSONDecodeError, JSONExtractionError) as first_error:
            correction_prompt = self._build_correction_prompt(schema, raw_response, first_error)
            retry_response = self._call_claude(image_base64, media_type, correction_prompt)
            try:
                return self._parse_and_validate(retry_response, schema)
            except (ValidationError, json.JSONDecodeError, JSONExtractionError) as second_error:
                raise ExtractionError(
                    f"La extracción falló tras el reintento. Error final: {second_error}"
                ) from second_error

    def _call_claude(self, image_base64: str, media_type: str, prompt: str) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
        except anthropic.APIError as exc:
            raise ExtractionError(f"Error al comunicarse con la API de Anthropic: {exc}") from exc

        return self._response_to_text(response)

    @staticmethod
    def _response_to_text(response) -> str:
        parts = []
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", ""))
        return "".join(parts).strip()

    def _parse_and_validate(self, raw_text: str, schema: Type[BaseModel]) -> BaseModel:
        json_str = self._extract_json(raw_text)
        data = json.loads(json_str)

        if isinstance(data, dict) and data.get(ILLEGIBLE_SENTINEL) is True:
            raise IllegibleDocumentError("El documento es ilegible o no corresponde al tipo esperado.")

        return schema.model_validate(data)

    @staticmethod
    def _extract_json(text: str) -> str:
        if not text or not text.strip():
            raise JSONExtractionError("La respuesta del modelo está vacía.")

        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise JSONExtractionError("No se encontró un objeto JSON en la respuesta del modelo.")
        return cleaned[start : end + 1]

    @staticmethod
    def _build_extraction_prompt(schema: Type[BaseModel]) -> str:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        return (
            "Eres un sistema experto de extracción de datos de documentos.\n"
            "Analiza la imagen del documento adjunto y extrae la información solicitada.\n\n"
            "Devuelve ÚNICAMENTE un objeto JSON válido que cumpla EXACTAMENTE con el siguiente "
            "JSON Schema. No incluyas explicaciones, texto adicional ni marcadores de código Markdown.\n\n"
            f"JSON Schema:\n{schema_json}\n\n"
            "Reglas:\n"
            "- Si un campo no aparece en el documento y el esquema lo permite, usa null.\n"
            "- Respeta los tipos de datos (los números deben ser números, no cadenas de texto).\n"
            "- Usa el formato de fecha ISO 8601 (YYYY-MM-DD) siempre que sea posible.\n"
            "- Si el documento es completamente ilegible o no corresponde al tipo esperado, "
            f'responde EXACTAMENTE con: {{"{ILLEGIBLE_SENTINEL}": true}}\n'
        )

    @staticmethod
    def _build_correction_prompt(schema: Type[BaseModel], previous_output: str, error: Exception) -> str:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        return (
            "Tu respuesta anterior NO superó la validación del esquema.\n\n"
            f"Respuesta anterior:\n{previous_output}\n\n"
            f"Error de validación detectado:\n{error}\n\n"
            "Corrige el JSON para que cumpla EXACTAMENTE con el siguiente JSON Schema. "
            "Devuelve ÚNICAMENTE el JSON corregido, sin texto adicional ni marcadores de código Markdown.\n\n"
            f"JSON Schema:\n{schema_json}\n"
        )
