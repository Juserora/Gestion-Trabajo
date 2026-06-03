from __future__ import annotations

from typing import Dict, List, Optional, Type

from pydantic import BaseModel, Field


class ItemFactura(BaseModel):
    descripcion: str = Field(..., description="Descripción del producto o servicio facturado.")
    cantidad: float = Field(..., description="Cantidad de unidades del ítem. Usa números, no texto.")
    precio_unitario: float = Field(..., description="Precio por unidad del ítem, sin impuestos.")
    total_linea: float = Field(..., description="Total de la línea (cantidad * precio_unitario).")


class FacturaSchema(BaseModel):
    numero_factura: str = Field(..., description="Número de la factura.")
    fecha_emision: Optional[str] = Field(None, description="Fecha de emisión (YYYY-MM-DD).")
    emisor_nombre: str = Field(..., description="Nombre o razón social del emisor.")
    emisor_identificacion: Optional[str] = Field(None, description="NIT o identificación tributaria del emisor.")
    receptor_nombre: Optional[str] = Field(None, description="Nombre del cliente o receptor.")
    receptor_identificacion: Optional[str] = Field(None, description="Identificación del receptor, si aparece.")
    moneda: Optional[str] = Field(None, description="Código o símbolo de la moneda (ej. COP, USD, $).")
    subtotal: Optional[float] = Field(None, description="Valor total antes de impuestos.")
    impuestos: Optional[float] = Field(None, description="Valor total de impuestos (ej. IVA).")
    total: float = Field(..., description="Valor total a pagar, incluyendo impuestos.")
    items: List[ItemFactura] = Field(default_factory=list, description="Lista de ítems o líneas de detalle de la factura.")


class ContratoSchema(BaseModel):
    tipo_contrato: Optional[str] = Field(None, description="Tipo de contrato (ej. arrendamiento, prestación de servicios).")
    partes: List[str] = Field(default_factory=list, description="Partes que firman el contrato.")
    objeto: Optional[str] = Field(None, description="Objeto del contrato, resumen breve.")
    fecha_inicio: Optional[str] = Field(None, description="Fecha de inicio de vigencia en formato ISO 8601 (YYYY-MM-DD).")
    fecha_fin: Optional[str] = Field(None, description="Fecha de finalización en formato ISO 8601 (YYYY-MM-DD), si aplica.")
    valor: Optional[float] = Field(None, description="Valor monetario total del contrato, si se especifica.")
    moneda: Optional[str] = Field(None, description="Moneda del valor del contrato (ej. COP, USD).")
    jurisdiccion: Optional[str] = Field(None, description="Ley aplicable o jurisdicción que rige el contrato.")
    obligaciones_clave: List[str] = Field(default_factory=list, description="Lista de obligaciones o cláusulas más relevantes (resumidas).")


class IdentidadSchema(BaseModel):
    tipo_documento: Optional[str] = Field(None, description="Tipo de documento (ej. cédula de ciudadanía, pasaporte, DNI).")
    numero_documento: str = Field(..., description="Número de identificación del documento.")
    nombres: str = Field(..., description="Nombres del titular del documento.")
    apellidos: str = Field(..., description="Apellidos del titular del documento.")
    fecha_nacimiento: Optional[str] = Field(None, description="Fecha de nacimiento en formato ISO 8601 (YYYY-MM-DD).")
    sexo: Optional[str] = Field(None, description="Sexo o género indicado en el documento (ej. M, F).")
    nacionalidad: Optional[str] = Field(None, description="Nacionalidad del titular, si aparece.")
    fecha_expedicion: Optional[str] = Field(None, description="Fecha de expedición en formato ISO 8601 (YYYY-MM-DD).")
    fecha_vencimiento: Optional[str] = Field(None, description="Fecha de vencimiento en formato ISO 8601 (YYYY-MM-DD), si aplica.")


SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
    "factura": FacturaSchema,
    "contrato": ContratoSchema,
    "identidad": IdentidadSchema,
}
