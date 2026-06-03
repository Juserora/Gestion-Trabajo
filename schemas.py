"""
schemas.py
==========
Definición de los esquemas Pydantic (v2) para cada tipo de documento soportado
por el Document Extraction Pipeline.

Cada campo incluye una descripción (`Field(description=...)`) que se inyecta en
el prompt enviado a Claude para guiar la extracción. Las descripciones claras
mejoran significativamente la calidad de los datos extraídos.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# FACTURA
# ---------------------------------------------------------------------------
class ItemFactura(BaseModel):
    """Línea de detalle (ítem) dentro de una factura."""

    descripcion: str = Field(
        ..., description="Descripción del producto o servicio facturado."
    )
    cantidad: float = Field(
        ..., description="Cantidad de unidades del ítem. Usa números, no texto."
    )
    precio_unitario: float = Field(
        ..., description="Precio por unidad del ítem, sin impuestos."
    )
    total_linea: float = Field(
        ..., description="Total de la línea (cantidad * precio_unitario)."
    )


class FacturaSchema(BaseModel):
    """Esquema de extracción para una factura comercial."""

    numero_factura: str = Field(
        ..., description="Número o consecutivo único de la factura."
    )
    fecha_emision: Optional[str] = Field(
        None,
        description="Fecha de emisión de la factura en formato ISO 8601 (YYYY-MM-DD).",
    )
    emisor_nombre: str = Field(
        ..., description="Razón social o nombre de quien emite la factura."
    )
    emisor_identificacion: Optional[str] = Field(
        None,
        description="Identificación tributaria del emisor (NIT, RUT o equivalente).",
    )
    receptor_nombre: Optional[str] = Field(
        None, description="Nombre o razón social del cliente o receptor."
    )
    receptor_identificacion: Optional[str] = Field(
        None, description="Identificación tributaria del receptor, si aparece."
    )
    moneda: Optional[str] = Field(
        None, description="Código o símbolo de la moneda (ej. COP, USD, $)."
    )
    subtotal: Optional[float] = Field(
        None, description="Valor total antes de impuestos."
    )
    impuestos: Optional[float] = Field(
        None, description="Valor total de impuestos (ej. IVA)."
    )
    total: float = Field(
        ..., description="Valor total a pagar, incluyendo impuestos."
    )
    items: List[ItemFactura] = Field(
        default_factory=list,
        description="Lista de ítems o líneas de detalle de la factura.",
    )


# ---------------------------------------------------------------------------
# CONTRATO
# ---------------------------------------------------------------------------
class ContratoSchema(BaseModel):
    """Esquema de extracción para un contrato."""

    tipo_contrato: Optional[str] = Field(
        None,
        description="Tipo o naturaleza del contrato (ej. arrendamiento, prestación de servicios).",
    )
    partes: List[str] = Field(
        default_factory=list,
        description="Nombres de las partes que firman el contrato.",
    )
    objeto: Optional[str] = Field(
        None, description="Objeto o propósito principal del contrato (resumen breve)."
    )
    fecha_inicio: Optional[str] = Field(
        None,
        description="Fecha de inicio de vigencia en formato ISO 8601 (YYYY-MM-DD).",
    )
    fecha_fin: Optional[str] = Field(
        None,
        description="Fecha de finalización en formato ISO 8601 (YYYY-MM-DD), si aplica.",
    )
    valor: Optional[float] = Field(
        None, description="Valor monetario total del contrato, si se especifica."
    )
    moneda: Optional[str] = Field(
        None, description="Moneda del valor del contrato (ej. COP, USD)."
    )
    jurisdiccion: Optional[str] = Field(
        None, description="Ley aplicable o jurisdicción que rige el contrato."
    )
    obligaciones_clave: List[str] = Field(
        default_factory=list,
        description="Lista de obligaciones o cláusulas más relevantes (resumidas).",
    )


# ---------------------------------------------------------------------------
# DOCUMENTO DE IDENTIDAD
# ---------------------------------------------------------------------------
class IdentidadSchema(BaseModel):
    """Esquema de extracción para un documento de identidad."""

    tipo_documento: Optional[str] = Field(
        None,
        description="Tipo de documento (ej. cédula de ciudadanía, pasaporte, DNI).",
    )
    numero_documento: str = Field(
        ..., description="Número de identificación del documento."
    )
    nombres: str = Field(..., description="Nombres del titular del documento.")
    apellidos: str = Field(..., description="Apellidos del titular del documento.")
    fecha_nacimiento: Optional[str] = Field(
        None, description="Fecha de nacimiento en formato ISO 8601 (YYYY-MM-DD)."
    )
    sexo: Optional[str] = Field(
        None, description="Sexo o género indicado en el documento (ej. M, F)."
    )
    nacionalidad: Optional[str] = Field(
        None, description="Nacionalidad del titular, si aparece."
    )
    fecha_expedicion: Optional[str] = Field(
        None, description="Fecha de expedición en formato ISO 8601 (YYYY-MM-DD)."
    )
    fecha_vencimiento: Optional[str] = Field(
        None,
        description="Fecha de vencimiento en formato ISO 8601 (YYYY-MM-DD), si aplica.",
    )


# ---------------------------------------------------------------------------
# MAPEADOR DE TIPOS DE DOCUMENTO
# ---------------------------------------------------------------------------
SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
    "factura": FacturaSchema,
    "contrato": ContratoSchema,
    "identidad": IdentidadSchema,
}
