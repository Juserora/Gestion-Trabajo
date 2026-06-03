"""
samples/create_samples.py
=========================
Genera tres documentos de muestra (PNG) con datos ficticios para probar
el pipeline de extracción sin necesidad de documentos reales confidenciales.

Ejecutar desde la raíz del proyecto:
    python samples/create_samples.py

Requiere únicamente Pillow (ya incluido en requirements.txt).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
OUT_DIR = Path(__file__).parent
PAGE_W, PAGE_H = 794, 1123          # A4 a 96 dpi
BG_COLOR = (255, 255, 255)
INK = (20, 20, 20)
ACCENT = (30, 90, 180)
GRAY = (120, 120, 120)
LIGHT_GRAY = (230, 230, 235)
RED_ACCENT = (180, 30, 30)

# Fuente del sistema (no requiere instalación adicional).
try:
    _font_path = "arial.ttf"
    ImageFont.truetype(_font_path, 12)
except OSError:
    _font_path = None   # Fallback a la fuente bitmap integrada de Pillow.


def _font(size: int, bold: bool = False):
    if _font_path is None:
        return ImageFont.load_default()
    # En muchos sistemas hay arial.ttf y arialbd.ttf; intentamos ambos.
    if bold:
        for name in ("arialbd.ttf", "Arial Bold.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
    return ImageFont.truetype(_font_path, size)


def _new_page() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (PAGE_W, PAGE_H), BG_COLOR)
    return img, ImageDraw.Draw(img)


def _hline(draw: ImageDraw.ImageDraw, y: int, color=LIGHT_GRAY, width: int = 1,
           x0: int = 40, x1: int | None = None) -> None:
    draw.line([(x0, y), (x1 or PAGE_W - 40, y)], fill=color, width=width)


def _text(draw: ImageDraw.ImageDraw, xy: tuple, text: str, size: int = 11,
          color=INK, bold: bool = False, align: str = "left") -> None:
    draw.text(xy, text, font=_font(size, bold), fill=color, align=align)


def _rect(draw: ImageDraw.ImageDraw, box: tuple, fill=LIGHT_GRAY,
          outline=None) -> None:
    draw.rectangle(box, fill=fill, outline=outline)


# ---------------------------------------------------------------------------
# Factura
# ---------------------------------------------------------------------------
def create_factura(path: Path) -> None:
    img, draw = _new_page()

    # Encabezado
    _rect(draw, (0, 0, PAGE_W, 90), fill=ACCENT)
    _text(draw, (40, 18), "TECNOSERVICIOS S.A.S.", size=20, color=(255,255,255), bold=True)
    _text(draw, (40, 52), "NIT: 900.123.456-7  |  Bogotá, Colombia", size=11, color=(200, 220, 255))

    _rect(draw, (PAGE_W - 210, 95, PAGE_W - 40, 155), fill=(240, 245, 255), outline=LIGHT_GRAY)
    _text(draw, (PAGE_W - 200, 100), "FACTURA DE VENTA", size=13, color=ACCENT, bold=True)
    _text(draw, (PAGE_W - 200, 120), "No. FV-2025-004821", size=11, color=INK)
    _text(draw, (PAGE_W - 200, 137), "Fecha: 2025-03-15", size=11, color=INK)

    y = 175
    _text(draw, (40, y), "DATOS DEL CLIENTE", size=10, color=GRAY, bold=True)
    _hline(draw, y + 16, color=ACCENT, width=2)
    y += 26
    _text(draw, (40, y),  "Nombre:",          size=11, bold=True)
    _text(draw, (160, y), "Distribuidora El Progreso Ltda.", size=11)
    y += 20
    _text(draw, (40, y),  "NIT:",             size=11, bold=True)
    _text(draw, (160, y), "800.987.654-3", size=11)
    y += 20
    _text(draw, (40, y),  "Dirección:",       size=11, bold=True)
    _text(draw, (160, y), "Cra. 7 # 45-22, Medellín, Antioquia", size=11)
    y += 20
    _text(draw, (40, y),  "Teléfono:",        size=11, bold=True)
    _text(draw, (160, y), "+57 604 555 0123", size=11)

    # Tabla de ítems
    y += 45
    _text(draw, (40, y), "DETALLE DE PRODUCTOS / SERVICIOS", size=10, color=GRAY, bold=True)
    _hline(draw, y + 16, color=ACCENT, width=2)
    y += 26

    _rect(draw, (40, y, PAGE_W - 40, y + 22), fill=ACCENT)
    cols = [40, 310, 430, 560, 680]
    headers = ["Descripción", "Cant.", "Precio Unit.", "Total línea"]
    for i, h in enumerate(headers):
        _text(draw, (cols[i] + 5, y + 4), h, size=10, color=(255,255,255), bold=True)
    y += 22

    items = [
        ("Licencia software ERP anual",    "2",   "3.200.000",  "6.400.000"),
        ("Soporte técnico remoto (mes)",   "3",     "450.000",  "1.350.000"),
        ("Capacitación usuarios (hora)",   "8",     "180.000",  "1.440.000"),
        ("Migración de datos (proyecto)",  "1",   "2.100.000",  "2.100.000"),
    ]
    for idx, (desc, cant, precio, total) in enumerate(items):
        fill = BG_COLOR if idx % 2 == 0 else (245, 247, 252)
        _rect(draw, (40, y, PAGE_W - 40, y + 22), fill=fill)
        _text(draw, (cols[0] + 5, y + 4), desc,   size=10)
        _text(draw, (cols[1] + 5, y + 4), cant,   size=10)
        _text(draw, (cols[2] + 5, y + 4), precio, size=10)
        _text(draw, (cols[3] + 5, y + 4), total,  size=10)
        y += 22

    _hline(draw, y, color=ACCENT)
    y += 15

    # Totales
    for label, value in [
        ("Subtotal:",   "COP 11.290.000"),
        ("IVA (19%):",  "COP  2.145.100"),
        ("TOTAL:",      "COP 13.435.100"),
    ]:
        bold = label == "TOTAL:"
        color = ACCENT if bold else INK
        size = 13 if bold else 11
        _text(draw, (PAGE_W - 280, y), label, size=size, bold=bold, color=color)
        _text(draw, (PAGE_W - 160, y), value, size=size, bold=bold, color=color)
        y += 22 if not bold else 0

    # Pie
    y = PAGE_H - 100
    _hline(draw, y)
    _text(draw, (40, y + 10), "Condiciones de pago: 30 días neto.", size=10, color=GRAY)
    _text(draw, (40, y + 28), "Banco: Bancolombia  |  Cuenta corriente: 123-456789-00", size=10, color=GRAY)
    _text(draw, (40, y + 46), "Este documento es válido como factura electrónica (DIAN).", size=9, color=GRAY)

    img.save(path, format="PNG", optimize=True)
    print(f"  OK  {path.name}")


# ---------------------------------------------------------------------------
# Contrato
# ---------------------------------------------------------------------------
def create_contrato(path: Path) -> None:
    img, draw = _new_page()

    _rect(draw, (0, 0, PAGE_W, 80), fill=(50, 50, 80))
    _text(draw, (40, 15), "CONTRATO DE PRESTACIÓN DE SERVICIOS", size=16,
          color=(255, 255, 255), bold=True)
    _text(draw, (40, 50), "Contrato No. CPS-2025-0037", size=12, color=(180, 180, 220))

    y = 105
    _text(draw, (40, y),
          "En la ciudad de Bogotá D.C., a los veinte (20) días del mes de enero de dos mil",
          size=11)
    y += 18
    _text(draw, (40, y),
          "veinticinco (2025), las partes que se indican a continuación celebran el presente",
          size=11)
    y += 18
    _text(draw, (40, y), "contrato de prestación de servicios profesionales, sujeto a las", size=11)
    y += 18
    _text(draw, (40, y), "siguientes cláusulas:", size=11)

    y += 30
    _text(draw, (40, y), "PARTES", size=12, bold=True, color=ACCENT)
    _hline(draw, y + 18, color=ACCENT, width=2)
    y += 28

    for label, value in [
        ("CONTRATANTE:", "INVERSIONES ROCA S.A.S., NIT 901.234.567-8, representada por"),
        ("",              "su gerente general, señor Andrés Felipe Roca Bermúdez,"),
        ("",              "identificado con C.C. 79.654.321 de Bogotá."),
        ("CONTRATISTA:",  "María Alejandra Torres Vargas, identificada con C.C."),
        ("",              "1.032.567.890 de Bogotá, consultora independiente en"),
        ("",              "transformación digital."),
    ]:
        bold = bool(label)
        _text(draw, (40, y), label, size=11, bold=bold, color=ACCENT if bold else INK)
        _text(draw, (180 if bold else 40, y), value, size=11)
        y += 18
    y += 10

    clauses = [
        ("PRIMERA – OBJETO:",
         "La CONTRATISTA se obliga a prestar servicios de consultoría en transformación\n"
         "digital e implementación de sistemas ERP para el CONTRATANTE, de acuerdo con\n"
         "el plan de trabajo aprobado por ambas partes el 15 de enero de 2025."),
        ("SEGUNDA – DURACIÓN:",
         "El presente contrato tendrá una vigencia de seis (6) meses, contados a partir\n"
         "del 20 de enero de 2025, con fecha de finalización el 20 de julio de 2025.\n"
         "Podrá prorrogarse mediante acuerdo escrito firmado por ambas partes."),
        ("TERCERA – VALOR Y FORMA DE PAGO:",
         "El valor total del contrato es de VEINTICUATRO MILLONES DE PESOS\n"
         "COLOMBIANOS (COP 24.000.000), pagaderos en cuotas mensuales iguales\n"
         "de COP 4.000.000 dentro de los primeros cinco (5) días de cada mes."),
        ("CUARTA – OBLIGACIONES DEL CONTRATISTA:",
         "Entregar informes de avance quincenales; asistir a las reuniones de\n"
         "seguimiento; guardar absoluta confidencialidad sobre la información del\n"
         "CONTRATANTE; y cumplir los entregables definidos en el plan de trabajo."),
        ("QUINTA – JURISDICCIÓN:",
         "Las partes acuerdan que cualquier controversia derivada del presente\n"
         "contrato será resuelta conforme a las leyes de la República de Colombia,\n"
         "sometiéndose a la jurisdicción de los jueces civiles de Bogotá D.C."),
    ]

    for title, body in clauses:
        _text(draw, (40, y), title, size=11, bold=True, color=(50, 50, 80))
        y += 18
        for line in body.split("\n"):
            _text(draw, (40, y), line, size=11)
            y += 17
        y += 8

    y = PAGE_H - 140
    _hline(draw, y)
    y += 20
    for name, role, cc in [
        ("____________________________", "____________________________", ""),
        ("Andrés Felipe Roca Bermúdez", "María Alejandra Torres Vargas", ""),
        ("Representante Legal",         "Contratista",                   ""),
        ("INVERSIONES ROCA S.A.S.",     "C.C. 1.032.567.890",            ""),
    ]:
        _text(draw, (80,  y), name, size=10)
        _text(draw, (450, y), role, size=10)
        y += 16

    img.save(path, format="PNG", optimize=True)
    print(f"  OK  {path.name}")


# ---------------------------------------------------------------------------
# Documento de identidad
# ---------------------------------------------------------------------------
def create_identidad(path: Path) -> None:
    W, H = 638, 402      # Proporción tarjeta ID (8,56 cm × 5,40 cm a 75 dpi)
    img = Image.new("RGB", (W, H), (245, 245, 250))
    draw = ImageDraw.Draw(img)

    # Banda superior
    _rect(draw, (0, 0, W, 55), fill=(18, 52, 120))
    _text(draw, (20, 8),  "REPÚBLICA DE COLOMBIA",       size=13, color=(255,255,255), bold=True)
    _text(draw, (20, 30), "CÉDULA DE CIUDADANÍA",        size=11, color=(180, 210, 255))

    # Banda inferior
    _rect(draw, (0, H - 38, W, H), fill=(18, 52, 120))
    _text(draw, (20, H - 28), "Documento válido en todo el territorio nacional", size=9,
          color=(180, 210, 255))

    # Foto (placeholder)
    _rect(draw, (20, 70, 145, 220), fill=(200, 200, 210), outline=(150, 150, 160))
    _text(draw, (45, 138), "FOTO", size=14, color=(150, 150, 160), bold=True)

    # Datos personales
    x, y0 = 165, 68
    pairs = [
        ("Apellidos",        "RODRÍGUEZ RAMÍREZ"),
        ("Nombres",          "JUAN SEBASTIÁN"),
        ("Número",           "1.020.304.050"),
        ("Fecha nacimiento", "01-ENE-2005"),
        ("Lugar expedición", "BOGOTÁ D.C."),
        ("Fecha expedición", "15-ENE-2023"),
        ("Fecha vencimiento","15-ENE-2033"),
        ("Sexo",             "M"),
        ("Nacionalidad",     "COLOMBIANA"),
    ]
    for label, value in pairs:
        _text(draw, (x, y0),      label.upper(), size=8,  color=(100, 100, 130))
        _text(draw, (x, y0 + 12), value,         size=10, bold=True)
        y0 += 30

    # MRZ simulada
    _rect(draw, (0, H - 80, W, H - 38), fill=(230, 230, 240))
    _text(draw, (20, H - 76), "IDCOL1020304050<<<<<<<<<<<<<<<7", size=8, color=(60, 60, 80))
    _text(draw, (20, H - 60), "0501011M3301151COL<<<<<<<<<<<6", size=8, color=(60, 60, 80))
    _text(draw, (20, H - 44), "RODRIGUEZ<<RAMIREZ<<JUAN<<SEBASTIAN<<<<<<", size=8, color=(60, 60, 80))

    img = img.resize((PAGE_W - 80, int((PAGE_W - 80) * H / W)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (PAGE_W, PAGE_H), BG_COLOR)

    y_offset = 60
    canvas.paste(img, (40, y_offset))
    draw2 = ImageDraw.Draw(canvas)

    note_y = y_offset + img.height + 30
    _text(draw2, (40, note_y),
          "Documento de identidad — muestra sintética para pruebas de extracción.",
          size=10, color=GRAY)
    _text(draw2, (40, note_y + 18),
          "Los datos son ficticios y no corresponden a ninguna persona real.",
          size=10, color=GRAY)

    canvas.save(path, format="PNG", optimize=True)
    print(f"  OK  {path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("Generando archivos de muestra en samples/...")
    create_factura(OUT_DIR / "factura_muestra.png")
    create_contrato(OUT_DIR / "contrato_muestra.png")
    create_identidad(OUT_DIR / "identidad_muestra.png")
    print("\nListo. Prueba la extracción con:")
    print("  python main.py samples/factura_muestra.png   factura")
    print("  python main.py samples/contrato_muestra.png  contrato")
    print("  python main.py samples/identidad_muestra.png identidad")


if __name__ == "__main__":
    main()
