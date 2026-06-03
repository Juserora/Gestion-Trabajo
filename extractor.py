"""
extractor.py
============
Contiene la clase `DocumentExtractor`, responsable de:
  1. Construir el prompt multimodal (imagen + instrucciones + JSON Schema).
  2. Llamar al modelo de Anthropic (Claude) en modo multimodal.
  3. Parsear y validar la respuesta contra el esquema Pydantic.
  4. Ejecutar UN ÚNICO reintento de auto-corrección si la validación falla.
"""

from __future__ import annotations

import json
import re
from typing import Optional, Type

import anthropic
from pydantic import BaseModel, ValidationError

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 4096

# Marcador que el modelo debe devolver si el documento es ilegible.
ILLEGIBLE_SENTINEL = "_document_illegible"


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------
class JSONExtractionError(Exception):
    """No se encontró un objeto JSON válido en la respuesta del modelo."""


class IllegibleDocumentError(Exception):
    """El modelo indicó que el documento es ilegible o no corresponde al tipo."""


class ExtractionError(Exception):
    """La extracción falló de forma definitiva (incluso tras el reintento)."""


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------
class DocumentExtractor:
    """Orquesta la extracción estructurada de datos desde una imagen."""

    def __init__(
        self,
        client: Optional[anthropic.Anthropic] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        # Si no se inyecta cliente, se crea uno (lee ANTHROPIC_API_KEY del entorno).
        self.client = client or anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    # ---------------------------------------------------------------- público
    def extract(
        self,
        image_base64: str,
        media_type: str,
        schema: Type[BaseModel],
    ) -> BaseModel:
        """
        Extrae y valida los datos del documento.

        Flujo:
          - Primer intento de extracción.
          - Si falla la validación/parseo -> un único reintento con corrección.
          - Si el segundo intento también falla -> ExtractionError.

        Lanza:
          IllegibleDocumentError -> documento ilegible (sin reintento).
          ExtractionError        -> fallo definitivo de parseo/validación.
        """
        prompt = self._build_extraction_prompt(schema)
        raw_response = self._call_claude(image_base64, media_type, prompt)

        try:
            return self._parse_and_validate(raw_response, schema)
        except (ValidationError, json.JSONDecodeError, JSONExtractionError) as first_error:
            # --- Reintento único de auto-corrección ---
            correction_prompt = self._build_correction_prompt(
                schema, raw_response, first_error
            )
            retry_response = self._call_claude(
                image_base64, media_type, correction_prompt
            )
            try:
                return self._parse_and_validate(retry_response, schema)
            except (ValidationError, json.JSONDecodeError, JSONExtractionError) as second_error:
                raise ExtractionError(
                    "La extracción falló tras el reintento de auto-corrección. "
                    f"Error final: {second_error}"
                ) from second_error

    # ----------------------------------------------------------- llamada LLM
    def _call_claude(self, image_base64: str, media_type: str, prompt: str) -> str:
        """Realiza la llamada multimodal y devuelve el texto de la respuesta."""
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
            raise ExtractionError(
                f"Error al comunicarse con la API de Anthropic: {exc}"
            ) from exc

        return self._response_to_text(response)

    @staticmethod
    def _response_to_text(response) -> str:
        """Concatena todos los bloques de texto de la respuesta de Claude."""
        parts = []
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", ""))
        return "".join(parts).strip()

    # -------------------------------------------------------- parseo/validación
    def _parse_and_validate(self, raw_text: str, schema: Type[BaseModel]) -> BaseModel:
        """Extrae el JSON, detecta ilegibilidad y valida contra el esquema."""
        json_str = self._extract_json(raw_text)
        data = json.loads(json_str)

        if isinstance(data, dict) and data.get(ILLEGIBLE_SENTINEL) is True:
            # No tiene sentido reintentar: la ilegibilidad no se corrige sola.
            raise IllegibleDocumentError(
                "El documento es ilegible o no corresponde al tipo esperado."
            )

        return schema.model_validate(data)

    @staticmethod
    def _extract_json(text: str) -> str:
        """Aísla el primer objeto JSON presente en el texto de la respuesta."""
        if not text or not text.strip():
            raise JSONExtractionError("La respuesta del modelo está vacía.")

        cleaned = text.strip()
        # Elimina cercas de código Markdown (```json ... ```), si existen.
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise JSONExtractionError(
                "No se encontró un objeto JSON en la respuesta del modelo."
            )
        return cleaned[start : end + 1]

    # ------------------------------------------------------------- prompts
    @staticmethod
    def _build_extraction_prompt(schema: Type[BaseModel]) -> str:
        """Construye el prompt de extracción inicial a partir del JSON Schema."""
        schema_json = json.dumps(
            schema.model_json_schema(), ensure_ascii=False, indent=2
        )
        return (
            "Eres un sistema experto de extracción de datos de documentos.\n"
            "Analiza la imagen del documento adjunto y extrae la información "
            "solicitada.\n\n"
            "Devuelve ÚNICAMENTE un objeto JSON válido que cumpla EXACTAMENTE "
            "con el siguiente JSON Schema. No incluyas explicaciones, texto "
            "adicional ni marcadores de código Markdown.\n\n"
            f"JSON Schema:\n{schema_json}\n\n"
            "Reglas:\n"
            "- Si un campo no aparece en el documento y el esquema lo permite, "
            "usa null.\n"
            "- Respeta los tipos de datos (los números deben ser números, no "
            "cadenas de texto).\n"
            "- Usa el formato de fecha ISO 8601 (YYYY-MM-DD) siempre que sea "
            "posible.\n"
            "- Si el documento es completamente ilegible o no corresponde al "
            'tipo esperado, responde EXACTAMENTE con: {"'
            f"{ILLEGIBLE_SENTINEL}"
            '": true}\n'
        )

    @staticmethod
    def _build_correction_prompt(
        schema: Type[BaseModel],
        previous_output: str,
        error: Exception,
    ) -> str:
        """Construye el prompt de corrección inyectando el error de validación."""
        schema_json = json.dumps(
            schema.model_json_schema(), ensure_ascii=False, indent=2
        )
        return (
            "Tu respuesta anterior NO superó la validación del esquema.\n\n"
            "Respuesta anterior:\n"
            f"{previous_output}\n\n"
            "Error de validación detectado:\n"
            f"{error}\n\n"
            "Corrige el JSON para que cumpla EXACTAMENTE con el siguiente "
            "JSON Schema. Devuelve ÚNICAMENTE el JSON corregido, sin texto "
            "adicional ni marcadores de código Markdown.\n\n"
            f"JSON Schema:\n{schema_json}\n"
        )
