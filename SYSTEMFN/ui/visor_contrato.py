# ui/visor_contrato.py - Visor de contrato integrado con desglose y verificación
import os
import datetime
import customtkinter as ctk
from tkinter import ttk
import tkinter.messagebox as mb

from services.db_service import obtener_conexion, PAQUETES, EMPRESA
from services.contrato_service import ContratoService
from services.precio_service import verificar_contrato, lineas_desglose, r2
from utils.helpers import centrar_ventana, formatear_moneda, mostrar_dialogo_verificar_total, COLOR_GOLD


class VisorContrato(ctk.CTkToplevel):
    """Ventana para visualizar el contrato en el sistema con desglose y verificación de costos"""

    def __init__(self, parent, contrato_id: int):
        super().__init__(parent)
        self.parent = parent
        self.contrato_id = contrato_id
        self.title("Visor de Contrato - Memoriales Altagracia")
        self.geometry("900x950")
        self.resizable(True, True)
        self.grab_set()

        centrar_ventana(self, 900, 950)
        self.cargar_datos()
        self.crear_interfaz()

    def cargar_datos(self):
        """Carga todos los datos del contrato mediante ContratoService"""
        self.contrato = ContratoService.obtener_contrato_completo(self.contrato_id)
        if not self.contrato:
            return

        conn = obtener_conexion()
        cursor = conn.cursor()

        # Productos adicionales
        cursor.execute("""
            SELECT i.nombre, cp.cantidad, cp.precio_unitario
            FROM contrato_productos cp
            JOIN inventario i ON cp.producto_id = i.id
            WHERE cp.contrato_id = ?
        """, (self.contrato_id,))
        self.productos = cursor.fetchall()

        # Servicios adicionales
        cursor.execute("""
            SELECT servicio_nombre, cantidad, precio_unitario, subtotal
            FROM contratos_servicios
            WHERE contrato_id = ?
        """, (self.contrato_id,))
        self.servicios = cursor.fetchall()

        # Cuotas
        cursor.execute("""
            SELECT numero, monto, fecha_vencimiento, estado, fecha_pago
            FROM cuotas WHERE contrato_id = ? ORDER BY numero
        """, (self.contrato_id,))
        self.cuotas = cursor.fetchall()

        conn.close()

    def crear_interfaz(self):
        if not self.contrato:
            ctk.CTkLabel(self, text="Error: No se encontraron datos del contrato",
                         font=("Segoe UI", 16), text_color="red").pack(expand=True)
            return

        main_frame = ctk.CTkScrollableFrame(self, fg_color="#FFFFFF")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Encabezado corporativo
        header_frame = ctk.CTkFrame(main_frame, fg_color="#1A1A2E", corner_radius=10)
        header_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(header_frame, text="🏛️", font=("Segoe UI", 36), text_color=COLOR_GOLD).pack(pady=(10, 0))
        ctk.CTkLabel(header_frame, text=EMPRESA["nombre"],
                     font=("Segoe UI", 16, "bold"), text_color=COLOR_GOLD).pack()
        ctk.CTkLabel(header_frame, text=f"RIF: {EMPRESA['rif']}",
                     font=("Segoe UI", 11), text_color="#BDC3C7").pack()
        ctk.CTkLabel(header_frame, text=EMPRESA["direccion"],
                     font=("Segoe UI", 10), text_color="#BDC3C7").pack()
        ctk.CTkLabel(header_frame, text=f"Tel: {EMPRESA['telefono']} | Email: {EMPRESA['correo']}",
                     font=("Segoe UI", 10), text_color="#BDC3C7").pack(pady=(0, 10))

        # Título y tipo de contrato
        tipo_badge = f"[{self.contrato['tipo_contrato'].upper()}]"
        ctk.CTkLabel(main_frame, text=f"CONTRATO DE SERVICIO FUNERARIO {tipo_badge}",
                     font=("Segoe UI", 20, "bold"), text_color="#1A1A2E").pack(pady=5)

        from utils.helpers import formatear_fecha_ddmmyyyy

        sub_info = (f"N° {self.contrato['numero']}  ·  Fecha: {formatear_fecha_ddmmyyyy(self.contrato['fecha_contrato'])}  ·  "
                    f"Estado: {self.contrato['estado']}")
        ctk.CTkLabel(main_frame, text=sub_info, font=("Segoe UI", 12), text_color="#666666").pack(pady=3)

        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=10)

        # 1. Datos del fallecido / afiliado
        if self.contrato['tipo_contrato'] == "Largo Plazo" and not self.contrato['difunto_id']:
            datos_dif = [
                ("Modalidad:", "Plan a Largo Plazo (Previsión Funeraria)"),
                ("Beneficiario:", "Por designar al activar el plan"),
                ("Titular:", self.contrato['responsable'])
            ]
        else:
            datos_dif = [
                ("Nombre completo:", self.contrato['difunto']),
                ("Cédula de identidad:", self.contrato['difunto_cedula']),
                ("Fecha de defunción:", formatear_fecha_ddmmyyyy(self.contrato['difunto_defuncion']) if self.contrato['difunto_defuncion'] else "No especificada")
            ]
        self._crear_seccion(main_frame, "1. DATOS DEL FALLECIDO / AFILIADO", datos_dif)

        # 2. Familiar Responsable
        tit_datos = [
            ("Nombre completo:", self.contrato['responsable']),
            ("Cédula de identidad:", self.contrato['responsable_cedula']),
        ]
        if self.contrato.get('titular_edad'):
            tit_datos.append(("Edad del titular:", f"{self.contrato['titular_edad']} años (Mayor de edad)"))
        tit_datos.extend([
            ("Teléfono:", self.contrato['responsable_telefono'] or "—"),
            ("Correo electrónico:", self.contrato['responsable_email'] or "—"),
            ("Dirección:", self.contrato['responsable_direccion'] or "—")
        ])
        self._crear_seccion(main_frame, "2. FAMILIAR RESPONSABLE / TITULAR", tit_datos)

        num_sec = 3
        # Beneficiarios PNF si existen
        if self.contrato.get('beneficiarios'):
            b_frame = ctk.CTkFrame(main_frame, fg_color="#F4F4F4", corner_radius=10)
            b_frame.pack(fill="x", pady=8)
            ctk.CTkLabel(b_frame, text=f"{num_sec}. BENEFICIARIOS A SU CARGO (PNF - {len(self.contrato['beneficiarios'])} PERSONAS)",
                         font=("Segoe UI", 13, "bold"), text_color=COLOR_GOLD).pack(anchor="w", padx=15, pady=(8, 4))
            b_list_frame = ctk.CTkFrame(b_frame, fg_color="transparent")
            b_list_frame.pack(fill="x", padx=15, pady=4)
            for idx, b in enumerate(self.contrato['beneficiarios'], 1):
                doc_str = f"C.I: {b.get('cedula')}" if b.get('tipo_documento') == "Cedula" else f"Partida (Folio: {b.get('folio')}, Acta: {b.get('acta')})"
                fnac_fmt = formatear_fecha_ddmmyyyy(b.get('fecha_nacimiento'))
                line = f"{idx}. {b.get('nombre_completo')}  |  {doc_str}  |  F.Nac: {fnac_fmt}  |  Edad: {b.get('edad')} años"
                ctk.CTkLabel(b_list_frame, text=line, font=("Segoe UI", 10), anchor="w").pack(anchor="w", pady=1)
            num_sec += 1

        # 3. Cobertura PNF (si aplica)
        if self.contrato['pnf_asociado']:
            self._crear_seccion(main_frame, f"{num_sec}. AFILIACIÓN A PLAN NACIONAL FUNERARIO (PNF)", [
                ("Afiliación PNF:", "Sí (Plan Nacional Funerario asociado)"),
                ("N° Contrato / Póliza:", self.contrato['pnf_numero'] or "No especificado"),
                ("Cubre Cremación:", "Sí (sin recargo adicional)" if self.contrato['pnf_cubre_cremacion'] else "No cubierta"),
                ("Cubre Traslado:", f"Sí (cobertura {self.contrato['tipo_traslado']})" if self.contrato['pnf_cubre_traslado'] else "No cubierto"),
                ("Descuento total PNF:", f"${self.contrato['descuento_pnf']:,.2f}")
            ])
            num_sec += 1


        # 4. Detalle del servicio
        paquete = PAQUETES.get(self.contrato['paquete'], {})
        incluye = "  •  ".join(paquete.get("incluye", ["Servicio básico"]))

        datos_serv = [
            ("Tipo de contrato:", self.contrato['tipo_contrato']),
            ("Paquete:", f"{self.contrato['paquete']}  —  ${paquete.get('precio', 0):,.2f}"),
            ("Descripción:", paquete.get("descripcion", "")),
            ("Incluye:", incluye),
            ("Tipo de velación:", self.contrato['tipo_velacion']),
            ("Capilla asignada:", self.contrato['capilla']),
            ("Cremación:", "Sí" if self.contrato['requiere_cremacion'] else "No"),
            ("Tipo de traslado:", self.contrato['tipo_traslado'])
        ]
        if self.contrato['tipo_contrato'] == "Inmediato" or self.contrato['fecha_velacion']:
            datos_serv.append(("Fecha de velación:", formatear_fecha_ddmmyyyy(self.contrato['fecha_velacion'])))
            datos_serv.append(("Horario planificado:", f"{self.contrato['hora_inicio']} a {self.contrato['hora_fin']}"))
        else:
            datos_serv.append(("Fecha y horario:", "Se asignarán al momento de activar el plan"))

        self._crear_seccion(main_frame, f"{num_sec}. DETALLE DEL SERVICIO CONTRATADO", datos_serv)
        num_sec += 1

        # 5. Horarios reales
        if self.contrato['hora_llegada_real'] or self.contrato['hora_salida_capilla']:
            llegada_txt = self.contrato['hora_llegada_real']
            if self.contrato['fecha_llegada_real']:
                llegada_txt = f"{self.contrato['fecha_llegada_real']} {llegada_txt}"
            self._crear_seccion(main_frame, f"{num_sec}. HORARIOS REALES DEL SERVICIO", [
                ("Hora real de llegada del cuerpo:", llegada_txt or "No registrada"),
                ("Hora de salida de capilla:", self.contrato['hora_salida_capilla'] or "No registrada")
            ])
            num_sec += 1

        # 6. Productos adicionales
        if self.productos:
            frame = ctk.CTkFrame(main_frame, fg_color="#F4F4F4", corner_radius=10)
            frame.pack(fill="x", pady=8)
            ctk.CTkLabel(frame, text=f"{num_sec}. PRODUCTOS ADICIONALES",
                         font=("Segoe UI", 13, "bold"), text_color=COLOR_GOLD).pack(anchor="w", padx=15, pady=(8, 4))
            prod_frame = ctk.CTkFrame(frame, fg_color="transparent")
            prod_frame.pack(fill="x", padx=15, pady=4)

            ctk.CTkLabel(prod_frame, text="Producto", font=("Segoe UI", 10, "bold"), width=280, anchor="w").grid(row=0, column=0, padx=5, pady=2)
            ctk.CTkLabel(prod_frame, text="Cant.", font=("Segoe UI", 10, "bold"), width=60, anchor="center").grid(row=0, column=1, padx=5, pady=2)
            ctk.CTkLabel(prod_frame, text="Precio Unit.", font=("Segoe UI", 10, "bold"), width=100, anchor="center").grid(row=0, column=2, padx=5, pady=2)
            ctk.CTkLabel(prod_frame, text="Subtotal", font=("Segoe UI", 10, "bold"), width=100, anchor="center").grid(row=0, column=3, padx=5, pady=2)

            for i, p in enumerate(self.productos, 1):
                sub = p[1] * p[2]
                ctk.CTkLabel(prod_frame, text=p[0], width=280, anchor="w", text_color="#333333").grid(row=i, column=0, padx=5, pady=2)
                ctk.CTkLabel(prod_frame, text=str(p[1]), width=60, anchor="center", text_color="#333333").grid(row=i, column=1, padx=5, pady=2)
                ctk.CTkLabel(prod_frame, text=f"${p[2]:,.2f}", width=100, anchor="center", text_color="#333333").grid(row=i, column=2, padx=5, pady=2)
                ctk.CTkLabel(prod_frame, text=f"${sub:,.2f}", width=100, anchor="center", text_color="#333333").grid(row=i, column=3, padx=5, pady=2)
            num_sec += 1

        # 7. Servicios adicionales
        if self.servicios:
            frame = ctk.CTkFrame(main_frame, fg_color="#F4F4F4", corner_radius=10)
            frame.pack(fill="x", pady=8)
            ctk.CTkLabel(frame, text=f"{num_sec}. SERVICIOS ADICIONALES",
                         font=("Segoe UI", 13, "bold"), text_color=COLOR_GOLD).pack(anchor="w", padx=15, pady=(8, 4))
            serv_frame = ctk.CTkFrame(frame, fg_color="transparent")
            serv_frame.pack(fill="x", padx=15, pady=4)

            ctk.CTkLabel(serv_frame, text="Servicio", font=("Segoe UI", 10, "bold"), width=280, anchor="w").grid(row=0, column=0, padx=5, pady=2)
            ctk.CTkLabel(serv_frame, text="Cant.", font=("Segoe UI", 10, "bold"), width=60, anchor="center").grid(row=0, column=1, padx=5, pady=2)
            ctk.CTkLabel(serv_frame, text="Precio Unit.", font=("Segoe UI", 10, "bold"), width=100, anchor="center").grid(row=0, column=2, padx=5, pady=2)
            ctk.CTkLabel(serv_frame, text="Subtotal", font=("Segoe UI", 10, "bold"), width=100, anchor="center").grid(row=0, column=3, padx=5, pady=2)

            for i, s in enumerate(self.servicios, 1):
                ctk.CTkLabel(serv_frame, text=s[0], width=280, anchor="w", text_color="#333333").grid(row=i, column=0, padx=5, pady=2)
                ctk.CTkLabel(serv_frame, text=str(s[1]), width=60, anchor="center", text_color="#333333").grid(row=i, column=1, padx=5, pady=2)
                ctk.CTkLabel(serv_frame, text=f"${s[2]:,.2f}", width=100, anchor="center", text_color="#333333").grid(row=i, column=2, padx=5, pady=2)
                ctk.CTkLabel(serv_frame, text=f"${s[3]:,.2f}", width=100, anchor="center", text_color="#333333").grid(row=i, column=3, padx=5, pady=2)
            num_sec += 1

        # 8. Desglose y Resumen Financiero
        saldo = r2(self.contrato['monto_total'] - self.contrato['pagado'])
        datos_fin = []
        if self.contrato.get('costo_paquete') is not None:
            d_dict = {
                "costo_paquete": self.contrato['costo_paquete'],
                "costo_cremacion": self.contrato['costo_cremacion'],
                "costo_traslado": self.contrato['costo_traslado'],
                "costo_productos": self.contrato['costo_productos'],
                "costo_servicios": self.contrato['costo_servicios'],
                "descuento_pnf": self.contrato['descuento_pnf']
            }
            for concepto, monto in lineas_desglose(d_dict, self.contrato['paquete'], self.contrato['tipo_traslado']):
                prefix = "- " if monto < 0 else ""
                datos_fin.append((f"{concepto}:", f"{prefix}${abs(monto):,.2f}"))

        datos_fin.append(("TOTAL DEL CONTRATO:", f"${self.contrato['monto_total']:,.2f}"))
        datos_fin.append(("Modalidad de pago:", self.contrato['metodo_pago']))

        if self.contrato['metodo_pago'] == "Financiado":
            datos_fin.append(("Inicial pactada:", f"${self.contrato['inicial']:,.2f}"))
            datos_fin.append(("Número de cuotas:", str(len(self.cuotas) if self.cuotas else self.contrato['numero_cuotas'])))

        datos_fin.append(("Total pagado a la fecha:", f"${self.contrato['pagado']:,.2f}"))
        datos_fin.append(("Saldo pendiente:", f"${saldo:,.2f}"))

        self._crear_seccion(main_frame, f"{num_sec}. DESGLOSE Y RESUMEN FINANCIERO", datos_fin)
        num_sec += 1

        # 9. Plan de Cuotas
        if self.cuotas and self.contrato['metodo_pago'] == "Financiado":
            frame = ctk.CTkFrame(main_frame, fg_color="#F4F4F4", corner_radius=10)
            frame.pack(fill="x", pady=8)
            ctk.CTkLabel(frame, text=f"{num_sec}. PLAN DE PAGOS (CUOTAS)",
                         font=("Segoe UI", 13, "bold"), text_color=COLOR_GOLD).pack(anchor="w", padx=15, pady=(8, 4))

            cuota_frame = ctk.CTkFrame(frame, fg_color="transparent")
            cuota_frame.pack(fill="x", padx=15, pady=4)

            ctk.CTkLabel(cuota_frame, text="N°", font=("Segoe UI", 10, "bold"), width=50, anchor="center").grid(row=0, column=0, padx=5, pady=2)
            ctk.CTkLabel(cuota_frame, text="Monto", font=("Segoe UI", 10, "bold"), width=100, anchor="center").grid(row=0, column=1, padx=5, pady=2)
            ctk.CTkLabel(cuota_frame, text="Vencimiento", font=("Segoe UI", 10, "bold"), width=120, anchor="center").grid(row=0, column=2, padx=5, pady=2)
            ctk.CTkLabel(cuota_frame, text="Estado", font=("Segoe UI", 10, "bold"), width=100, anchor="center").grid(row=0, column=3, padx=5, pady=2)

            for i, cu in enumerate(self.cuotas, 1):
                color_estado = "#27AE60" if cu[3] == "Pagada" else "#E74C3C"
                ctk.CTkLabel(cuota_frame, text=str(cu[0]), width=50, anchor="center", text_color="#333333").grid(row=i, column=0, padx=5, pady=2)
                ctk.CTkLabel(cuota_frame, text=f"${cu[1]:,.2f}", width=100, anchor="center", text_color="#333333").grid(row=i, column=1, padx=5, pady=2)
                ctk.CTkLabel(cuota_frame, text=formatear_fecha_ddmmyyyy(cu[2]), width=120, anchor="center", text_color="#333333").grid(row=i, column=2, padx=5, pady=2)
                ctk.CTkLabel(cuota_frame, text=cu[3], width=100, anchor="center", text_color=color_estado).grid(row=i, column=3, padx=5, pady=2)
            num_sec += 1

        # Observaciones
        if self.contrato['observaciones'] and self.contrato['observaciones'].strip():
            self._crear_seccion(main_frame, "OBSERVACIONES", [("", self.contrato['observaciones'])])

        # Cláusulas y firmas
        clausula = (
            "El presente contrato tiene carácter vinculante entre SERVICIOS MEMORIALES ALTAGRACIA C.A. "
            "y el Familiar Responsable identificado en la Sección 2. Los servicios serán prestados conforme "
            "a los términos acordados."
        )
        frame_cl = ctk.CTkFrame(main_frame, fg_color="#F4F4F4", corner_radius=10)
        frame_cl.pack(fill="x", pady=8)
        ctk.CTkLabel(frame_cl, text="CLÁUSULAS", font=("Segoe UI", 12, "bold"), text_color=COLOR_GOLD).pack(anchor="w", padx=15, pady=(6, 2))
        ctk.CTkLabel(frame_cl, text=clausula, font=("Segoe UI", 9), wraplength=800, justify="left", text_color="#555555").pack(anchor="w", padx=15, pady=4)

        # Botonera de acciones
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15)

        ctk.CTkButton(btn_frame, text="🔍 Verificar Total y Costo", command=self.verificar_total_click,
                     fg_color=COLOR_GOLD, text_color="black", height=38, width=200,
                     font=("Segoe UI", 12, "bold")).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="📄 Generar / Ver PDF", command=self.generar_pdf_click,
                     fg_color="#3498DB", text_color="white", height=38, width=170).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="📋 Copiar Resumen", command=self.copiar,
                     fg_color="#2ECC71", text_color="black", height=38, width=150).pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="❌ Cerrar", command=self.destroy,
                     fg_color="#E74C3C", text_color="white", height=38, width=100).pack(side="right", padx=5)

    def _crear_seccion(self, parent, titulo, datos):
        frame = ctk.CTkFrame(parent, fg_color="#F4F4F4", corner_radius=10)
        frame.pack(fill="x", pady=8)

        ctk.CTkLabel(frame, text=titulo, font=("Segoe UI", 13, "bold"), text_color=COLOR_GOLD).pack(anchor="w", padx=15, pady=(8, 4))

        for label, valor in datos:
            row_frame = ctk.CTkFrame(frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=15, pady=2)
            if label:
                ctk.CTkLabel(row_frame, text=label, font=("Segoe UI", 11, "bold"),
                             width=220, anchor="w", text_color="#333333").pack(side="left")
                ctk.CTkLabel(row_frame, text=str(valor), font=("Segoe UI", 11),
                             anchor="w", text_color="#555555", wraplength=580).pack(side="left", padx=10)
            else:
                ctk.CTkLabel(row_frame, text=str(valor), font=("Segoe UI", 11),
                             anchor="w", text_color="#555555", wraplength=800).pack(padx=10)

    def verificar_total_click(self):
        """Ejecuta la auditoría matemática del contrato y muestra el reporte"""
        verificacion = verificar_contrato(self.contrato_id)
        mostrar_dialogo_verificar_total(self, verificacion)

    def generar_pdf_click(self):
        """Genera el PDF del contrato y lo abre con el visor predeterminado"""
        from services.pdf_service import generar_pdf_contrato
        ruta = generar_pdf_contrato(self.contrato_id)
        if ruta and os.path.exists(ruta):
            mb.showinfo("PDF Generado", f"El contrato PDF se generó exitosamente en:\n{ruta}")
            try:
                os.startfile(ruta)
            except Exception:
                pass
        else:
            mb.showerror("Error", "No se pudo generar el archivo PDF.")

    def copiar(self):
        texto = f"""SERVICIOS MEMORIALES ALTAGRACIA C.A.
CONTRATO N°: {self.contrato['numero']} ({self.contrato['tipo_contrato']})
Fecha: {self.contrato['fecha_contrato']}
Titular / Responsable: {self.contrato['responsable']} (C.I. {self.contrato['responsable_cedula']})
Difunto: {self.contrato['difunto']}
Paquete: {self.contrato['paquete']}
Monto Total: ${self.contrato['monto_total']:,.2f}
Pagado: ${self.contrato['pagado']:,.2f}
Saldo Pendiente: ${r2(self.contrato['monto_total'] - self.contrato['pagado']):,.2f}
"""
        self.clipboard_clear()
        self.clipboard_append(texto)
        mb.showinfo("Copiado", "Resumen del contrato copiado al portapapeles.")