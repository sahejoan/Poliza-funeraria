# ui/pagos_frame.py - Gestión de pagos con múltiples métodos y finalización de servicios
import customtkinter as ctk
import tkinter.messagebox as mb
from tkinter import ttk
import datetime
from services.db_service import obtener_conexion, ContratoRepository
from services.contrato_service import ContratoService
from services.pago_service import PagoService
from utils.helpers import formatear_fecha_ddmmyyyy, parsear_decimal_monetario

class PagosFrame(ctk.CTkFrame):
    """Módulo de pagos con múltiples métodos de pago y finalización de servicios"""
    
    # Paleta de colores armonizada con el tema del sistema (soporte Claro y Oscuro)
    C_BG = "transparent"
    C_CARD = ("#FFFFFF", "#1A1E26")
    C_GOLD = "#D4AF37"
    C_GREEN = "#2ECC71"
    C_RED = "#E74C3C"
    C_GRAY = ("#64748B", "#9DA3AE")
    C_NAVY = ("#E2E8F0", "#262D3A")
    C_HEADER = ("#F8FAFC", "#12151B")
    
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.contrato_dict = {}
        self.contrato_id_actual = None
        self.crear_interfaz()
        self.cargar_contratos()
    
    def crear_interfaz(self):
        self.configure(fg_color=self.C_BG)
        
        # Encabezado
        hdr = ctk.CTkFrame(self, fg_color=self.C_CARD, corner_radius=0, height=70)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="💰 Gestión de Pagos y Facturación",
                     font=("Segoe UI", 24, "bold"), text_color=self.C_GOLD).pack(side="left", padx=24, pady=14)
        
        # Barra de selección de contrato
        sel = ctk.CTkFrame(self, fg_color=self.C_CARD, corner_radius=10)
        sel.pack(fill="x", padx=20, pady=(14, 6))
        ctk.CTkLabel(sel, text="Contrato:", font=("Segoe UI", 12, "bold"),
                     text_color=self.C_GOLD).pack(side="left", padx=(16, 6), pady=10)
        self.contrato_om = ctk.CTkOptionMenu(
            sel, width=500, font=("Segoe UI", 11),
            fg_color=self.C_NAVY, button_color=self.C_GOLD,
            button_hover_color="#F0D060", text_color=("#0F172A", "white"),
            dropdown_fg_color=self.C_NAVY, dropdown_text_color=("#0F172A", "white"),
            command=self.cargar_detalle
        )
        self.contrato_om.pack(side="left", padx=6, pady=10)
        ctk.CTkButton(sel, text="↻ Actualizar", width=110, height=32,
                      font=("Segoe UI", 11), fg_color=self.C_NAVY,
                      hover_color=self.C_GOLD, text_color=("#0F172A", "white"),
                      command=self.cargar_contratos).pack(side="left", padx=6)
        
        # Configuración de tasa de cambio
        tasa_frame = ctk.CTkFrame(sel, fg_color="transparent")
        tasa_frame.pack(side="right", padx=10)
        ctk.CTkLabel(tasa_frame, text="Tasa USD/BS:", font=("Segoe UI", 10)).pack(side="left")
        self.tasa_entry = ctk.CTkEntry(tasa_frame, width=80)
        self.tasa_entry.pack(side="left", padx=5)
        ctk.CTkButton(tasa_frame, text="Actualizar", width=80, height=28,
                     command=self.actualizar_tasa_cambio,
                     fg_color=self.C_NAVY, text_color=("#0F172A", "white")).pack(side="left")
        self.cargar_tasa_cambio()
        
        # KPI cards
        kpi_row = ctk.CTkFrame(self, fg_color="transparent")
        kpi_row.pack(fill="x", padx=20, pady=6)
        self.kpi_total = self._crear_kpi(kpi_row, "Total Contrato", "$0.00", ("#EBF5FB", "#1C2836"), ("#1E3A8A", "white"))
        self.kpi_pagado = self._crear_kpi(kpi_row, "Total Pagado", "$0.00", ("#E8F8F0", "#143625"), ("#065F46", "white"))
        self.kpi_saldo = self._crear_kpi(kpi_row, "Saldo Pendiente", "$0.00", ("#FDEDEC", "#38191D"), ("#991B1B", "white"))
        self.kpi_cuotas = self._crear_kpi(kpi_row, "Estado Cuotas", "—", ("#F1F5F9", "#262D3A"), ("#334155", "white"))
        
        # Área scrollable
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=self.C_BG, corner_radius=0)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))
    
    def _crear_kpi(self, parent, label, valor, color_bg, color_txt=("black", "white")):
        card = ctk.CTkFrame(parent, fg_color=color_bg, corner_radius=12, width=170, height=72)
        card.pack(side="left", padx=6, pady=4)
        card.pack_propagate(False)
        ctk.CTkLabel(card, text=label, font=("Segoe UI", 10), text_color=("#64748B", "#BDC3C7")).pack(pady=(8, 0))
        lbl = ctk.CTkLabel(card, text=valor, font=("Segoe UI", 18, "bold"), text_color=color_txt)
        lbl.pack()
        return lbl
    
    def cargar_tasa_cambio(self):
        tasa = PagoService.obtener_tasa_cambio_dia()
        self.tasa_entry.delete(0, "end")
        self.tasa_entry.insert(0, str(tasa))
    
    def actualizar_tasa_cambio(self):
        try:
            tasa = float(self.tasa_entry.get())
            if tasa <= 0:
                raise ValueError
            PagoService.actualizar_tasa_cambio(tasa)
            mb.showinfo("Éxito", f"Tasa de cambio actualizada: 1 USD = {tasa:.2f} BS")
        except ValueError:
            mb.showerror("Error", "Ingrese una tasa de cambio válida (número positivo)")
    
    def cargar_contratos(self):
        contratos = ContratoRepository.listar_contratos_activos()
        
        self.contrato_dict = {}
        opciones = []
        for c in contratos:
            texto = f"{c[1]}  —  {c[2]}  (${c[3]:,.2f} pendiente)"
            self.contrato_dict[texto] = c[0]
            opciones.append(texto)
        
        if opciones:
            self.contrato_om.configure(values=opciones)
            self.contrato_om.set(opciones[0])
            self.cargar_detalle(opciones[0])
        else:
            self.contrato_om.configure(values=["Sin contratos activos"])
            self.contrato_om.set("Sin contratos activos")
    
    def cargar_detalle(self, seleccion):
        if seleccion not in self.contrato_dict:
            return
        cid = self.contrato_dict[seleccion]
        self.contrato_id_actual = cid
        
        # Limpiar scroll
        for w in self.scroll.winfo_children():
            w.destroy()
        
        # Obtener datos del contrato
        contrato_data = ContratoService.obtener_contrato_completo(cid)
        if not contrato_data:
            return
        
        # Obtener capilla_id para liberar después
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT capilla_id FROM contratos WHERE id = ?", (cid,))
        capilla_row = cursor.fetchone()
        capilla_id = capilla_row[0] if capilla_row else None
        conn.close()
        
        # Actualizar KPIs
        total = contrato_data['monto_total']
        pagado = contrato_data['pagado']
        saldo = total - pagado
        self.kpi_total.configure(text=f"${total:,.2f}")
        self.kpi_pagado.configure(text=f"${pagado:,.2f}")
        self.kpi_saldo.configure(text=f"${saldo:,.2f}")
        
        # ========== SECCIÓN: NUEVO PAGO ==========
        self.crear_seccion_nuevo_pago(cid, saldo)
        
        # ========== SECCIÓN: EDITAR HORARIOS ==========
        self.crear_seccion_editar_horarios(contrato_data, cid, capilla_id)
        
        # ========== SECCIÓN: INFORMACIÓN DEL CONTRATO ==========
        self.crear_seccion_informacion(contrato_data)
        
        # ========== SECCIÓN: PLAN DE CUOTAS ==========
        if contrato_data['metodo_pago'] == "Financiado":
            self.mostrar_cuotas(cid)
        
        # ========== SECCIÓN: HISTORIAL DE PAGOS (CON DETALLE) ==========
        self.mostrar_historial_pagos(cid)
    
    def crear_seccion_nuevo_pago(self, contrato_id, saldo_disponible):
        pago_frame = ctk.CTkFrame(self.scroll, fg_color=self.C_CARD, corner_radius=10)
        pago_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(pago_frame, text="💵 REGISTRAR NUEVO PAGO", 
                    font=("Segoe UI", 14, "bold"), text_color=self.C_GOLD).pack(anchor="w", padx=15, pady=(10,5))
        
        monto_frame = ctk.CTkFrame(pago_frame, fg_color="transparent")
        monto_frame.pack(fill="x", padx=15, pady=5)

        # Mes / Período que cancela
        cuotas_db = PagoService.obtener_cuotas_con_saldos(contrato_id)

        meses_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        self.meses_dict = {}
        opciones_mes = []
        cuotas_pendientes = [cu for cu in cuotas_db if cu["saldo"] > 0.01]

        for cu in cuotas_pendientes:
            cid = cu["id"]
            num = cu["numero"]
            saldo_cuota = cu["saldo"]
            vcto = cu["fecha_vencimiento"]
            try:
                dt = datetime.datetime.strptime(vcto, "%Y-%m-%d")
                txt = (
                    f"Cuota #{num} - {meses_es[dt.month]} {dt.year} "
                    f"(${saldo_cuota:,.2f} pendiente)"
                )
            except Exception:
                txt = f"Cuota #{num} ({vcto}) - ${saldo_cuota:,.2f} pendiente"
            self.meses_dict[txt] = {
                "cuota_id": cid, "monto": saldo_cuota, "concepto": txt,
            }
            opciones_mes.append(txt)

        hoy = datetime.datetime.now()
        mes_actual_txt = f"Mes Actual: {meses_es[hoy.month]} {hoy.year}"
        self.meses_dict[mes_actual_txt] = {"cuota_id": None, "monto": None, "concepto": mes_actual_txt}
        opciones_mes.append(mes_actual_txt)

        # Meses del año actual y próximo para facturación mensual directa (PNF)
        for anio in (hoy.year, hoy.year + 1):
            for m in range(1, 13):
                m_txt = f"Mes: {meses_es[m]} {anio}"
                if m_txt not in self.meses_dict:
                    self.meses_dict[m_txt] = {"cuota_id": None, "monto": None, "concepto": m_txt}
                    opciones_mes.append(m_txt)

        opc_abono = "Abono / Pago General a Saldo"
        self.meses_dict[opc_abono] = {"cuota_id": None, "monto": None, "concepto": opc_abono}
        opciones_mes.append(opc_abono)

        periodo_frame = ctk.CTkFrame(pago_frame, fg_color="transparent")
        periodo_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(periodo_frame, text="Mes que se saca / Paga:*", width=180, anchor="w", font=("Segoe UI", 11, "bold")).pack(side="left")
        self.mes_combo = ctk.CTkComboBox(periodo_frame, values=opciones_mes, width=340, state="normal", command=self.on_mes_seleccionado)
        self.mes_combo.set(opciones_mes[0])
        self.mes_combo.pack(side="left", padx=10)

        ctk.CTkLabel(monto_frame, text="Monto a pagar:", width=150, anchor="w").pack(side="left")
        self.monto_entry = ctk.CTkEntry(monto_frame, width=150)
        self.monto_entry.pack(side="left", padx=10)
        if cuotas_pendientes:
            self.monto_entry.insert(0, f"{cuotas_pendientes[0]['saldo']:.2f}")
        ctk.CTkLabel(monto_frame, text=f"(Saldo pendiente: ${saldo_disponible:,.2f})", 
                    font=("Segoe UI", 10), text_color=self.C_GRAY).pack(side="left", padx=10)
        
        metodo_frame = ctk.CTkFrame(pago_frame, fg_color="transparent")
        metodo_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(metodo_frame, text="Método de pago:", width=150, anchor="w").pack(side="left")
        self.metodo_combo = ctk.CTkComboBox(metodo_frame, values=PagoService.METODOS_PAGO, width=200, state="readonly")
        self.metodo_combo.set("Efectivo (USD)")
        self.metodo_combo.pack(side="left", padx=10)
        self.metodo_combo.bind("<<ComboboxSelected>>", self.on_metodo_cambiado)
        
        moneda_frame = ctk.CTkFrame(pago_frame, fg_color="transparent")
        moneda_frame.pack(fill="x", padx=15, pady=5)
        self.moneda_label = ctk.CTkLabel(moneda_frame, text="Moneda:", width=150, anchor="w")
        self.moneda_label.pack(side="left")
        self.moneda_combo = ctk.CTkComboBox(moneda_frame, values=["USD", "BS"], width=100, state="readonly")
        self.moneda_combo.set("USD")
        self.moneda_combo.pack(side="left", padx=10)
        self.moneda_combo.bind("<<ComboboxSelected>>", self.on_moneda_cambiado)
        
        self.tasa_info_label = ctk.CTkLabel(moneda_frame, text="", font=("Segoe UI", 10))
        self.tasa_info_label.pack(side="left", padx=10)
        
        ref_frame = ctk.CTkFrame(pago_frame, fg_color="transparent")
        ref_frame.pack(fill="x", padx=15, pady=5)
        self.ref_label = ctk.CTkLabel(ref_frame, text="Referencia:", width=150, anchor="w")
        self.ref_label.pack(side="left")
        self.ref_entry = ctk.CTkEntry(ref_frame, width=250, placeholder_text="Número de referencia / comprobante")
        self.ref_entry.pack(side="left", padx=10)
        
        btn_frame = ctk.CTkFrame(pago_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)
        ctk.CTkButton(btn_frame, text="✅ REGISTRAR PAGO", command=lambda: self.registrar_pago(contrato_id, saldo_disponible),
                     fg_color=self.C_GREEN, text_color="black", height=40, width=250).pack()
        
        self.on_metodo_cambiado(None)
        self.on_moneda_cambiado(None)

    def on_mes_seleccionado(self, seleccion=None):
        sel = self.mes_combo.get()
        if hasattr(self, 'meses_dict') and sel in self.meses_dict:
            item = self.meses_dict[sel]
            if item.get('monto') and hasattr(self, 'monto_entry'):
                self.monto_entry.delete(0, 'end')
                self.monto_entry.insert(0, f"{item['monto']:.2f}")

    def on_metodo_cambiado(self, event):
        metodo = self.metodo_combo.get()
        
        if metodo == "Efectivo (USD)":
            self.moneda_label.configure(state="normal")
            self.moneda_combo.configure(state="normal")
            self.moneda_combo.set("USD")
            self.moneda_combo.configure(state="disabled")
            self.on_moneda_cambiado(None)
            self.ref_label.configure(text="Referencia (opcional):")
            self.ref_entry.configure(placeholder_text="Opcional")
            self.ref_entry.delete(0, "end")
        elif metodo == "Efectivo (BS)":
            self.moneda_label.configure(state="disabled")
            self.moneda_combo.configure(state="normal")
            self.moneda_combo.set("BS")
            self.moneda_combo.configure(state="disabled")
            self.on_moneda_cambiado(None)
            self.ref_label.configure(text="Referencia (opcional):")
            self.ref_entry.configure(placeholder_text="Opcional")
            self.ref_entry.delete(0, "end")
        elif metodo in ["Transferencia Bancaria", "Pago Móvil"]:
            self.moneda_label.configure(state="disabled")
            self.moneda_combo.configure(state="normal")
            self.moneda_combo.set("USD")
            self.moneda_combo.configure(state="disabled")
            self.on_moneda_cambiado(None)
            self.ref_label.configure(text="Referencia (obligatorio):")
            self.ref_entry.configure(placeholder_text="Número de referencia / comprobante")
        else:
            self.moneda_label.configure(state="normal")
            self.moneda_combo.configure(state="readonly")
            self.on_moneda_cambiado(None)
            self.ref_label.configure(text="Referencia (opcional):")
            self.ref_entry.configure(placeholder_text="Opcional - últimos 4 dígitos")
    
    def on_moneda_cambiado(self, event):
        moneda = self.moneda_combo.get()
        if moneda == "BS":
            tasa = PagoService.obtener_tasa_cambio_dia()
            self.tasa_info_label.configure(text=f"Tasa del día: 1 USD = {tasa:.2f} BS", text_color=self.C_GOLD)
        else:
            self.tasa_info_label.configure(text="")
    
    def registrar_pago(self, contrato_id, saldo_disponible):
        try:
            monto = parsear_decimal_monetario(self.monto_entry.get())
            if monto <= 0:
                raise ValueError("El monto debe ser mayor a cero")
        except ValueError:
            mb.showerror("Error", "Ingrese un monto válido mayor a 0 (ej. 25.50 o 25,50)")
            return
        
        metodo = self.metodo_combo.get()
        if metodo == "Efectivo (BS)":
            moneda = "BS"
        elif metodo in ["Efectivo (USD)", "Transferencia Bancaria", "Pago Móvil"]:
            moneda = "USD"
        else:
            moneda = self.moneda_combo.get()
        referencia = self.ref_entry.get().strip()
        
        if metodo in ["Transferencia Bancaria", "Pago Móvil"] and not referencia:
            mb.showerror("Error", f"El método {metodo} requiere un número de referencia")
            return
        
        tasa_cambio = None
        monto_usd = monto
        if moneda == "BS":
            tasa_cambio = PagoService.obtener_tasa_cambio_dia()
            monto_usd = monto / tasa_cambio
        if monto_usd > saldo_disponible + 0.01:
            mb.showerror(
                "Error",
                f"El monto equivalente en USD (${monto_usd:,.2f}) excede "
                f"el saldo pendiente (${saldo_disponible:,.2f})."
            )
            return
        if moneda == "BS":
            mb.showinfo(
                "Conversión",
                f"Monto en USD equivalente: ${monto_usd:.2f} "
                f"(tasa: 1 USD = {tasa_cambio:.2f} BS)"
            )
        
        sel_mes = self.mes_combo.get() if hasattr(self, "mes_combo") else "Abono / Pago General a Saldo"
        item_mes = getattr(self, "meses_dict", {}).get(sel_mes, {})
        cuota_asoc_id = item_mes.get("cuota_id")
        concepto_mes = item_mes.get("concepto") or sel_mes

        try:
            res_pago = PagoService.registrar_pago(
                contrato_id=contrato_id,
                monto=monto,
                metodo=metodo,
                referencia=referencia,
                moneda=moneda,
                tasa_cambio=tasa_cambio if moneda == "BS" else None,
                cuota_id=cuota_asoc_id,
                mes_periodo=concepto_mes
            )
            pid = res_pago['id'] if isinstance(res_pago, dict) else res_pago

            self.monto_entry.delete(0, "end")
            self.ref_entry.delete(0, "end")
            
            seleccion = self.contrato_om.get()
            if seleccion in self.contrato_dict:
                self.cargar_detalle(seleccion)
            self.cargar_contratos()

            # Preguntar si desea generar el recibo de pago PNF en PDF
            if mb.askyesno("Recibo de pago", f"✅ Pago de ${monto:,.2f} registrado correctamente vía {metodo}.\nMes / Período: {concepto_mes}\n\n¿Desea generar e imprimir el Recibo Oficial de Pago (PDF) ahora?"):
                self.generar_recibo_pago_pdf(pid)
            
        except Exception as e:
            mb.showerror("Error", f"No se pudo registrar el pago: {str(e)}")

    def generar_recibo_pago_pdf(self, pago_id):
        """Genera y abre el recibo oficial de pago en PDF"""
        from services.pdf_service import generar_pdf_recibo_pago
        import os
        try:
            ruta_pdf = generar_pdf_recibo_pago(int(pago_id))
            if ruta_pdf and os.path.exists(ruta_pdf):
                try:
                    os.startfile(ruta_pdf)
                except Exception:
                    pass
                mb.showinfo("Recibo PDF", f"✅ Recibo Oficial de Pago generado con éxito:\n{ruta_pdf}")
            else:
                mb.showerror("Error", "No se pudo generar el archivo PDF del recibo.")
        except Exception as ex:
            mb.showerror("Error", f"Error al generar recibo PDF: {str(ex)}")
    
    def crear_seccion_editar_horarios(self, contrato_data, cid, capilla_id):
        edit_frame = ctk.CTkFrame(self.scroll, fg_color=self.C_CARD, corner_radius=10)
        edit_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(edit_frame, text="✏️ EDITAR HORARIOS DEL SERVICIO", 
                    font=("Segoe UI", 14, "bold"), text_color=self.C_GOLD).pack(anchor="w", padx=15, pady=(10,5))
        
        row1 = ctk.CTkFrame(edit_frame, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row1, text="📅 Fecha Velación:", width=150, anchor="w").pack(side="left")
        ctk.CTkLabel(row1, text=contrato_data['fecha_velacion'], font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(row1, text="⏰ Hora Planificada:", width=130, anchor="w").pack(side="left", padx=(20,0))
        ctk.CTkLabel(row1, text=contrato_data['hora_inicio'], font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)
        
        row2 = ctk.CTkFrame(edit_frame, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row2, text="🚗 Hora Real de Llegada del Cuerpo:", width=200, anchor="w").pack(side="left")
        self.hora_llegada_entry = ctk.CTkEntry(row2, width=100)
        self.hora_llegada_entry.insert(0, contrato_data['hora_llegada_real'] or "")
        self.hora_llegada_entry.pack(side="left", padx=10)
        
        row3 = ctk.CTkFrame(edit_frame, fg_color="transparent")
        row3.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row3, text="🏛️ Hora de Salida de Capilla:", width=200, anchor="w").pack(side="left")
        self.hora_salida_entry = ctk.CTkEntry(row3, width=100)
        self.hora_salida_entry.insert(0, contrato_data['hora_salida_capilla'] or "")
        self.hora_salida_entry.pack(side="left", padx=10)
        
        btn_frame = ctk.CTkFrame(edit_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_frame, text="💾 Guardar Cambios de Horario", 
                     command=lambda: self.guardar_horarios(cid),
                     fg_color="#3498db", hover_color="#2980b9", width=200).pack(side="left", padx=10)
        
        # Botón FINALIZAR SERVICIO (solo si el contrato está activo)
        if contrato_data['estado'] == 'Activo' and capilla_id:
            ctk.CTkButton(btn_frame, text="🏁 FINALIZAR SERVICIO Y LIBERAR CAPILLA", 
                         command=lambda: self.finalizar_servicio(cid, capilla_id),
                         fg_color=self.C_RED, hover_color="#8B0000", width=280).pack(side="left", padx=10)
    
    def guardar_horarios(self, contrato_id):
        import re
        hora_llegada = self.hora_llegada_entry.get().strip()
        hora_salida = self.hora_salida_entry.get().strip()
        patron_hora = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
        
        if hora_llegada and not patron_hora.match(hora_llegada):
            mb.showwarning("Formato inválido", "La hora de llegada debe tener formato HH:MM")
            return
        if hora_salida and not patron_hora.match(hora_salida):
            mb.showwarning("Formato inválido", "La hora de salida debe tener formato HH:MM")
            return
        
        if ContratoRepository.actualizar_horario(contrato_id, hora_llegada or None, hora_salida or None):
            ContratoRepository.registrar_bitacora(self.usuario[0], "Edición de horarios",
                                                  f"Contrato {contrato_id}: Llegada={hora_llegada}, Salida={hora_salida}")
            mb.showinfo("Éxito", "Horarios actualizados correctamente")
            seleccion = self.contrato_om.get()
            if seleccion in self.contrato_dict:
                self.cargar_detalle(seleccion)
        else:
            mb.showerror("Error", "No se pudieron actualizar los horarios")
    
    def finalizar_servicio(self, contrato_id, capilla_id):
        """Finaliza el servicio y libera la capilla"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            # Cambiar estado del contrato a Finalizado
            cursor.execute("""
                UPDATE contratos 
                SET estado = 'Finalizado', estado_servicio = 'Finalizado'
                WHERE id = ?
            """, (contrato_id,))
            
            # Liberar la capilla
            cursor.execute("""
                UPDATE capillas 
                SET estado = 'Disponible'
                WHERE id = ?
            """, (capilla_id,))
            
            conn.commit()
            ContratoRepository.registrar_bitacora(
                self.usuario[0], 
                "Finalizar servicio", 
                f"Contrato {contrato_id} finalizado, capilla {capilla_id} liberada"
            )
            mb.showinfo("Éxito", "✅ Servicio finalizado correctamente.\n\nCapilla liberada y disponible para nuevos contratos.")
            
            # Recargar la vista
            seleccion = self.contrato_om.get()
            if seleccion in self.contrato_dict:
                self.cargar_detalle(seleccion)
            self.cargar_contratos()
            
        except Exception as e:
            conn.rollback()
            mb.showerror("Error", f"No se pudo finalizar el servicio: {str(e)}")
        finally:
            conn.close()
    
    def crear_seccion_informacion(self, contrato_data):
        info_frame = ctk.CTkFrame(self.scroll, fg_color=self.C_CARD, corner_radius=10)
        info_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(info_frame, text="📋 INFORMACIÓN DEL CONTRATO", 
                    font=("Segoe UI", 14, "bold"), text_color=self.C_GOLD).pack(anchor="w", padx=15, pady=(10,5))
        
        datos = [
            ("N° Contrato:", contrato_data['numero']),
            ("Difunto:", contrato_data['difunto']),
            ("Cédula Difunto:", contrato_data['difunto_cedula']),
            ("Responsable:", contrato_data['responsable']),
            ("Capilla:", contrato_data['capilla']),
            ("Paquete:", contrato_data['paquete']),
            ("Cremación:", "Sí" if contrato_data['requiere_cremacion'] else "No"),
            ("Traslado:", contrato_data['tipo_traslado'])
        ]
        
        info_grid = ctk.CTkFrame(info_frame, fg_color="transparent")
        info_grid.pack(fill="x", padx=15, pady=5)
        
        for i, (label, valor) in enumerate(datos):
            row = i // 2
            col = (i % 2) * 2
            ctk.CTkLabel(info_grid, text=label, font=("Segoe UI", 10, "bold"), width=130, anchor="w").grid(row=row, column=col, padx=5, pady=3, sticky="w")
            ctk.CTkLabel(info_grid, text=str(valor), font=("Segoe UI", 10), anchor="w").grid(row=row, column=col+1, padx=5, pady=3, sticky="w")

        # Reflejar Carga Familiar / Beneficiarios a su cargo si existen
        beneficiarios = contrato_data.get('beneficiarios') or []
        if beneficiarios:
            ben_frame = ctk.CTkFrame(info_frame, fg_color=("#F8FAFC", "#141A22"), corner_radius=8)
            ben_frame.pack(fill="x", padx=15, pady=(6, 10))
            ctk.CTkLabel(
                ben_frame,
                text=f"👨‍👩‍👧‍👦 CARGA FAMILIAR / BENEFICIARIOS A SU CARGO ({len(beneficiarios)} persona(s) + Titular = {len(beneficiarios) + 1}):",
                font=("Segoe UI", 11, "bold"),
                text_color=self.C_GOLD
            ).pack(anchor="w", padx=10, pady=(6, 4))

            for idx, b in enumerate(beneficiarios, 1):
                if b.get('tipo_documento') == 'Cedula':
                    doc_txt = f"C.I: {b.get('cedula') or '—'}"
                else:
                    doc_txt = f"Partida (Folio: {b.get('folio') or '—'} | Acta: {b.get('acta') or '—'})"
                par_txt = b.get('parentesco') or 'Familiar'
                linea = f"  {idx}. {b.get('nombre_completo')}  —  {doc_txt}  |  F. Nac: {b.get('fecha_nacimiento')} ({b.get('edad')} años)  |  Parentesco: {par_txt}"
                ctk.CTkLabel(
                    ben_frame,
                    text=linea,
                    font=("Segoe UI", 10),
                    anchor="w"
                ).pack(fill="x", padx=12, pady=1)
            ctk.CTkLabel(ben_frame, text="", height=4).pack()
    
    def mostrar_cuotas(self, contrato_id):
        cuotas_frame = ctk.CTkFrame(self.scroll, fg_color=self.C_CARD, corner_radius=10)
        cuotas_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(cuotas_frame, text="📆 PLAN DE CUOTAS", 
                    font=("Segoe UI", 14, "bold"), text_color=self.C_GOLD).pack(anchor="w", padx=15, pady=(10,5))
        
        cuotas = PagoService.obtener_cuotas_con_saldos(contrato_id)
        
        pendientes = sum(1 for c in cuotas if c["saldo"] > 0.01)
        self.kpi_cuotas.configure(text=f"{pendientes}/{len(cuotas)}")
        
        enc_frame = ctk.CTkFrame(cuotas_frame, fg_color="#0D2137", corner_radius=8)
        enc_frame.pack(fill="x", padx=10, pady=(5,2))
        headers = ["N°", "Monto", "Abonado", "Saldo", "Vencimiento", "Fecha Pago", "Estado", ""]
        widths = [45, 85, 85, 85, 105, 105, 85, 75]
        for h, w in zip(headers, widths):
            ctk.CTkLabel(enc_frame, text=h, font=("Segoe UI", 10, "bold"), 
                        text_color=self.C_GOLD, width=w, anchor="center").pack(side="left", padx=2, pady=5)
        
        for cu in cuotas:
            cuota_id = cu["id"]
            numero = cu["numero"]
            monto = cu["monto"]
            abonado = cu["pagado"]
            saldo = cu["saldo"]
            vcto = cu["fecha_vencimiento"]
            fpago = cu["fecha_pago"]
            estado = cu["estado"]
            bg = (
                "#1A4731" if saldo <= 0.01
                else "#3D1515" if estado == "Vencida"
                else self.C_NAVY
            )
            fila = ctk.CTkFrame(cuotas_frame, fg_color=bg, corner_radius=8)
            fila.pack(fill="x", padx=10, pady=2)
            

            ctk.CTkLabel(fila, text=str(numero), width=45, anchor="center").pack(side="left", padx=2, pady=6)
            ctk.CTkLabel(fila, text=f"${monto:,.2f}", width=85, anchor="center").pack(side="left", padx=2)
            ctk.CTkLabel(fila, text=f"${abonado:,.2f}", width=85, anchor="center").pack(side="left", padx=2)
            ctk.CTkLabel(fila, text=f"${saldo:,.2f}", width=85, anchor="center").pack(side="left", padx=2)
            ctk.CTkLabel(fila, text=formatear_fecha_ddmmyyyy(vcto), width=105, anchor="center").pack(side="left", padx=2)
            ctk.CTkLabel(fila, text=formatear_fecha_ddmmyyyy(fpago) if fpago else "—", width=105, anchor="center").pack(side="left", padx=2)
            
            color_estado = self.C_GREEN if saldo <= 0.01 else (self.C_RED if estado == "Vencida" else self.C_GOLD)
            ctk.CTkLabel(fila, text=estado, width=85, anchor="center", 
                        font=("Segoe UI", 10, "bold"), text_color=color_estado).pack(side="left", padx=2)
            
            if saldo > 0.01:
                ctk.CTkButton(fila, text="Pagar", width=65, height=25,
                             fg_color=self.C_GOLD, text_color="black",
                             command=lambda ci=cuota_id, m=saldo: self.pagar_cuota(ci, m, contrato_id)).pack(side="left", padx=5)
    
    def pagar_cuota(self, cuota_id, monto_max, contrato_id):
        dialog = ctk.CTkInputDialog(text=f"Monto a pagar (máx. ${monto_max:,.2f}):", title="Registrar Pago")
        valor = dialog.get_input()
        if not valor:
            return
        try:
            monto = float(valor)
            if monto <= 0 or monto > monto_max + 0.01:
                raise ValueError
        except:
            mb.showerror("Error", "Monto inválido")
            return
        
        try:
            pago = PagoService.registrar_pago(
                contrato_id=contrato_id,
                monto=monto,
                metodo="Efectivo (USD)",
                referencia="",
                moneda="USD",
                cuota_id=cuota_id
            )
            pago_id = pago["id"] if isinstance(pago, dict) else pago
            if mb.askyesno(
                "Recibo de pago",
                f"Pago de ${monto:,.2f} registrado correctamente.\n"
                "¿Desea generar el recibo PDF ahora?",
            ):
                self.generar_recibo_pago_pdf(pago_id)
            seleccion = self.contrato_om.get()
            if seleccion in self.contrato_dict:
                self.cargar_detalle(seleccion)
            self.cargar_contratos()
        except Exception as e:
            mb.showerror("Error", str(e))
    
    def mostrar_historial_pagos(self, contrato_id):
        """Muestra el historial de pagos con botón para ver detalle y generar recibo PDF"""
        hist_frame = ctk.CTkFrame(self.scroll, fg_color=self.C_CARD, corner_radius=10)
        hist_frame.pack(fill="x", pady=(0, 10))
        
        top_hist = ctk.CTkFrame(hist_frame, fg_color="transparent")
        top_hist.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkLabel(top_hist, text="📜 HISTORIAL DE PAGOS", 
                    font=("Segoe UI", 14, "bold"), text_color=self.C_GOLD).pack(side="left")
        
        pagos = PagoService.obtener_pagos_contrato(contrato_id)
        
        if pagos:
            ctk.CTkButton(top_hist, text="📄 Generar Recibo de Pago (PDF)", 
                         command=lambda: self.generar_recibo_desde_tabla(tree),
                         fg_color="#D4AF37", hover_color="#B8860B", text_color="black", 
                         font=("Segoe UI", 11, "bold"), height=30).pack(side="right")

            from utils.helpers import aplicar_estilo_treeview
            aplicar_estilo_treeview()
            
            cols = ("id", "Fecha", "Mes", "Monto", "Método", "Moneda", "Referencia", "Acción")
            tree = ttk.Treeview(hist_frame, columns=cols, show="headings", height=min(len(pagos), 6))
            tree.heading("id", text="ID")
            tree.heading("Fecha", text="Fecha")
            tree.heading("Mes", text="Mes / Período")
            tree.heading("Monto", text="Monto")
            tree.heading("Método", text="Método")
            tree.heading("Moneda", text="Moneda")
            tree.heading("Referencia", text="Referencia")
            tree.heading("Acción", text="Acción")
            
            tree.column("id", width=45, anchor="center")
            tree.column("Fecha", width=125, anchor="center")
            tree.column("Mes", width=170, anchor="w")
            tree.column("Monto", width=95, anchor="center")
            tree.column("Método", width=150, anchor="center")
            tree.column("Moneda", width=80, anchor="center")
            tree.column("Referencia", width=130, anchor="center")
            tree.column("Acción", width=75, anchor="center")
            
            # Insertar datos
            for p in pagos:
                moneda_str = p['moneda']
                if p['moneda'] == "BS" and p['tasa_cambio']:
                    moneda_str = f"BS (tasa: {p['tasa_cambio']:.2f})"
                
                tree.insert("", "end", values=(
                    p['id'],
                    formatear_fecha_ddmmyyyy(p['fecha']),
                    p.get('mes_periodo') or "—",
                    f"${p['monto']:,.2f}",
                    p['metodo'],
                    moneda_str,
                    (p['referencia'] or "—")[:30],
                    "🔍 Ver"
                ))
            
            tree.pack(fill="x", padx=10, pady=5)
            
            # Bind click en la tabla
            def on_tree_click(event):
                region = tree.identify_region(event.x, event.y)
                if region == "cell":
                    column = tree.identify_column(event.x)
                    if column == "#8":  # Columna Acción
                        item = tree.identify_row(event.y)
                        if item:
                            valores = tree.item(item, "values")
                            pago_id = valores[0]
                            self.ver_detalle_pago(pago_id)
            
            tree.bind("<ButtonRelease-1>", on_tree_click)
            tree.bind("<Double-1>", lambda e: self.generar_recibo_desde_tabla(tree))
            
            # Resumen por método
            resumen = PagoService.obtener_resumen_pagos_contrato(contrato_id)
            if resumen['por_metodo']:
                resumen_text = "📊 Resumen: " + " | ".join([f"{k}: ${v:,.2f}" for k, v in resumen['por_metodo'].items()])
                ctk.CTkLabel(hist_frame, text=resumen_text, font=("Segoe UI", 10), 
                            text_color=self.C_GRAY).pack(pady=5)
        else:
            ctk.CTkLabel(hist_frame, text="Sin pagos registrados", 
                        font=("Segoe UI", 11), text_color=self.C_GRAY).pack(pady=10)
    
    def generar_recibo_desde_tabla(self, tree):
        """Genera el recibo PDF del pago seleccionado en la tabla"""
        sel = tree.selection()
        if not sel:
            mb.showwarning("Selección Requerida", "Seleccione un pago de la lista para generar o imprimir su Recibo Oficial en PDF.")
            return
        vals = tree.item(sel[0], "values")
        pago_id = vals[0]
        self.generar_recibo_pago_pdf(pago_id)

    def ver_detalle_pago(self, pago_id):
        """Abre la ventana de detalle del pago"""
        from ui.visor_pago import VisorPago
        VisorPago(self, pago_id)