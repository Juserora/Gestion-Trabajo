# Document Extraction Pipeline

Módulo en Python que recibe un documento (PDF nativo, PDF escaneado o imagen),
lo procesa como imagen y devuelve un JSON estructurado y validado con los campos
clave del documento, usando el SDK oficial de Anthropic (Claude) en modo
multimodal.

## Características

- Soporta PDF (nativo o escaneado), PNG y JPEG.
- 3 tipos de documento listos para usar: `factura`, `contrato`, `identidad`.
- Esquema fijo en Pydantic v2 por cada tipo de documento.
- **Auto-corrección:** si el JSON devuelto por Claude no pasa la validación, el
  error se inyecta en un nuevo prompt y se reintenta **una única vez**.
- Manejo explícito de errores: archivo muy grande, formato no soportado,
  documento ilegible y fallo de parseo tras el reintento.

## Requisitos previos

- Python 3.10 o superior.
- **poppler** instalado en el sistema (lo necesita `pdf2image`):
  - Ubuntu / WSL: `sudo apt-get install poppler-utils`
  - macOS (Homebrew): `brew install poppler`
  - Windows: descarga los binarios de poppler y agrega su carpeta `bin` al PATH.

## Instalación

```bash
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

El SDK lee la clave de API desde la variable de entorno `ANTHROPIC_API_KEY`:

```bash
export ANTHROPIC_API_KEY="tu_api_key"
# En Windows (PowerShell): $env:ANTHROPIC_API_KEY="tu_api_key"
```

## Uso

### Línea de comandos (CLI)

```bash
python main.py ruta/al/documento.pdf factura
python main.py ruta/al/cedula.jpg identidad
```

La salida es un JSON con la forma
`{"success": true, "document_type": ..., "data": {...}}`.

### Uso programático

```python
from main import extract_document

datos = extract_document("ruta/al/documento.pdf", "factura")
print(datos)   # dict con los campos extraídos y validados
```

## Ejecución de pruebas

### Pruebas unitarias (sin API key)

Las pruebas simulan (mock) la API de Anthropic, por lo que **no consumen
créditos ni requieren clave de API**. Ejecútalas desde la raíz del proyecto:

```bash
python -m pytest
```

> **Importante:** usa `python -m pytest` (no solo `pytest`) para que la raíz del
> proyecto quede en el `PYTHONPATH` y los imports de los módulos funcionen.

### Prueba end-to-end con documentos de muestra

La carpeta `samples/` incluye tres documentos sintéticos listos para probar la
extracción real contra la API de Claude. Primero configura tu API key y luego
ejecuta:

```bash
# Genera (o regenera) los archivos de muestra:
python samples/create_samples.py

# Extrae datos de cada tipo de documento:
python main.py samples/factura_muestra.png   factura
python main.py samples/contrato_muestra.png  contrato
python main.py samples/identidad_muestra.png identidad
```

Cada comando imprime un JSON con `"success": true` y los campos extraídos por Claude.

## Estructura del proyecto

```
.
├── requirements.txt
├── schemas.py               # Esquemas Pydantic + mapeador SCHEMA_MAP
├── converter.py             # Archivo -> imagen -> Base64
├── extractor.py             # Prompt, llamada a Claude y reintento de corrección
├── main.py                  # Pipeline unificado + CLI
├── samples/
│   ├── create_samples.py    # Genera los documentos de muestra con Pillow
│   ├── factura_muestra.png
│   ├── contrato_muestra.png
│   └── identidad_muestra.png
└── tests/
    └── test_extractor.py
```

## Manejo de errores

La CLI captura las excepciones y devuelve un JSON con un código de error:

| Código                  | Causa                                                        |
|-------------------------|--------------------------------------------------------------|
| `INVALID_DOCUMENT_TYPE` | El tipo de documento no está en `SCHEMA_MAP`.                |
| `FILE_TOO_LARGE`        | El archivo supera el tamaño máximo permitido.                |
| `UNSUPPORTED_FILE_TYPE` | El formato no es PDF, PNG ni JPEG.                            |
| `FILE_CONVERSION_ERROR` | Error al leer o convertir el archivo (p. ej. falta poppler). |
| `ILLEGIBLE_DOCUMENT`    | Claude reportó que el documento es ilegible.                 |
| `EXTRACTION_FAILED`     | El JSON falló la validación incluso tras el reintento.       |
| `UNEXPECTED_ERROR`      | Cualquier otro error no contemplado.                         |

## Cómo agregar un cuarto tipo de documento

El sistema es extensible: el prompt se genera automáticamente a partir del JSON
Schema de Pydantic, así que **no hay que tocar la lógica del LLM**. Sigue estos
pasos.

### Paso 1: Define el nuevo esquema en `schemas.py`

Crea una clase que herede de `BaseModel`, con una `description` clara en cada
campo (esas descripciones guían a Claude durante la extracción):

```python
class CertificadoSchema(BaseModel):
    """Esquema de extracción para un certificado académico."""

    nombre_estudiante: str = Field(..., description="Nombre completo del estudiante.")
    institucion: str = Field(..., description="Nombre de la institución que emite el certificado.")
    programa: Optional[str] = Field(None, description="Programa o curso certificado.")
    fecha_emision: Optional[str] = Field(None, description="Fecha de emisión en formato ISO 8601 (YYYY-MM-DD).")
```

### Paso 2: Regístralo en el mapeador `SCHEMA_MAP`

En el mismo archivo, agrega una entrada con la clave que usarás como tipo:

```python
SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
    "factura": FacturaSchema,
    "contrato": ContratoSchema,
    "identidad": IdentidadSchema,
    "certificado": CertificadoSchema,   # <-- nueva línea
}
```

### Paso 3: ¡Listo!

No se necesita nada más. La CLI toma sus opciones de `SCHEMA_MAP`, por lo que el
nuevo tipo queda disponible automáticamente:

```bash
python main.py ruta/al/certificado.pdf certificado
```

### Paso 4 (recomendado): Agrega una prueba

En `tests/test_extractor.py`, replica los casos de éxito/reintento usando tu
nuevo esquema para garantizar que la extracción funciona como esperas.
