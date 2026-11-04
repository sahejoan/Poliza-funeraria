"""Consultas y reglas de solvencia para contratos funerarios."""
import datetime
import unicodedata
from typing import Dict, List, Optional

from services.db_service import obtener_conexion
from services.precio_service import r2


class SolvenciaService:
    """Busca contratos y determina saldos, períodos pagados y cuotas vencidas."""

    @staticmethod
    def consultar(termino: str = "", limite: int = 500) -> List[Dict]:
        conn = obtener_conexion()
        conn.create_function("NORMALIZAR_TEXTO", 1, SolvenciaService._normalizar_texto)
        try:
            cursor = conn.cursor()
            filtro = (termino or "").strip()
            parametros = []
            condicion = ""
            if filtro:
                comodin = f"%{SolvenciaService._normalizar_texto(filtro)}%"
                cedula = filtro.upper().replace(".", "").replace("-", "").replace(" ", "")
                condicion = """
                    WHERE c.numero LIKE ? COLLATE NOCASE
                       OR NORMALIZAR_TEXTO(COALESCE(f.resp_nombre, '') || ' ' ||
                           COALESCE(f.resp_apellido, '')) LIKE ?
                       OR NORMALIZAR_TEXTO(COALESCE(f.resp_apellido, '') || ' ' ||
                           COALESCE(f.resp_nombre, '')) LIKE ?
                       OR NORMALIZAR_TEXTO(COALESCE(f.resp_nombre, '')) LIKE ?
                       OR NORMALIZAR_TEXTO(COALESCE(f.resp_apellido, '')) LIKE ?
                       OR REPLACE(REPLACE(REPLACE(UPPER(COALESCE(f.resp_cedula, '')),
                           '.', ''), '-', ''), ' ', '') LIKE ?
                       OR NORMALIZAR_TEXTO(COALESCE(d.nombre, '') || ' ' ||
                           COALESCE(d.apellido, '')) LIKE ?
                       OR NORMALIZAR_TEXTO(COALESCE(d.apellido, '') || ' ' ||
                           COALESCE(d.nombre, '')) LIKE ?
                       OR NORMALIZAR_TEXTO(COALESCE(d.nombre, '')) LIKE ?
                       OR NORMALIZAR_TEXTO(COALESCE(d.apellido, '')) LIKE ?
                       OR REPLACE(REPLACE(REPLACE(UPPER(COALESCE(d.cedula, '')),
                           '.', ''), '-', ''), ' ', '') LIKE ?
                """
                parametros = [
                    f"%{filtro}%", comodin, comodin, comodin, comodin, f"%{cedula}%",
                    comodin, comodin, comodin, comodin, f"%{cedula}%",
                ]

            filas = cursor.execute(f"""
                SELECT c.id, c.numero, c.fecha_contrato, COALESCE(c.estado, ''),
                       COALESCE(c.tipo_contrato, 'Inmediato'), COALESCE(c.monto_total, 0),
                       COALESCE(c.pagado, 0),
                       COALESCE(f.resp_nombre || ' ' || f.resp_apellido, 'Sin titular'),
                       COALESCE(f.resp_cedula, ''),
                       COALESCE(d.nombre || ' ' || d.apellido, 'No asignado'),
                       COALESCE(d.cedula, '')
                FROM contratos c
                LEFT JOIN familias f ON f.familia_id = c.familia_id
                LEFT JOIN difuntos d ON d.id = c.difunto_id
                {condicion}
                ORDER BY c.id DESC
                LIMIT ?
            """, (*parametros, max(1, int(limite)))).fetchall()

            detalles = SolvenciaService._obtener_detalles(cursor, [fila[0] for fila in filas])
        finally:
            conn.close()

        return [
            SolvenciaService._formatear_fila(fila, *detalles.get(fila[0], ([], [])))
            for fila in filas
        ]

    @staticmethod
    def _normalizar_texto(texto):
        return unicodedata.normalize("NFKD", str(texto or "")).encode(
            "ASCII", "ignore"
        ).decode("ASCII").casefold()

    @staticmethod
    def obtener_por_id(contrato_id: int) -> Optional[Dict]:
        conn = obtener_conexion()
        try:
            cursor = conn.cursor()
            fila = cursor.execute("""
                SELECT c.id, c.numero, c.fecha_contrato, COALESCE(c.estado, ''),
                       COALESCE(c.tipo_contrato, 'Inmediato'), COALESCE(c.monto_total, 0),
                       COALESCE(c.pagado, 0),
                       COALESCE(f.resp_nombre || ' ' || f.resp_apellido, 'Sin titular'),
                       COALESCE(f.resp_cedula, ''),
                       COALESCE(d.nombre || ' ' || d.apellido, 'No asignado'),
                       COALESCE(d.cedula, '')
                FROM contratos c
                LEFT JOIN familias f ON f.familia_id = c.familia_id
                LEFT JOIN difuntos d ON d.id = c.difunto_id
                WHERE c.id = ?
            """, (contrato_id,)).fetchone()
            if not fila:
                return None
            cuotas, pagos = SolvenciaService._obtener_detalles(cursor, [contrato_id])[contrato_id]
        finally:
            conn.close()
        return SolvenciaService._formatear_fila(fila, cuotas, pagos)

    @staticmethod
    def _obtener_detalles(cursor, contrato_ids):
        if not contrato_ids:
            return {}

        placeholders = ",".join("?" for _ in contrato_ids)
        cuotas = cursor.execute(f"""
            SELECT contrato_id, id, numero, monto, fecha_vencimiento, estado
            FROM cuotas
            WHERE contrato_id IN ({placeholders})
            ORDER BY contrato_id, numero
        """, contrato_ids).fetchall()
        pagos = cursor.execute(f"""
            SELECT contrato_id, id, cuota_id, fecha, monto, mes_periodo
            FROM pagos
            WHERE contrato_id IN ({placeholders})
            ORDER BY contrato_id, fecha, id
        """, contrato_ids).fetchall()

        detalles = {contrato_id: ([], []) for contrato_id in contrato_ids}
        for fila in cuotas:
            detalles[fila[0]][0].append(fila[1:])
        for fila in pagos:
            detalles[fila[0]][1].append(fila[1:])
        return detalles

    @staticmethod
    def _etiqueta_cuota(numero, vencimiento):
        try:
            fecha = datetime.datetime.strptime(vencimiento, "%Y-%m-%d")
        except (TypeError, ValueError):
            return f"Cuota #{numero} ({vencimiento or 'sin vencimiento'})"
        meses = (
            "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
        )
        return f"Cuota #{numero} - {meses[fecha.month]} {fecha.year}"

    @staticmethod
    def _formatear_fila(fila, cuotas=None, pagos=None) -> Dict:
        (contrato_id, numero, fecha, estado, tipo, total, pagado,
         titular, titular_cedula, difunto, difunto_cedula) = fila
        cuotas = cuotas or []
        pagos = pagos or []
        total = r2(total)
        pagado = r2(pagado)
        saldo = r2(total - pagado)
        estado_normalizado = estado.strip().casefold()
        cancelado = estado_normalizado in {"cancelado", "cancelada"}

        cuotas_saldo = {
            cuota_id: {
                "numero": cuota_numero,
                "monto": r2(monto),
                "vencimiento": vencimiento,
                "estado": (estado_cuota or "").casefold(),
                "restante": r2(monto),
                "fecha_pago": None,
            }
            for cuota_id, cuota_numero, monto, vencimiento, estado_cuota in cuotas
        }

        periodos_con_pagos = {}
        for pago_id, cuota_id, fecha_pago, monto, periodo in pagos:
            monto_restante = r2(monto)
            if periodo:
                periodo_limpio = periodo.strip()
                if periodo_limpio.casefold() not in {
                    "pago / abono general", "abono / pago general a saldo",
                }:
                    periodos_con_pagos[periodo_limpio] = r2(
                        periodos_con_pagos.get(periodo_limpio, 0) + monto_restante
                    )

            if cuota_id in cuotas_saldo:
                cuota = cuotas_saldo[cuota_id]
                cuota["restante"] = max(0.0, r2(cuota["restante"] - monto_restante))
                if cuota["restante"] <= 0.01 and cuota["fecha_pago"] is None:
                    cuota["fecha_pago"] = fecha_pago
                continue

            for cuota in cuotas_saldo.values():
                if monto_restante <= 0:
                    break
                if cuota["estado"] == "pagada" or cuota["restante"] <= 0.01:
                    cuota["restante"] = 0.0
                    continue
                aplicado = min(cuota["restante"], monto_restante)
                cuota["restante"] = r2(cuota["restante"] - aplicado)
                monto_restante = r2(monto_restante - aplicado)
                if cuota["restante"] <= 0.01 and cuota["fecha_pago"] is None:
                    cuota["fecha_pago"] = fecha_pago

        # Contratos históricos pueden tener pagos acumulados sin recibos asociados.
        saldo_sin_recibos = max(0.0, r2(pagado - sum(r2(p[3]) for p in pagos)))
        for cuota in cuotas_saldo.values():
            if saldo_sin_recibos <= 0:
                break
            if cuota["estado"] == "pagada" or cuota["restante"] <= 0.01:
                cuota["restante"] = 0.0
                continue
            aplicado = min(cuota["restante"], saldo_sin_recibos)
            cuota["restante"] = r2(cuota["restante"] - aplicado)
            saldo_sin_recibos = r2(saldo_sin_recibos - aplicado)

        cuotas_pendientes = []
        cuotas_vencidas = []
        hoy = datetime.date.today()
        for cuota in cuotas_saldo.values():
            if cuota["estado"] == "pagada":
                cuota["restante"] = 0.0
            if cuota["restante"] <= 0.01:
                continue
            etiqueta = SolvenciaService._etiqueta_cuota(
                cuota["numero"], cuota["vencimiento"]
            )
            cuotas_pendientes.append(
                f"{etiqueta} (${cuota['restante']:,.2f} pendiente)"
            )
            try:
                fecha_vencimiento = datetime.datetime.strptime(
                    cuota["vencimiento"], "%Y-%m-%d"
                ).date()
            except (TypeError, ValueError):
                continue
            if fecha_vencimiento < hoy:
                cuotas_vencidas.append({
                    "etiqueta": etiqueta,
                    "saldo": cuota["restante"],
                    "fecha_vencimiento": cuota["vencimiento"],
                })

        monto_vencido = r2(sum(cuota["saldo"] for cuota in cuotas_vencidas))
        solvente = not cancelado and saldo <= 0.01
        moroso = not cancelado and not solvente and monto_vencido > 0.01
        if cancelado:
            estado_solvencia = "CANCELADO"
        elif solvente:
            estado_solvencia = "SOLVENTE"
        elif moroso:
            estado_solvencia = "MOROSO"
        else:
            estado_solvencia = "PENDIENTE"

        return {
            "id": contrato_id,
            "numero": numero,
            "fecha_contrato": fecha or "",
            "estado_contrato": estado,
            "tipo_contrato": tipo,
            "monto_total": total,
            "pagado": pagado,
            "saldo_pendiente": 0.0 if saldo <= 0.01 else saldo,
            "titular": titular.strip(),
            "titular_cedula": titular_cedula,
            "difunto": difunto.strip(),
            "difunto_cedula": difunto_cedula,
            "solvente": solvente,
            "moroso": moroso,
            "estado_solvencia": estado_solvencia,
            "periodos_con_pagos": [
                {"periodo": periodo, "monto": monto}
                for periodo, monto in periodos_con_pagos.items()
            ],
            "cuotas_pendientes": cuotas_pendientes,
            "cuotas_vencidas": cuotas_vencidas,
            "monto_vencido": monto_vencido,
        }
