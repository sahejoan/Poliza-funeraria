# services/contrato_service.py - Validaciones de disponibilidad y gestión de contratos
from datetime import datetime
from typing import Optional, Tuple, List, Dict
import random

from services.db_service import obtener_conexion, ContratoRepository, CapillaRepository
from models import EstadoServicio


class ContratoService:
    """Servicio para validaciones de contratos, disponibilidad y gestión de horarios"""

    @staticmethod
    def validar_disponibilidad_capilla(capilla_id: int, fecha: str, hora_inicio: str, hora_fin: str,
                                       contrato_excluir_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Verifica si una capilla está disponible en la fecha y horario solicitados.
        Retorna: (disponible, mensaje)
        """
        if not capilla_id:
            return False, "Debe seleccionar una capilla válida"

        # Verificar estado general de la capilla
        capilla = CapillaRepository.obtener_por_id(capilla_id)
        if not capilla or not capilla.get("activo"):
            return False, "La capilla seleccionada no existe o está inactiva"
        if capilla.get("estado") == "Mantenimiento":
            return False, f"La capilla '{capilla['nombre']}' se encuentra en mantenimiento"

        from utils.helpers import normalizar_fecha_iso, formatear_fecha_ddmmyyyy
        fecha_iso = normalizar_fecha_iso(fecha)
        fecha_dd = formatear_fecha_ddmmyyyy(fecha)

        conn = obtener_conexion()
        cursor = conn.cursor()

        query = """
            SELECT c.id, c.hora_inicio, c.hora_fin, c.numero
            FROM contratos c
            WHERE c.capilla_id = ?
              AND (c.fecha_velacion = ? OR c.fecha_velacion = ? OR c.fecha_velacion = ?)
              AND c.estado = 'Activo'
              AND c.id != ?
        """
        params = [capilla_id, fecha, fecha_iso, fecha_dd, contrato_excluir_id or -1]
        cursor.execute(query, params)
        contratos_existentes = cursor.fetchall()
        conn.close()

        def hora_a_minutos(hora_str):
            try:
                partes = str(hora_str).split(':')
                return int(partes[0]) * 60 + int(partes[1])
            except Exception:
                return 0

        inicio_nuevo = hora_a_minutos(hora_inicio)
        fin_nuevo = hora_a_minutos(hora_fin)

        if fin_nuevo <= inicio_nuevo:
            return False, "La hora de fin debe ser posterior a la hora de inicio"

        for contrato in contratos_existentes:
            inicio_existente = hora_a_minutos(contrato[1])
            fin_existente = hora_a_minutos(contrato[2])
            # Verificar solapamiento
            if not (fin_nuevo <= inicio_existente or inicio_nuevo >= fin_existente):
                return False, f"La capilla ya está ocupada por el contrato {contrato[3]} ({contrato[1]} - {contrato[2]})"

        return True, "Capilla disponible"

    @staticmethod
    def generar_numero_contrato() -> str:
        """Genera un número único de contrato asegurando que no exista en la BD"""
        ahora = datetime.now()
        año = ahora.year
        mes = ahora.month
        dia = ahora.day
        conn = obtener_conexion()
        cursor = conn.cursor()
        while True:
            random_num = random.randint(1000, 9999)
            num = f"CT-{año}{mes:02d}{dia:02d}-{random_num}"
            if not cursor.execute("SELECT 1 FROM contratos WHERE numero = ?", (num,)).fetchone():
                conn.close()
                return num

    @staticmethod
    def obtener_contrato_completo(contrato_id: int) -> Optional[dict]:
        """Obtiene todos los datos de un contrato para mostrar en visor, edición o PDF (usa LEFT JOIN)"""
        conn = obtener_conexion()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.id, c.numero, c.fecha_contrato, c.fecha_velacion,
                   c.hora_inicio, c.hora_fin, c.hora_llegada_real, c.hora_salida_capilla,
                   c.monto_total, c.pagado, c.metodo_pago, c.estado,
                   c.requiere_cremacion, c.tipo_traslado, c.estado_servicio, c.tipo_velacion, c.paquete,
                   d.nombre, d.apellido, d.cedula, d.fecha_defuncion,
                   f.resp_nombre, f.resp_apellido, f.resp_cedula, f.resp_telefono, f.resp_email, f.resp_direccion,
                   cap.nombre as capilla_nombre, c.observaciones,
                   c.tipo_contrato, c.fecha_llegada_real,
                   c.pnf_asociado, c.pnf_numero, c.pnf_cubre_traslado, c.pnf_cubre_cremacion,
                   c.costo_paquete, c.costo_cremacion, c.costo_traslado, c.costo_productos, c.costo_servicios,
                   c.descuento_pnf, c.fecha_activacion, c.pdf_ruta,
                   c.familia_id, c.difunto_id, c.capilla_id, c.inicial, c.numero_cuotas,
                   c.titular_edad, c.frecuencia_pago
            FROM contratos c
            LEFT JOIN difuntos d ON c.difunto_id = d.id
            JOIN familias f ON c.familia_id = f.familia_id
            LEFT JOIN capillas cap ON c.capilla_id = cap.id
            WHERE c.id = ?
        """, (contrato_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        beneficiarios = ContratoRepository.obtener_beneficiarios(contrato_id)

        difunto_nombre = f"{row[17]} {row[18]}".strip() if row[17] else "(Sin difunto asignado - Plan a Largo Plazo)"
        difunto_cedula = row[19] or "N/A"

        return {
            'id': row[0],
            'numero': row[1],
            'fecha_contrato': row[2],
            'fecha_velacion': row[3] or "",
            'hora_inicio': row[4] or "",
            'hora_fin': row[5] or "",
            'hora_llegada_real': row[6] or "",
            'hora_salida_capilla': row[7] or "",
            'monto_total': row[8],
            'pagado': row[9],
            'metodo_pago': row[10],
            'estado': row[11],
            'requiere_cremacion': bool(row[12]),
            'tipo_traslado': row[13] or "Local",
            'estado_servicio': row[14],
            'tipo_velacion': row[15] or "Funeraria",
            'paquete': row[16],
            'difunto': difunto_nombre,
            'difunto_cedula': difunto_cedula,
            'difunto_defuncion': row[20] or "",
            'responsable': f"{row[21]} {row[22]}",
            'responsable_cedula': row[23],
            'responsable_telefono': row[24] or "",
            'responsable_email': row[25] or "",
            'responsable_direccion': row[26] or "",
            'capilla': row[27] or "(Por asignar)",
            'observaciones': row[28] or "",
            'tipo_contrato': row[29] or "Inmediato",
            'fecha_llegada_real': row[30] or "",
            'pnf_asociado': bool(row[31]),
            'pnf_numero': row[32] or "",
            'pnf_cubre_traslado': bool(row[33]),
            'pnf_cubre_cremacion': bool(row[34]),
            'costo_paquete': row[35],
            'costo_cremacion': row[36],
            'costo_traslado': row[37],
            'costo_productos': row[38],
            'costo_servicios': row[39],
            'descuento_pnf': row[40] or 0.0,
            'fecha_activacion': row[41] or "",
            'pdf_ruta': row[42] or "",
            'familia_id': row[43],
            'difunto_id': row[44],
            'capilla_id': row[45],
            'inicial': row[46] or 0.0,
            'numero_cuotas': row[47] or 1,
            'titular_edad': row[48],
            'frecuencia_pago': row[49] or "Mensual",
            'beneficiarios': beneficiarios
        }

    @staticmethod
    def actualizar_horarios_llegada(contrato_id: int, hora_llegada: str, hora_salida: str,
                                    estado_servicio: Optional[str] = None,
                                    fecha_llegada: Optional[str] = None, usuario_id: int = 1) -> Tuple[bool, str]:
        """Actualiza la hora de llegada del difunto y hora de salida de capilla con validaciones"""
        import re
        patron = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
        hl = hora_llegada.strip() if hora_llegada else ""
        hs = hora_salida.strip() if hora_salida else ""

        if hl and not patron.match(hl):
            return False, "La hora de llegada debe tener formato HH:MM (ej. 14:30)"
        if hs and not patron.match(hs):
            return False, "La hora de salida debe tener formato HH:MM (ej. 18:00)"

        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE contratos
                SET hora_llegada_real = ?, hora_salida_capilla = ?,
                    fecha_llegada_real = COALESCE(?, fecha_llegada_real),
                    estado_servicio = COALESCE(?, estado_servicio)
                WHERE id = ?
            """, (hl or None, hs or None, fecha_llegada or None, estado_servicio or None, contrato_id))
            conn.commit()

            ContratoRepository.registrar_bitacora(
                usuario_id, "Modificación de horario de llegada",
                f"Contrato ID {contrato_id}: Llegada={hl or 'N/E'}, Salida={hs or 'N/E'}, Estado={estado_servicio or 'Sin cambio'}"
            )
            return True, "Horario actualizado correctamente"
        except Exception as e:
            conn.rollback()
            return False, f"Error en base de datos: {str(e)}"
        finally:
            conn.close()

    @staticmethod
    def reasignar_capilla(contrato_id: int, nueva_capilla_id: int, usuario_id: int = 1) -> Tuple[bool, str]:
        """Permite cambiar la capilla asignada a un contrato verificando disponibilidad"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT capilla_id, fecha_velacion, hora_inicio, hora_fin, estado FROM contratos WHERE id = ?", (contrato_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "Contrato no encontrado"

        capilla_anterior, fecha_vel, hora_ini, hora_fin, estado = row
        if estado != 'Activo':
            conn.close()
            return False, "Solo se puede reasignar capilla en contratos activos"

        # Validar disponibilidad de la nueva capilla
        disponible, msg = ContratoService.validar_disponibilidad_capilla(
            nueva_capilla_id, fecha_vel, hora_ini, hora_fin, contrato_excluir_id=contrato_id
        )
        if not disponible:
            conn.close()
            return False, msg

        try:
            cursor.execute("UPDATE contratos SET capilla_id = ? WHERE id = ?", (nueva_capilla_id, contrato_id))
            cursor.execute("UPDATE capillas SET estado = 'Ocupada' WHERE id = ?", (nueva_capilla_id,))
            if capilla_anterior and capilla_anterior != nueva_capilla_id:
                # Comprobar si la capilla anterior tiene otros contratos activos hoy
                otros = cursor.execute("""
                    SELECT COUNT(*) FROM contratos WHERE capilla_id = ? AND estado = 'Activo' AND id != ?
                """, (capilla_anterior, contrato_id)).fetchone()[0]
                if otros == 0:
                    cursor.execute("UPDATE capillas SET estado = 'Disponible' WHERE id = ?", (capilla_anterior,))

            conn.commit()
            ContratoRepository.registrar_bitacora(
                usuario_id, "Reasignación de capilla",
                f"Contrato ID {contrato_id}: Capilla {capilla_anterior} -> {nueva_capilla_id}"
            )
            return True, "Capilla reasignada con éxito"
        except Exception as e:
            conn.rollback()
            return False, f"Error reasignando: {str(e)}"
        finally:
            conn.close()

    @staticmethod
    def activar_plan_largo_plazo(contrato_id: int, difunto_id: int, capilla_id: int,
                                 fecha_velacion: str, hora_inicio: str, hora_fin: str,
                                 usuario_id: int = 1) -> Tuple[bool, str]:
        """Activa un contrato que estaba a Largo Plazo asignándole difunto, capilla y horario"""
        disponible, msg = ContratoService.validar_disponibilidad_capilla(
            capilla_id, fecha_velacion, hora_inicio, hora_fin, contrato_excluir_id=contrato_id
        )
        if not disponible:
            return False, msg

        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                UPDATE contratos
                SET difunto_id = ?, capilla_id = ?, fecha_velacion = ?, hora_inicio = ?, hora_fin = ?,
                    fecha_activacion = ?, estado_servicio = 'En capilla'
                WHERE id = ?
            """, (difunto_id, capilla_id, fecha_velacion, hora_inicio, hora_fin, ahora, contrato_id))

            cursor.execute("UPDATE capillas SET estado = 'Ocupada' WHERE id = ?", (capilla_id,))
            conn.commit()

            ContratoRepository.registrar_bitacora(
                usuario_id, "Activación de Plan Largo Plazo",
                f"Contrato ID {contrato_id} activado para difunto ID {difunto_id} en capilla {capilla_id}"
            )
            return True, "Plan activado correctamente. La capilla ha sido asignada."
        except Exception as e:
            conn.rollback()
            return False, f"Error activando plan: {str(e)}"
        finally:
            conn.close()

    @staticmethod
    def actualizar_estado_servicio(contrato_id: int, nuevo_estado: str) -> bool:
        """Actualiza el estado del servicio (Pendiente, En capilla, Cremación, Finalizado)"""
        estados_validos = [e.value for e in EstadoServicio]
        if nuevo_estado not in estados_validos:
            return False

        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE contratos SET estado_servicio = ? WHERE id = ?", (nuevo_estado, contrato_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error actualizando estado: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def obtener_cuotas_pendientes(contrato_id: int) -> List[Tuple]:
        """Obtiene las cuotas pendientes de un contrato"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, numero, monto, fecha_vencimiento
            FROM cuotas
            WHERE contrato_id = ? AND estado = 'Pendiente'
            ORDER BY numero
        """, (contrato_id,))
        cuotas = cursor.fetchall()
        conn.close()
        return cuotas