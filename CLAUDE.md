# Document Extraction Pipeline

## Qué hace este proyecto
Recibe un archivo (PDF nativo, PDF escaneado o imagen PNG/JPEG), lo convierte a
imagen Base64 y usa la API multimodal de Anthropic (Claude) para extraer campos
clave y devolverlos como JSON validado con Pydantic v2.

## Stack
- **anthropic** — llamadas multimodales a `claude-sonnet-4-6`
- **pydantic v2** — validación y definición de esquemas
- **pdf2image + Pillow** — conversión de PDF/imagen a Base64
- **pytest + unittest.mock** — tests sin consumir API real

## Arquitectura de archivos
```
esquemas.py     → Esquemas Pydantic (FacturaSchema, ContratoSchema, IdentidadSchema)
                  + dict SCHEMA_MAP {"factura": ..., "contrato": ..., "identidad": ...}
convertidor.py  → file_to_base64(file) → (base64_str, media_type)
                  Detecta formato por magic bytes. PDF → combina páginas verticalmente.
extractor.py    → class DocumentExtractor
                  .extract(image_b64, media_type, schema) → BaseModel
                  Reintento único de auto-corrección si falla validación Pydantic.
main.py         → extract_document(file, document_type) → dict   ← API pública
                  run_cli() → CLI con argparse
tests/
  test_extractor.py → 5 tests (mock del cliente Anthropic, no usa API real)
```

## Flujo de extracción
1. `file_to_base64` convierte el archivo.
2. `DocumentExtractor._call_claude` hace la llamada multimodal.
3. `_parse_and_validate` extrae el JSON y valida con Pydantic.
4. Si falla → `_build_correction_prompt` inyecta el error y reintenta UNA vez.
5. Si falla de nuevo → lanza `ExtractionError`.
6. Si el doc es ilegible → Claude devuelve `{"_document_illegible": true}` →
   lanza `IllegibleDocumentError` (sin reintento).

## Convenciones importantes
- El cliente de Anthropic siempre se inyecta como parámetro (`client=`) para
  facilitar el mocking en tests.
- Todas las excepciones propias están definidas en su módulo correspondiente
  (`converter.py` y `extractor.py`).
- El prompt se genera dinámicamente desde `schema.model_json_schema()` —
  nunca hay prompts hardcodeados por tipo de documento.
- Para agregar un nuevo tipo: definir schema en `esquemas.py` + registrar en
  `SCHEMA_MAP`. Nada más.

## Comandos clave
```bash
python -m pytest                         # correr tests (no necesita API key)
python main.py factura.pdf factura       # CLI
export ANTHROPIC_API_KEY="sk-ant-..."    # requerido para llamadas reales
sudo apt-get install poppler-utils       # dependencia de sistema para pdf2image
```

## Estado actual
Completo y funcional. Los 5 tests pasan. Listo para extender con nuevos tipos
de documento o nuevas funcionalidades.
