# services/precio_service.py - Cálculo y verificación de costos de contratos
"""
Fuente ÚNICA de los cálculos de dinero del sistema.
El formulario de contratos, el visor, el PDF y la verificación usan estas funciones,
así el total que se ve en pantalla es exactamente el que se guarda y se imprime.
"""
import calendar
import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple, Optional

from services.db_service import PAQUETES, obtener_conexion

# Costos de servicios especiales (USD)
COSTO_CREMACION = 250.00
COSTOS_TRASLADO = {
    "Local": 0.00,
    "Regional": 300.00,
    "Nacional": 800.00,
    "Externo": 0.00,   # Traslado externo: no lo presta la funeraria, no se cobra
}
TIPOS_TRASLADO = ["Local", "Regional", "Nacional", "Externo"]

TIPOS_CONTRATO = ["Inmediato", "Largo Plazo"]

TOLERANCIA = 0.01  # diferencia máxima aceptada por redondeo


def r2(valor) -> float:
    """Redondeo comercial a 2 decimales (0.125 -> 0.13), evita errores de coma flotante"""
    return float(Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def etiqueta_traslado(tipo: str) -> str:
    """Texto para mostrar en el combo: 'Regional (+$300.00)'"""
    if tipo == "Externo":
        return "Externo (no incluido)"
    costo = COSTOS_TRASLADO.get(tipo, 0)
    return f"{tipo} (+${costo:,.2f})" if costo > 0 else tipo


def traslado_desde_etiqueta(etiqueta: str) -> str:
    """Convierte la etiqueta del combo en el tipo de traslado guardado"""
    for tipo in TIPOS_TRASLADO:
        if (etiqueta or "").startswith(tipo):
            return tipo
    return "Local"


def calcular_desglose(paquete: str, requiere_cremacion: bool, tipo_traslado: str,
                      productos: List[Dict], servicios: List[Dict],
                      pnf_asociado: bool = False, pnf_cubre_traslado: bool = False,
                      pnf_cubre_cremacion: bool = False) -> Dict:
    """
    Calcula todas las partes del costo de un contrato.
    productos / servicios: listas de dicts con 'cantidad' y 'precio'.
    Si el contrato está asociado a PNF, lo que el PNF cubre se descuenta (descuento_pnf).
    """
    if paquete not in PAQUETES:
        raise ValueError(f"Paquete desconocido: {paquete}")

    costo_paquete = r2(PAQUETES[paquete]["precio"])
    costo_cremacion = r2(COSTO_CREMACION if requiere_cremacion else 0)
    costo_traslado = r2(COSTOS_TRASLADO.get(tipo_traslado or "Local", 0))
    costo_productos = r2(sum(r2(p["cantidad"]) * r2(p["precio"]) for p in productos))
    costo_servicios = r2(sum(r2(s["cantidad"]) * r2(s["precio"]) for s in servicios))

    descuento_pnf = 0.0
    if pnf_asociado:
        if pnf_cubre_cremacion:
            descuento_pnf += costo_cremacion
        if pnf_cubre_traslado:
            descuento_pnf += costo_traslado
    descuento_pnf = r2(descuento_pnf)

    subtotal = r2(costo_paquete + costo_cremacion + costo_traslado + costo_productos + costo_servicios)
    total = r2(subtotal - descuento_pnf)

    return {
        "costo_paquete": costo_paquete,
        "costo_cremacion": costo_cremacion,
        "costo_traslado": costo_traslado,
        "costo_productos": costo_productos,
        "costo_servicios": costo_servicios,
        "subtotal": subtotal,
        "descuento_pnf": descuento_pnf,
        "total": total,
    }


def lineas_desglose(desglose: Dict, paquete: str = "", tipo_traslado: str = "") -> List[Tuple[str, float]]:
    """Lista de (concepto, monto) lista para mostrar en pantalla / PDF"""
    lineas = [(f"Paquete {paquete}".strip(), desglose["costo_paquete"])]
    if desglose["costo_cremacion"]:
        lineas.append(("Cremación", desglose["costo_cremacion"]))
    if desglose["costo_traslado"]:
        lineas.append((f"Traslado {tipo_traslado}".strip(), desglose["costo_traslado"]))
    if desglose["costo_productos"]:
        lineas.append(("Productos adicionales", desglose["costo_productos"]))
    if desglose["costo_servicios"]:
        lineas.append(("Servicios adicionales", desglose["costo_servicios"]))
    if desglose["descuento_pnf"]:
        lineas.append(("Cubierto por PNF", -desglose["descuento_pnf"]))
    return lineas


def validar_financiamiento(total: float, inicial: float, numero_cuotas: int) -> Tuple[bool, str]:
    """Valida inicial y número de cuotas de un contrato financiado"""
    if inicial < 0:
        return False, "La inicial no puede ser negativa"
    if r2(inicial) >= r2(total):
        return False, (f"La inicial (${inicial:,.2f}) cubre todo el total (${total:,.2f}).\n"
                       f"Seleccione la modalidad 'Contado'.")
    if numero_cuotas < 1:
        return False, "El número de cuotas debe ser al menos 1"
    if numero_cuotas > 120:
        return False, "El número máximo de cuotas es 120"
    return True, "OK"


def sumar_meses(fecha: datetime.date, meses: int) -> datetime.date:
    """Suma meses respetando el fin de mes (31/01 + 1 mes = 28/02 o 29/02)"""
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return datetime.date(anio, mes, dia)


def calcular_fecha_vencimiento(fecha_base: datetime.date, i: int, frecuencia: str = "Mensual") -> datetime.date:
    """Calcula fecha de vencimiento según la periodicidad: Semanal, Quincenal, Mensual, Trimestral"""
    freq = (frecuencia or "Mensual").strip().capitalize()
    if freq == "Semanal":
        return fecha_base + datetime.timedelta(days=7 * i)
    elif freq == "Quincenal":
        return fecha_base + datetime.timedelta(days=15 * i)
    elif freq == "Trimestral":
        return sumar_meses(fecha_base, 3 * i)
    else:  # Mensual
        return sumar_meses(fecha_base, i)


def generar_plan_cuotas(total: float, inicial: float, numero_cuotas: int,
                        fecha_base: Optional[datetime.date] = None,
                        frecuencia: str = "Mensual") -> List[Dict]:
    """
    Divide el saldo (total - inicial) en cuotas periódicas (Semanal, Quincenal, Mensual, Trimestral).
    La última cuota absorbe la diferencia de redondeo, así la suma es EXACTA.
    """
    fecha_base = fecha_base or datetime.date.today()
    saldo = r2(total - inicial)
    if numero_cuotas < 1 or saldo <= 0:
        return []
    cuota_base = r2(saldo / numero_cuotas)
    plan = []
    acumulado = 0.0
    for i in range(1, numero_cuotas + 1):
        monto = cuota_base if i < numero_cuotas else r2(saldo - acumulado)
        acumulado = r2(acumulado + monto)
        venc = calcular_fecha_vencimiento(fecha_base, i, frecuencia)
        plan.append({
            "numero": i,
            "monto": monto,
            "fecha_vencimiento": venc.strftime("%Y-%m-%d"),
        })
    return plan



def verificar_contrato(contrato_id: int) -> Dict:
    """
    Recalcula el total de un contrato a partir de sus partes y lo compara con lo guardado.
    Devuelve {'ok': bool, 'lineas': [...], 'total_guardado', 'total_calculado', 'problemas': [...]}
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    row = cursor.execute("""
        SELECT paquete, requiere_cremacion, tipo_traslado, monto_total, pagado, metodo_pago, inicial,
               costo_paquete, costo_cremacion, costo_traslado, costo_productos, costo_servicios,
               COALESCE(descuento_pnf, 0), COALESCE(pnf_asociado, 0)
        FROM contratos WHERE id = ?
    """, (contrato_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "problemas": ["Contrato no encontrado"], "lineas": [],
                "total_guardado": 0, "total_calculado": 0}

    (paquete, cremacion, traslado, monto_total, pagado, metodo, inicial,
     c_paq, c_crem, c_tras, c_prod, c_serv, desc_pnf, pnf) = row

    productos_reales = r2(cursor.execute(
        "SELECT COALESCE(SUM(cantidad * precio_unitario), 0) FROM contrato_productos WHERE contrato_id = ?",
        (contrato_id,)).fetchone()[0])
    servicios_reales = r2(cursor.execute(
        "SELECT COALESCE(SUM(cantidad * precio_unitario), 0) FROM contratos_servicios WHERE contrato_id = ?",
        (contrato_id,)).fetchone()[0])
    servicios_subtotales = r2(cursor.execute(
        "SELECT COALESCE(SUM(subtotal), 0) FROM contratos_servicios WHERE contrato_id = ?",
        (contrato_id,)).fetchone()[0])
    pagos_reales = r2(cursor.execute(
        "SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE contrato_id = ?", (contrato_id,)).fetchone()[0])
    cuotas = cursor.execute("SELECT COALESCE(SUM(monto), 0), COUNT(*) FROM cuotas WHERE contrato_id = ?",
                            (contrato_id,)).fetchone()
    conn.close()

    # Si el contrato es antiguo y no tiene desglose guardado, se usan los precios estándar
    c_paq = r2(c_paq if c_paq is not None else PAQUETES.get(paquete, {}).get("precio", 0))
    c_crem = r2(c_crem if c_crem is not None else (COSTO_CREMACION if cremacion else 0))
    c_tras = r2(c_tras if c_tras is not None else COSTOS_TRASLADO.get(traslado or "Local", 0))

    desglose = {
        "costo_paquete": c_paq,
        "costo_cremacion": c_crem,
        "costo_traslado": c_tras,
        "costo_productos": productos_reales,
        "costo_servicios": servicios_reales,
        "descuento_pnf": r2(desc_pnf),
    }
    total_calculado = r2(c_paq + c_crem + c_tras + productos_reales + servicios_reales - r2(desc_pnf))
    desglose["subtotal"] = r2(total_calculado + r2(desc_pnf))
    desglose["total"] = total_calculado

    problemas = []
    if abs(total_calculado - r2(monto_total)) > TOLERANCIA:
        problemas.append(f"El total guardado (${monto_total:,.2f}) no coincide con la suma de sus partes "
                         f"(${total_calculado:,.2f}). Diferencia: ${monto_total - total_calculado:,.2f}")
    if c_prod is not None and abs(r2(c_prod) - productos_reales) > TOLERANCIA:
        problemas.append(f"Productos: guardado ${c_prod:,.2f} vs detalle ${productos_reales:,.2f}")
    if c_serv is not None and abs(r2(c_serv) - servicios_reales) > TOLERANCIA:
        problemas.append(f"Servicios: guardado ${c_serv:,.2f} vs detalle ${servicios_reales:,.2f}")
    if abs(servicios_subtotales - servicios_reales) > TOLERANCIA:
        problemas.append("Algún servicio adicional tiene un subtotal distinto de cantidad × precio")
    if abs(pagos_reales - r2(pagado)) > TOLERANCIA:
        problemas.append(f"Pagado guardado (${pagado:,.2f}) no coincide con la suma de pagos (${pagos_reales:,.2f})")
    if metodo == "Financiado" and cuotas[1] > 0:
        plan = r2(cuotas[0] + r2(inicial))
        if abs(plan - r2(monto_total)) > TOLERANCIA:
            problemas.append(f"Inicial + cuotas (${plan:,.2f}) no suman el total (${monto_total:,.2f})")
    if pagos_reales - r2(monto_total) > TOLERANCIA:
        problemas.append(f"Se ha cobrado más del total: pagado ${pagos_reales:,.2f}")

    return {
        "ok": not problemas,
        "desglose": desglose,
        "lineas": lineas_desglose(desglose, paquete, traslado),
        "total_guardado": r2(monto_total),
        "total_calculado": total_calculado,
        "pagado": pagos_reales,
        "saldo": r2(r2(monto_total) - pagos_reales),
        "problemas": problemas,
    }


class PrecioService:
    """Clase unificada para invocación estática de servicios de precio y verificación"""

    @staticmethod
    def calcular_desglose(paquete: str, requiere_cremacion: bool, tipo_traslado: str,
                          productos: List[Dict], servicios: List[Dict],
                          pnf_asociado: bool = False, pnf_cubre_traslado: bool = False,
                          pnf_cubre_cremacion: bool = False) -> Dict:
        return calcular_desglose(
            paquete=paquete,
            requiere_cremacion=requiere_cremacion,
            tipo_traslado=tipo_traslado,
            productos=productos,
            servicios=servicios,
            pnf_asociado=pnf_asociado,
            pnf_cubre_traslado=pnf_cubre_traslado,
            pnf_cubre_cremacion=pnf_cubre_cremacion
        )

    @staticmethod
    def verificar_contrato(contrato_id: int) -> Dict:
        return verificar_contrato(contrato_id)

    @staticmethod
    def generar_plan_cuotas(total: float, inicial: float, numero_cuotas: int,
                            fecha_base: Optional[datetime.date] = None,
                            frecuencia: str = "Mensual") -> List[Dict]:
        return generar_plan_cuotas(total, inicial, numero_cuotas, fecha_base, frecuencia)

    @staticmethod
    def calcular_cuotas_exactas(saldo: float, numero_cuotas: int,
                                frecuencia: str = "Mensual") -> List[float]:
        plan = generar_plan_cuotas(saldo, 0.0, numero_cuotas, frecuencia=frecuencia)
        return [c["monto"] for c in plan]


    @staticmethod
    def construir_verificacion_previa(desglose: Dict, paquete: str = "", tipo_traslado: str = "",
                                     metodo: str = "Contado", inicial: float = 0.0, cuotas: int = 1) -> Dict:
        lineas = lineas_desglose(desglose, paquete, tipo_traslado)
        tot = desglose.get("total", 0.0)
        sal = max(0.0, tot - inicial) if metodo == "Financiado" else 0.0
        return {
            "ok": True,
            "desglose": desglose,
            "lineas": lineas,
            "total_guardado": tot,
            "total_calculado": tot,
            "pagado": inicial if metodo == "Financiado" else tot,
            "saldo": sal,
            "problemas": []
        }

DesglosePrecio = Dict


