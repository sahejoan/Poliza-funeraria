# services/reporte_service.py - Generación de reportes y estadísticas avanzados
import sqlite3
import datetime
from typing import List, Dict, Optional, Tuple
from services.db_service import EMPRESA, obtener_conexion

class ReporteService:
    """Servicio para generación de reportes del sistema"""
    
    @staticmethod
    def ventas_por_periodo(fecha_inicio: str, fecha_fin: str) -> Dict:
        """Reporte de ventas en un período de fechas (acepta DD/MM/AAAA o YYYY-MM-DD)"""
        from utils.helpers import normalizar_fecha_iso
        fecha_inicio_iso = normalizar_fecha_iso(fecha_inicio)
        fecha_fin_iso = normalizar_fecha_iso(fecha_fin)
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Ventas totales del período
        cursor.execute("""
            SELECT COALESCE(SUM(p.monto), 0)
            FROM pagos p
            WHERE DATE(p.fecha) BETWEEN ? AND ?
        """, (fecha_inicio_iso, fecha_fin_iso))
        total_ventas = cursor.fetchone()[0] or 0.0
        
        # Cantidad de contratos
        cursor.execute("""
            SELECT COUNT(*)
            FROM contratos
            WHERE DATE(fecha_contrato) BETWEEN ? AND ?
        """, (fecha_inicio_iso, fecha_fin_iso))
        cantidad_contratos = cursor.fetchone()[0] or 0
        
        # Ingresos por paquete
        cursor.execute("""
            SELECT c.paquete, COUNT(*) as cantidad, SUM(c.monto_total) as total
            FROM contratos c
            WHERE DATE(c.fecha_contrato) BETWEEN ? AND ?
            GROUP BY c.paquete
        """, (fecha_inicio_iso, fecha_fin_iso))
        ingresos_por_paquete = [{
            'paquete': row[0],
            'cantidad': row[1],
            'total': row[2] or 0.0
        } for row in cursor.fetchall()]
        
        # Ingresos por método de pago
        cursor.execute("""
            SELECT p.metodo, COALESCE(SUM(p.monto), 0)
            FROM pagos p
            WHERE DATE(p.fecha) BETWEEN ? AND ?
            GROUP BY p.metodo
            ORDER BY SUM(p.monto) DESC
        """, (fecha_inicio_iso, fecha_fin_iso))
        ingresos_por_metodo = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Ingresos por moneda (USD/BS)
        cursor.execute("""
            SELECT COALESCE(SUM(CASE WHEN moneda = 'USD' THEN monto ELSE 0 END), 0) as usd,
                   COALESCE(SUM(CASE WHEN moneda = 'BS' THEN monto ELSE 0 END), 0) as bs
            FROM pagos p
            WHERE DATE(p.fecha) BETWEEN ? AND ?
        """, (fecha_inicio_iso, fecha_fin_iso))
        moneda_row = cursor.fetchone()
        
        conn.close()
        
        promedio = total_ventas / cantidad_contratos if cantidad_contratos > 0 else 0
        
        return {
            'total_ventas': total_ventas,
            'cantidad_contratos': cantidad_contratos,
            'promedio_por_contrato': promedio,
            'ingresos_por_paquete': ingresos_por_paquete,
            'ingresos_por_metodo': ingresos_por_metodo,
            'ingresos_usd': moneda_row[0] if moneda_row else 0,
            'ingresos_bs': moneda_row[1] if moneda_row else 0
        }
    
    @staticmethod
    def cuotas_vencidas() -> List[Dict]:
        """Reporte de cuotas vencidas con más detalles"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        hoy = datetime.datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT c.id as contrato_id,
                   c.numero as contrato_numero,
                   c.fecha_contrato,
                   cu.id as cuota_id,
                   cu.numero as cuota_numero,
                   cu.monto,
                   cu.fecha_vencimiento,
                   COALESCE(f.resp_nombre || ' ' || f.resp_apellido, 'Sin titular') as responsable,
                   COALESCE(f.resp_telefono, '—') as telefono,
                   COALESCE(d.nombre || ' ' || d.apellido, 'Plan a Futuro') as difunto
            FROM cuotas cu
            JOIN contratos c ON cu.contrato_id = c.id
            LEFT JOIN familias f ON c.familia_id = f.familia_id
            LEFT JOIN difuntos d ON c.difunto_id = d.id
            WHERE cu.estado = 'Pendiente' 
              AND cu.fecha_vencimiento < ?
            ORDER BY cu.fecha_vencimiento ASC
        """, (hoy,))
        
        resultados = []
        for row in cursor.fetchall():
            dias_atraso = (datetime.datetime.now() - datetime.datetime.strptime(row[6], "%Y-%m-%d")).days
            resultados.append({
                'contrato_id': row[0],
                'contrato_numero': row[1],
                'fecha_contrato': row[2],
                'cuota_id': row[3],
                'cuota_numero': row[4],
                'monto': row[5],
                'fecha_vencimiento': row[6],
                'responsable': row[7],
                'telefono': row[8],
                'difunto': row[9],
                'dias_atraso': dias_atraso
            })
        
        conn.close()
        return resultados
    
    @staticmethod
    def productos_mas_vendidos(limite: int = 10) -> List[Dict]:
        """Reporte de productos más vendidos"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT i.nombre,
                   SUM(cp.cantidad) as total_vendidos,
                   SUM(cp.cantidad * cp.precio_unitario) as total_ingresos
            FROM contrato_productos cp
            JOIN inventario i ON cp.producto_id = i.id
            GROUP BY cp.producto_id
            ORDER BY total_vendidos DESC
            LIMIT ?
        """, (limite,))
        
        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'producto': row[0],
                'cantidad_vendida': row[1],
                'ingresos': row[2] or 0.0
            })
        
        conn.close()
        return resultados
    
    @staticmethod
    def servicios_adicionales_mas_solicitados(limite: int = 10) -> List[Dict]:
        """Reporte de servicios adicionales más solicitados"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cs.servicio_nombre,
                   cs.tipo_velacion,
                   COUNT(*) as veces_solicitado,
                   SUM(cs.cantidad) as total_unidades,
                   SUM(cs.subtotal) as total_ingresos
            FROM contratos_servicios cs
            GROUP BY cs.servicio_key
            ORDER BY veces_solicitado DESC
            LIMIT ?
        """, (limite,))
        
        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'servicio': row[0],
                'tipo_velacion': row[1],
                'veces_solicitado': row[2],
                'total_unidades': row[3],
                'ingresos': row[4] or 0.0
            })
        
        conn.close()
        return resultados
    
    @staticmethod
    def ingresos_mensuales(anio: int = None) -> List[Dict]:
        """Reporte de ingresos por mes del año"""
        if anio is None:
            anio = datetime.datetime.now().year
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT strftime('%m', p.fecha) as mes,
                   COALESCE(SUM(p.monto), 0) as total
            FROM pagos p
            WHERE strftime('%Y', p.fecha) = ?
            GROUP BY strftime('%m', p.fecha)
            ORDER BY mes
        """, (str(anio),))
        
        resultados = []
        meses_nombres = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
                         7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}
        
        for row in cursor.fetchall():
            mes_num = int(row[0])
            resultados.append({
                'mes_numero': mes_num,
                'mes_nombre': meses_nombres.get(mes_num, ''),
                'total': row[1]
            })
        
        conn.close()
        return resultados
    
    @staticmethod
    def top_clientes(limite: int = 10) -> List[Dict]:
        """Top clientes (responsables) que más han gastado"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.resp_nombre || ' ' || f.resp_apellido as responsable,
                   f.resp_cedula,
                   f.resp_telefono,
                   COUNT(c.id) as cantidad_contratos,
                   SUM(c.monto_total) as total_gastado,
                   SUM(c.pagado) as total_pagado,
                   SUM(c.monto_total - c.pagado) as saldo_pendiente
            FROM familias f
            JOIN contratos c ON f.familia_id = c.familia_id
            GROUP BY f.familia_id
            ORDER BY total_gastado DESC
            LIMIT ?
        """, (limite,))
        
        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'responsable': row[0],
                'cedula': row[1],
                'telefono': row[2] or "—",
                'cantidad_contratos': row[3],
                'total_gastado': row[4] or 0.0,
                'total_pagado': row[5] or 0.0,
                'saldo_pendiente': row[6] or 0.0
            })
        
        conn.close()
        return resultados
    
    @staticmethod
    def ocupacion_capillas() -> List[Dict]:
        """Reporte de ocupación de capillas en los próximos 30 días"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        hoy = datetime.datetime.now().strftime("%Y-%m-%d")
        futuro = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT cap.nombre as capilla,
                   cap.capacidad,
                   COUNT(c.id) as contratos_proximos,
                   GROUP_CONCAT(c.fecha_velacion || ' (' || c.hora_inicio || ') - ' || 
                               d.nombre || ' ' || d.apellido) as detalles
            FROM capillas cap
            LEFT JOIN contratos c ON cap.id = c.capilla_id 
                AND c.estado = 'Activo'
                AND c.fecha_velacion BETWEEN ? AND ?
            LEFT JOIN difuntos d ON c.difunto_id = d.id
            GROUP BY cap.id
        """, (hoy, futuro))
        
        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'capilla': row[0],
                'capacidad': row[1],
                'contratos_proximos': row[2] or 0,
                'detalles': row[3] or "Sin contratos programados"
            })
        
        conn.close()
        return resultados
    
    @staticmethod
    def resumen_general() -> Dict:
        """Resumen general del sistema"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Total familias
        cursor.execute("SELECT COUNT(*) FROM familias WHERE activo = 1")
        total_familias = cursor.fetchone()[0] or 0
        
        # Total difuntos
        cursor.execute("SELECT COUNT(*) FROM difuntos")
        total_difuntos = cursor.fetchone()[0] or 0
        
        # Total contratos por estado
        cursor.execute("""
            SELECT estado, COUNT(*), SUM(monto_total), SUM(pagado)
            FROM contratos
            GROUP BY estado
        """)
        contratos_por_estado = {}
        for row in cursor.fetchall():
            contratos_por_estado[row[0]] = {
                'cantidad': row[1],
                'monto_total': row[2] or 0,
                'monto_pagado': row[3] or 0,
                'monto_pendiente': (row[2] or 0) - (row[3] or 0)
            }
        
        # Total productos en inventario
        cursor.execute("SELECT COUNT(*), SUM(stock), SUM(stock * precio) FROM inventario")
        inv_row = cursor.fetchone()
        total_productos = inv_row[0] or 0
        total_stock = inv_row[1] or 0
        valor_inventario = inv_row[2] or 0
        
        # Capillas disponibles
        cursor.execute("SELECT COUNT(*) FROM capillas WHERE estado = 'Disponible'")
        capillas_disponibles = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM capillas")
        total_capillas = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_familias': total_familias,
            'total_difuntos': total_difuntos,
            'contratos_por_estado': contratos_por_estado,
            'total_productos': total_productos,
            'total_stock': total_stock,
            'valor_inventario': valor_inventario,
            'capillas_disponibles': capillas_disponibles,
            'total_capillas': total_capillas
        }
    
    @staticmethod
    def exportar_a_excel(datos: List[Dict], nombre_archivo: str) -> str:
        """Exporta un reporte a Excel con encabezado corporativo y formato de impresión."""
        try:
            import pandas as pd
            import os
            from openpyxl.styles import Alignment, Font, PatternFill
            from openpyxl.utils import get_column_letter
            from openpyxl.worksheet.page import PageMargins
            
            df = pd.DataFrame(datos)
            os.makedirs("reportes", exist_ok=True)
            ruta = f"reportes/{nombre_archivo}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(ruta, index=False, engine="openpyxl", startrow=5)

            from openpyxl import load_workbook
            workbook = load_workbook(ruta)
            worksheet = workbook.active
            column_count = max(1, len(df.columns))
            last_column = get_column_letter(column_count)

            encabezado = [
                EMPRESA["nombre"],
                f"RIF: {EMPRESA['rif']}",
                EMPRESA["direccion"],
                f"Tel: {EMPRESA['telefono']} · {EMPRESA['correo']}",
            ]
            for row_number, texto in enumerate(encabezado, start=1):
                if column_count > 1:
                    worksheet.merge_cells(
                        start_row=row_number, start_column=1,
                        end_row=row_number, end_column=column_count,
                    )
                celda = worksheet.cell(row=row_number, column=1, value=texto)
                celda.alignment = Alignment(
                    horizontal="center" if row_number == 1 else "left",
                    vertical="center",
                )
                celda.font = Font(
                    name="Arial", size=15 if row_number == 1 else 9,
                    bold=row_number == 1, color="333333",
                )
                worksheet.row_dimensions[row_number].height = 25 if row_number == 1 else 16

            for celda in worksheet[6]:
                celda.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
                celda.fill = PatternFill(fill_type="solid", fgColor="16213E")
                celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            worksheet.row_dimensions[6].height = 25
            for row in worksheet.iter_rows(min_row=7):
                for celda in row:
                    celda.font = Font(name="Arial", size=10, color="222222")
                    celda.alignment = Alignment(vertical="top", wrap_text=True)
            for column_index in range(1, column_count + 1):
                letter = get_column_letter(column_index)
                longest = max(
                    (len(str(worksheet.cell(row=row_index, column=column_index).value or ""))
                     for row_index in range(6, worksheet.max_row + 1)),
                    default=12,
                )
                worksheet.column_dimensions[letter].width = min(max(longest + 2, 14), 42)

            worksheet.freeze_panes = "A7"
            if df.columns.size:
                worksheet.auto_filter.ref = f"A6:{last_column}{max(6, worksheet.max_row)}"
            worksheet.sheet_properties.pageSetUpPr.fitToPage = True
            worksheet.page_setup.orientation = "landscape"
            worksheet.page_setup.fitToWidth = 1
            worksheet.page_setup.fitToHeight = 0
            worksheet.print_title_rows = "1:6"
            worksheet.page_margins = PageMargins(
                left=0.25, right=0.25, top=0.5, bottom=0.5,
                header=0.2, footer=0.2,
            )
            workbook.save(ruta)
            return ruta
        except ImportError:
            return None
        except Exception as e:
            print(f"Error exportando: {e}")
            return None

    @staticmethod
    def exportar_a_pdf(titulo: str, columnas: List[str], filas: List[List], nombre_archivo: str) -> Optional[str]:
        """Exporta un reporte tabular a formato PDF profesional usando ReportLab"""
        try:
            from xml.sax.saxutils import escape
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.lib import colors as rc
            import os

            os.makedirs("reportes", exist_ok=True)
            ruta = f"reportes/{nombre_archivo}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            doc = SimpleDocTemplate(
                ruta,
                pagesize=landscape(letter),
                leftMargin=36,
                rightMargin=36,
                topMargin=105,
                bottomMargin=36
            )
            ancho_tabla = landscape(letter)[0] - doc.leftMargin - doc.rightMargin
            
            story = []
            s_tit = ParagraphStyle(
                "Tit", fontName="Helvetica-Bold", fontSize=16, leading=21,
                textColor=rc.HexColor("#1A1A2E"), alignment=TA_CENTER,
            )
            s_sub = ParagraphStyle(
                "Sub", fontName="Helvetica", fontSize=9, leading=13,
                textColor=rc.HexColor("#555555"), alignment=TA_CENTER,
            )
            s_head = ParagraphStyle(
                "Head", fontName="Helvetica-Bold", fontSize=9, leading=12,
                textColor=rc.white, alignment=TA_CENTER,
            )
            s_cel = ParagraphStyle(
                "Cel", fontName="Helvetica", fontSize=8, leading=11,
                textColor=rc.HexColor("#222222"),
            )
            
            story.extend([
                Paragraph(
                    escape(f"REPORTE OFICIAL: {titulo.upper()} — Generado: "
                           f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"),
                    s_sub,
                ),
                Spacer(1, 10),
            ])
            
            cantidad_columnas = max(1, len(columnas))
            anchos_columnas = [ancho_tabla / cantidad_columnas] * cantidad_columnas
            tabla_data = [[Paragraph(escape(str(c)), s_head) for c in columnas]]
            for f in filas:
                celdas = [Paragraph(escape(str(val)), s_cel) for val in f]
                if len(celdas) < cantidad_columnas:
                    celdas.extend([Paragraph("", s_cel)] * (cantidad_columnas - len(celdas)))
                tabla_data.append(celdas[:cantidad_columnas])
            
            t = Table(
                tabla_data, colWidths=anchos_columnas,
                repeatRows=1, hAlign="LEFT",
            )
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), rc.HexColor("#16213E")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, rc.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rc.white, rc.HexColor("#F8FAFC")])
            ]))
            story.append(t)
            
            def dibujar_encabezado(canvas, documento):
                ancho_pagina, alto_pagina = documento.pagesize
                canvas.saveState()
                canvas.setFillColor(rc.HexColor("#333333"))
                canvas.setFont("Helvetica-Bold", 15)
                canvas.drawCentredString(ancho_pagina / 2, alto_pagina - 30, EMPRESA["nombre"])
                canvas.setFont("Helvetica", 8)
                canvas.drawString(doc.leftMargin, alto_pagina - 52, f"RIF: {EMPRESA['rif']}")
                canvas.drawString(doc.leftMargin, alto_pagina - 64, EMPRESA["direccion"])
                canvas.drawString(
                    doc.leftMargin, alto_pagina - 76,
                    f"Tel: {EMPRESA['telefono']} · {EMPRESA['correo']}",
                )
                canvas.restoreState()

            doc.build(
                story,
                onFirstPage=dibujar_encabezado,
                onLaterPages=dibujar_encabezado,
            )
            return ruta
        except Exception as e:
            print(f"Error generando PDF de reporte: {e}")
            return None
            print(f"Error exportando: {e}")
            return None