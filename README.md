# Document Extraction Pipeline

Módulo en Python que recibe un archivo (PDF o imagen) y devuelve un JSON con los campos clave del documento usando Claude como motor de extracción.

Soporta facturas, contratos y documentos de identidad. Si Claude devuelve un JSON que no pasa la validación, reintenta una vez con el error incluido en el prompt.

## Requisitos

- Python 3.10+
- poppler en el sistema (solo para PDFs):
  - Ubuntu/WSL: `sudo apt-get install poppler-utils`
  - macOS: `brew install poppler`
  - Windows: descarga los binarios y agrega la carpeta `bin` al PATH

## Instalación

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

Configura la API key:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Windows: $env:ANTHROPIC_API_KEY="sk-ant-..."
```

Desde la línea de comandos:
```bash
python main.py documento.pdf factura
python main.py cedula.jpg identidad
```

O desde código:
```python
from main import extract_document

datos = extract_document("documento.pdf", "factura")
print(datos)
```

## Tests

Los tests usan mocks y no requieren API key:
```bash
python -m pytest
```

Para probar con documentos reales, genera los archivos de muestra:
```bash
python samples/create_samples.py

python main.py samples/factura_muestra.png   factura
python main.py samples/contrato_muestra.png  contrato
python main.py samples/identidad_muestra.png identidad
```

## Estructura

```
esquemas.py              # Esquemas Pydantic por tipo de documento
convertidor.py           # Convierte PDF/imagen a base64
extractor.py             # Llama a Claude y maneja el reintento
main.py                  # Función principal + CLI
samples/
  create_samples.py      # Genera documentos de prueba
  factura_muestra.png
  contrato_muestra.png
  identidad_muestra.png
tests/
  test_extractor.py
```

## Cómo agregar un nuevo tipo de documento

Define el schema en `esquemas.py`:

```python
class CertificadoSchema(BaseModel):
    nombre_estudiante: str = Field(..., description="Nombre completo del estudiante.")
    institucion: str = Field(..., description="Institución que emite el certificado.")
    programa: Optional[str] = Field(None, description="Programa o curso certificado.")
    fecha_emision: Optional[str] = Field(None, description="Fecha de emisión (YYYY-MM-DD).")
```

Regístralo en el `SCHEMA_MAP` de `esquemas.py`:

```python
SCHEMA_MAP = {
    "factura": FacturaSchema,
    "contrato": ContratoSchema,
    "identidad": IdentidadSchema,
    "certificado": CertificadoSchema,  # nueva línea
}
```

Listo. El prompt se genera automáticamente a partir del schema, así que no hay que tocar nada más.
