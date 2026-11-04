# services/pago_service.py - Gestión de pagos multimoneda y amortización de cuotas
import datetime
from typing import Optional, List, Dict
from services.db_service import obtener_conexion, ContratoRepository
from services.precio_service import r2


class PagoService:
    """Servicio para gestión de pagos con múltiples métodos y soporte multidivisa (USD / BS)"""

    MONEDAS = ["USD", "BS"]

    METODOS_PAGO = [
        "Efectivo (USD)",
        "Efectivo (BS)",
        "Punto de Venta (Tarjeta)",
        "Transferencia Bancaria",
        "Pago Móvil"
    ]

    @staticmethod
    def registrar_pago(contrato_id: int, monto: float, metodo: str,
                       referencia: str = "", moneda: str = "USD",
                       tasa_cambio: float = None, cuota_id: int = None,
                       usuario_id: int = 1, mes_periodo: str = None) -> Dict:
        """
        Registra un pago en USD o BS.
        - Si moneda == 'BS', 'monto' es en bolívares:
            monto_original = monto_bs
            monto (en pagos) = round(monto_bs / tasa_cambio, 2)  [USD que descuenta]
        - Si moneda == 'USD', monto_original = monto_usd = monto.

        Retorna un dict con los datos del pago registrado (incluye el id generado).
        """
        if monto <= 0:
            raise ValueError("El monto a pagar debe ser mayor a 0")

        # Métodos que exigen comprobante bancario
        if metodo in ["Transferencia Bancaria", "Pago Móvil"] and not (referencia or "").strip():
            raise ValueError(f"El método '{metodo}' requiere un número de referencia o comprobante")

        # Conversión de moneda
        monto_original = r2(monto)
        if moneda == "BS":
            tasa = tasa_cambio or PagoService.obtener_tasa_cambio_dia()
            if not tasa or tasa <= 0:
                raise ValueError("Tasa de cambio inválida para pago en Bolívares")
            monto_usd = r2(monto_original / tasa)
            tasa_usada = r2(tasa)
        else:
            moneda = "USD"
            monto_usd = monto_original
            tasa_usada = None

        if monto_usd <= 0:
            raise ValueError("El monto en USD resultante de la conversión debe ser mayor a cero")

        conn = obtener_conexion()
        cursor = conn.cursor()

        try:
            # Validar que el pago no exceda el saldo pendiente del contrato
            row_c = cursor.execute(
                "SELECT monto_total, pagado FROM contratos WHERE id = ?", (contrato_id,)
            ).fetchone()
            if not row_c:
                raise ValueError("Contrato no encontrado")

            total_contrato = r2(row_c[0])
            pagado_previo = r2(row_c[1])
            saldo_pendiente = r2(total_contrato - pagado_previo)

            if monto_usd > saldo_pendiente + 0.01:
                raise ValueError(
                    f"El pago (${monto_usd:,.2f} USD) excede el saldo pendiente (${saldo_pendiente:,.2f} USD)"
                )

            if cuota_id:
                fila_cuota = cursor.execute("""
                    SELECT monto, estado
                    FROM cuotas
                    WHERE id = ? AND contrato_id = ?
                """, (cuota_id, contrato_id)).fetchone()
                if not fila_cuota:
                    raise ValueError("La cuota no pertenece al contrato seleccionado")
                monto_cuota, estado_cuota = fila_cuota
                pagado_cuota = r2(cursor.execute(
                    "SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE cuota_id = ?",
                    (cuota_id,)
                ).fetchone()[0])
                saldo_cuota = max(0.0, r2(monto_cuota - pagado_cuota))
                if (estado_cuota or "").casefold() == "pagada" or saldo_cuota <= 0.01:
                    raise ValueError("La cuota seleccionada ya está pagada")
                if monto_usd > saldo_cuota + 0.01:
                    raise ValueError(
                        f"El pago (${monto_usd:,.2f} USD) excede el saldo de la cuota "
                        f"(${saldo_cuota:,.2f} USD)"
                    )

            # Si no se pasó mes_periodo pero sí cuota_id, averiguar la fecha_vencimiento de la cuota
            if cuota_id and not mes_periodo:
                row_cu = cursor.execute("SELECT numero, fecha_vencimiento FROM cuotas WHERE id = ?", (cuota_id,)).fetchone()
                if row_cu:
                    c_num, c_venc = row_cu
                    try:
                        dt = datetime.datetime.strptime(c_venc, "%Y-%m-%d")
                        meses_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                        mes_periodo = f"Cuota #{c_num} - {meses_es[dt.month]} {dt.year}"
                    except Exception:
                        mes_periodo = f"Cuota #{c_num} ({c_venc})"

            fecha_ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO pagos (
                    contrato_id, cuota_id, fecha, monto, metodo,
                    referencia, moneda, tasa_cambio, monto_original, mes_periodo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (contrato_id, cuota_id, fecha_ahora, monto_usd, metodo,
                  referencia.strip(), moneda, tasa_usada, monto_original, mes_periodo))

            pago_id = cursor.lastrowid

            # Recalcular el total pagado en el contrato (suma de montos en USD)
            cursor.execute("SELECT ROUND(SUM(monto), 2) FROM pagos WHERE contrato_id = ?", (contrato_id,))
            nuevo_pagado = cursor.fetchone()[0] or 0.0
            cursor.execute("UPDATE contratos SET pagado = ? WHERE id = ?", (nuevo_pagado, contrato_id))

            # Si se asoció a una cuota específica:
            if cuota_id:
                monto_cuota = r2(cursor.execute("SELECT monto FROM cuotas WHERE id = ?", (cuota_id,)).fetchone()[0])
                total_cuota = r2(cursor.execute(
                    "SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE cuota_id = ?", (cuota_id,)
                ).fetchone()[0])
                if total_cuota >= monto_cuota - 0.01:
                    cursor.execute("""
                        UPDATE cuotas SET estado = 'Pagada', fecha_pago = ? WHERE id = ?
                    """, (fecha_ahora, cuota_id))
            else:
                # Amortizar cuotas pendientes en orden si es financiado
                cursor.execute("""
                    SELECT id, monto, estado FROM cuotas
                    WHERE contrato_id = ? AND estado != 'Pagada'
                    ORDER BY numero
                """, (contrato_id,))
                cuotas_pendientes = cursor.fetchall()
                rem = monto_usd
                for cid, mc, est in cuotas_pendientes:
                    if rem <= 0:
                        break
                    # Cuánto ya tiene pagada esta cuota
                    pagado_cuota = r2(cursor.execute(
                        "SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE cuota_id = ?", (cid,)
                    ).fetchone()[0])
                    pendiente_cuota = r2(mc - pagado_cuota)
                    if rem >= pendiente_cuota - 0.01:
                        cursor.execute("""
                            UPDATE cuotas SET estado = 'Pagada', fecha_pago = ? WHERE id = ?
                        """, (fecha_ahora, cid))
                        rem = r2(rem - pendiente_cuota)

            conn.commit()

            detalles_bitacora = (
                f"Contrato ID {contrato_id}: Pago #{pago_id} por ${monto_usd:,.2f} USD "
                f"({monto_original:,.2f} {moneda}) via {metodo} (Ref: {referencia or 'N/A'})"
            )
            ContratoRepository.registrar_bitacora(usuario_id, "Registro de pago", detalles_bitacora)

            return {
                "id": pago_id,
                "contrato_id": contrato_id,
                "monto_usd": monto_usd,
                "monto_original": monto_original,
                "moneda": moneda,
                "tasa_cambio": tasa_usada,
                "metodo": metodo,
                "referencia": referencia,
                "fecha": fecha_ahora
            }
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def obtener_tasa_cambio_dia() -> float:
        """Obtiene la tasa de cambio del día (USD / BS)"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'tasa_cambio_usd_bs'")
        row = cursor.fetchone()
        if row and row[0]:
            try:
                tasa = float(row[0])
            except ValueError:
                tasa = 40.0
        else:
            tasa = 40.0
            cursor.execute("""
                INSERT OR REPLACE INTO configuracion (clave, valor, actualizado)
                VALUES ('tasa_cambio_usd_bs', '40.0', ?)
            """, (datetime.datetime.now().isoformat(),))
            conn.commit()
        conn.close()
        return tasa

    @staticmethod
    def actualizar_tasa_cambio(tasa: float) -> bool:
        """Actualiza la tasa de cambio del día"""
        if tasa <= 0:
            return False
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO configuracion (clave, valor, actualizado)
                VALUES ('tasa_cambio_usd_bs', ?, ?)
            """, (str(tasa), datetime.datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error actualizando tasa: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def obtener_pagos_contrato(contrato_id: int) -> List[Dict]:
        """Obtiene el historial completo de pagos de un contrato"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, fecha, monto, metodo, referencia, moneda, tasa_cambio, cuota_id, monto_original, mes_periodo
            FROM pagos
            WHERE contrato_id = ?
            ORDER BY fecha DESC, id DESC
        """, (contrato_id,))

        pagos = []
        for row in cursor.fetchall():
            pagos.append({
                'id': row[0],
                'fecha': row[1],
                'monto': row[2],
                'metodo': row[3],
                'referencia': row[4] or "",
                'moneda': row[5] or "USD",
                'tasa_cambio': row[6],
                'cuota_id': row[7],
                'monto_original': row[8] if row[8] is not None else row[2],
                'mes_periodo': row[9] or "Pago / Abono general"
            })
        conn.close()
        return pagos

    @staticmethod
    def obtener_cuotas_con_saldos(contrato_id: int) -> List[Dict]:
        """Obtiene el plan de cuotas con los abonos vinculados y saldo individual."""
        conn = obtener_conexion()
        try:
            filas = conn.execute("""
                SELECT cu.id, cu.numero, cu.monto, cu.fecha_vencimiento,
                       cu.fecha_pago, cu.estado,
                       COALESCE(SUM(p.monto), 0) AS pagado
                FROM cuotas cu
                LEFT JOIN pagos p ON p.cuota_id = cu.id
                WHERE cu.contrato_id = ?
                GROUP BY cu.id, cu.numero, cu.monto, cu.fecha_vencimiento,
                         cu.fecha_pago, cu.estado
                ORDER BY cu.numero
            """, (contrato_id,)).fetchall()
        finally:
            conn.close()

        cuotas = []
        hoy = datetime.date.today()
        for cuota_id, numero, monto, vencimiento, fecha_pago, estado, pagado in filas:
            monto = r2(monto)
            if (estado or "").casefold() == "pagada":
                pagado = monto
                saldo = 0.0
            else:
                pagado = min(monto, r2(pagado))
                saldo = max(0.0, r2(monto - pagado))
            if saldo <= 0.01:
                estado_mostrado = "Pagada"
                saldo = 0.0
            else:
                try:
                    vencimiento_fecha = datetime.datetime.strptime(
                        vencimiento, "%Y-%m-%d"
                    ).date()
                except (TypeError, ValueError):
                    vencimiento_fecha = None
                estado_mostrado = (
                    "Vencida" if vencimiento_fecha and vencimiento_fecha < hoy
                    else estado or "Pendiente"
                )
            cuotas.append({
                "id": cuota_id,
                "numero": numero,
                "monto": monto,
                "pagado": pagado,
                "saldo": saldo,
                "fecha_vencimiento": vencimiento,
                "fecha_pago": fecha_pago,
                "estado": estado_mostrado,
            })
        return cuotas

    @staticmethod
    def obtener_resumen_pagos_contrato(contrato_id: int) -> Dict:
        """Obtiene resumen de pagos por método y moneda"""
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT metodo, ROUND(SUM(monto), 2)
            FROM pagos
            WHERE contrato_id = ?
            GROUP BY metodo
        """, (contrato_id,))
        por_metodo = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT moneda, ROUND(SUM(monto), 2)
            FROM pagos
            WHERE contrato_id = ?
            GROUP BY moneda
        """, (contrato_id,))
        por_moneda = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        total = r2(sum(por_metodo.values()))
        return {
            'por_metodo': por_metodo,
            'por_moneda': por_moneda,
            'total': total
        }