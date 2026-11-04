# ui/reportes_frame.py - Módulo de reportes y estadísticas avanzados
import customtkinter as ctk
import tkinter.messagebox as mb
from tkinter import ttk
import datetime
import os
from services.reporte_service import ReporteService
from services.db_service import ContratoRepository
from utils.helpers import aplicar_estilo_treeview, formatear_moneda

class ReportesFrame(ctk.CTkFrame):
    """Módulo de reportes y estadísticas del sistema"""
    
    # Colores armonizados con el tema del sistema (soporte Claro y Oscuro)
    C_BG = "transparent"
    C_CARD = ("#FFFFFF", "#1A1E26")
    C_GOLD = "#D4AF37"
    C_GREEN = "#2ECC71"
    C_RED = "#E74C3C"
    C_BLUE = "#3498DB"
    C_ORANGE = "#F39C12"
    C_GRAY = ("#64748B", "#9DA3AE")
    C_WHITE = ("#0F172A", "#FFFFFF")
    
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.configure(fg_color=self.C_BG)
        self.crear_interfaz()
        self.cargar_reporte_ventas()

    @staticmethod
    def _mostrar_pdf_generado(ruta, titulo, mensaje):
        ruta = os.path.abspath(ruta)
        mb.showinfo(titulo, f"{mensaje}\n{ruta}")
        try:
            os.startfile(ruta)
        except OSError as exc:
            mb.showerror(
                "No se pudo abrir el PDF",
                f"El archivo se guardó correctamente, pero no se pudo abrir:\n{ruta}\n\n{exc}",
            )
    
    def crear_interfaz(self):
        # Título
        ctk.CTkLabel(self, text="📊 Reportes y Estadísticas", 
                    font=("Segoe UI", 28, "bold"), text_color=self.C_GOLD).pack(pady=20)
        
        # TabView para diferentes reportes
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Pestañas
        tab_ventas = self.tabview.add("💰 Ventas")
        tab_cuotas = self.tabview.add("⚠️ Cuotas Vencidas")
        tab_productos = self.tabview.add("📦 Productos Vendidos")
        tab_servicios = self.tabview.add("🎯 Servicios Adicionales")
        tab_mensual = self.tabview.add("📈 Ingresos Mensuales")
        tab_clientes = self.tabview.add("👥 Top Clientes")
        tab_capillas = self.tabview.add("🏛️ Ocupación Capillas")
        tab_resumen = self.tabview.add("📋 Resumen General")
        
        # Crear cada pestaña
        self.crear_tab_ventas(tab_ventas)
        self.crear_tab_cuotas(tab_cuotas)
        self.crear_tab_productos(tab_productos)
        self.crear_tab_servicios(tab_servicios)
        self.crear_tab_mensual(tab_mensual)
        self.crear_tab_clientes(tab_clientes)
        self.crear_tab_capillas(tab_capillas)
        self.crear_tab_resumen(tab_resumen)
    
    def crear_tab_ventas(self, parent):
        """Pestaña de reporte de ventas por período"""
        # Filtros
        filtros_frame = ctk.CTkFrame(parent, fg_color=self.C_CARD, corner_radius=10)
        filtros_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(filtros_frame, text="Período:", font=("Segoe UI", 12, "bold"),
                    text_color=self.C_GOLD).pack(side="left", padx=15, pady=10)
        
        # Fecha inicio
        ctk.CTkLabel(filtros_frame, text="Desde (DD/MM/AAAA):").pack(side="left", padx=(10,5))
        self.fecha_inicio = ctk.CTkEntry(filtros_frame, width=130, placeholder_text="DD/MM/AAAA")
        self.fecha_inicio.insert(0, (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%d/%m/%Y"))
        self.fecha_inicio.pack(side="left", padx=5)
        
        # Fecha fin
        ctk.CTkLabel(filtros_frame, text="Hasta (DD/MM/AAAA):").pack(side="left", padx=(10,5))
        self.fecha_fin = ctk.CTkEntry(filtros_frame, width=130, placeholder_text="DD/MM/AAAA")
        self.fecha_fin.insert(0, datetime.datetime.now().strftime("%d/%m/%Y"))
        self.fecha_fin.pack(side="left", padx=5)
        
        # Botón actualizar
        ctk.CTkButton(filtros_frame, text="🔍 Actualizar", command=self.cargar_reporte_ventas,
                     fg_color=self.C_BLUE, width=120).pack(side="left", padx=15)
        
        # Botón exportar
        ctk.CTkButton(filtros_frame, text="📄 Exportar a PDF", command=self.exportar_ventas_pdf,
                     fg_color=self.C_GOLD, text_color="black", font=("Segoe UI", 11, "bold"), width=140).pack(side="right", padx=6)
        ctk.CTkButton(filtros_frame, text="📎 Exportar a Excel", command=self.exportar_ventas_excel,
                     fg_color=self.C_GREEN, text_color="black", width=140).pack(side="right", padx=6)
        
        # Tarjetas de KPIs
        kpi_frame = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=10, pady=10)
        
        self.kpi_total_ventas = self._crear_kpi(kpi_frame, "💰 Total Ventas", "$0.00", self.C_GOLD, 0)
        self.kpi_cantidad_contratos = self._crear_kpi(kpi_frame, "📄 Contratos", "0", self.C_BLUE, 1)
        self.kpi_promedio = self._crear_kpi(kpi_frame, "📊 Promedio por Contrato", "$0.00", self.C_ORANGE, 2)
        self.kpi_usd = self._crear_kpi(kpi_frame, "💵 USD", "$0.00", self.C_GREEN, 3)
        
        # Segunda fila de KPIs
        kpi_frame2 = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_frame2.pack(fill="x", padx=10, pady=5)
        
        self.kpi_bs = self._crear_kpi(kpi_frame2, "🇻🇪 Bolívares", "Bs 0.00", self.C_ORANGE, 0)
        
        # Tabla de ingresos por paquete
        ctk.CTkLabel(parent, text="Ingresos por Paquete", font=("Segoe UI", 14, "bold"),
                    text_color=self.C_GOLD).pack(anchor="w", padx=15, pady=(10,5))
        
        self.ventas_tree = ttk.Treeview(parent, columns=("paquete", "cantidad", "total"), show="headings", height=5)
        self.ventas_tree.heading("paquete", text="Paquete")
        self.ventas_tree.heading("cantidad", text="Cantidad")
        self.ventas_tree.heading("total", text="Total")
        self.ventas_tree.column("paquete", width=150)
        self.ventas_tree.column("cantidad", width=100)
        self.ventas_tree.column("total", width=150)
        self.ventas_tree.pack(fill="x", padx=15, pady=5)
        
        # Tabla de ingresos por método de pago
        ctk.CTkLabel(parent, text="Ingresos por Método de Pago", font=("Segoe UI", 14, "bold"),
                    text_color=self.C_GOLD).pack(anchor="w", padx=15, pady=(10,5))
        
        self.metodo_tree = ttk.Treeview(parent, columns=("metodo", "total"), show="headings", height=5)
        self.metodo_tree.heading("metodo", text="Método de Pago")
        self.metodo_tree.heading("total", text="Total")
        self.metodo_tree.column("metodo", width=200)
        self.metodo_tree.column("total", width=150)
        self.metodo_tree.pack(fill="x", padx=15, pady=5)
        
        aplicar_estilo_treeview()
    
    def _crear_kpi(self, parent, titulo, valor, color, col):
        card = ctk.CTkFrame(parent, fg_color=color, corner_radius=12, width=180, height=80)
        card.grid(row=0, column=col, padx=10, pady=5, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        
        ctk.CTkLabel(card, text=titulo, font=("Segoe UI", 10, "bold"), 
                    text_color="white").pack(pady=(8,0))
        lbl = ctk.CTkLabel(card, text=valor, font=("Segoe UI", 16, "bold"), 
                          text_color="white")
        lbl.pack(pady=5)
        return lbl
    
    def cargar_reporte_ventas(self):
        fecha_ini = self.fecha_inicio.get().strip()
        fecha_fin = self.fecha_fin.get().strip()
        
        if not fecha_ini or not fecha_fin:
            mb.showwarning("Fechas", "Ingrese fecha de inicio y fin")
            return
        
        datos = ReporteService.ventas_por_periodo(fecha_ini, fecha_fin)
        
        self.kpi_total_ventas.configure(text=f"${datos['total_ventas']:,.2f}")
        self.kpi_cantidad_contratos.configure(text=str(datos['cantidad_contratos']))
        self.kpi_promedio.configure(text=f"${datos['promedio_por_contrato']:,.2f}")
        self.kpi_usd.configure(text=f"${datos['ingresos_usd']:,.2f}")
        self.kpi_bs.configure(text=f"Bs {datos['ingresos_bs']:,.2f}")
        
        # Limpiar y cargar tabla de paquetes
        for row in self.ventas_tree.get_children():
            self.ventas_tree.delete(row)
        
        for p in datos['ingresos_por_paquete']:
            self.ventas_tree.insert("", "end", values=(p['paquete'], p['cantidad'], f"${p['total']:,.2f}"))
        
        # Limpiar y cargar tabla de métodos
        for row in self.metodo_tree.get_children():
            self.metodo_tree.delete(row)
        
        for metodo, total in datos['ingresos_por_metodo'].items():
            self.metodo_tree.insert("", "end", values=(metodo, f"${total:,.2f}"))
    
    def exportar_ventas_excel(self):
        fecha_ini = self.fecha_inicio.get().strip()
        fecha_fin = self.fecha_fin.get().strip()
        datos = ReporteService.ventas_por_periodo(fecha_ini, fecha_fin)
        
        export_data = []
        export_data.append({"Periodo": f"{fecha_ini} al {fecha_fin}", "Total Ventas": datos['total_ventas']})
        export_data.append({"Cantidad Contratos": datos['cantidad_contratos'], "Promedio": datos['promedio_por_contrato']})
        export_data.append({"USD": datos['ingresos_usd'], "Bolívares": datos['ingresos_bs']})
        
        for p in datos['ingresos_por_paquete']:
            export_data.append({"Paquete": p['paquete'], "Cantidad": p['cantidad'], "Total": p['total']})
        
        ruta = ReporteService.exportar_a_excel(export_data, "reporte_ventas")
        if ruta:
            mb.showinfo("Exportación Exitosa", f"Archivo guardado en:\n{ruta}")
        else:
            mb.showerror("Error", "No se pudo exportar. Instale: pip install pandas openpyxl")

    def exportar_ventas_pdf(self):
        fecha_ini = self.fecha_inicio.get().strip()
        fecha_fin = self.fecha_fin.get().strip()
        datos = ReporteService.ventas_por_periodo(fecha_ini, fecha_fin)
        
        columnas = ["Concepto / Paquete", "Cantidad / Detalle", "Total Recaudado (USD)"]
        filas = [
            ["Ventas Totales del Período", f"{datos['cantidad_contratos']} Contratos", f"${datos['total_ventas']:,.2f}"],
            ["Promedio por Contrato", "—", f"${datos['promedio_por_contrato']:,.2f}"],
            ["Recaudación en USD", "Dólares", f"${datos['ingresos_usd']:,.2f}"],
            ["Recaudación en Bolívares", "Bolívares", f"Bs {datos['ingresos_bs']:,.2f}"]
        ]
        for p in datos['ingresos_por_paquete']:
            filas.append([f"Paquete: {p['paquete']}", f"{p['cantidad']} Contratos", f"${p['total']:,.2f}"])
        for met, tot in datos['ingresos_por_metodo'].items():
            filas.append([f"Método: {met}", "—", f"${tot:,.2f}"])
            
        ruta = ReporteService.exportar_a_pdf(f"Ventas del {fecha_ini} al {fecha_fin}", columnas, filas, "reporte_ventas")
        if ruta and os.path.exists(ruta):
            self._mostrar_pdf_generado(ruta, "PDF Generado", "Reporte PDF guardado en:")
        else:
            mb.showerror("Error", "No se pudo generar el reporte en PDF.")
    
    def crear_tab_cuotas(self, parent):
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="🔍 Actualizar", command=self.cargar_cuotas_vencidas,
                     fg_color=self.C_BLUE).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📄 Generar / Ver PDF del Contrato", command=self.abrir_pdf_contrato_seleccionado,
                     fg_color=self.C_GOLD, text_color="black", font=("Segoe UI", 11, "bold"), width=220).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📄 Exportar Cuotas a PDF", command=self.exportar_cuotas_pdf,
                     fg_color=self.C_ORANGE, text_color="black", width=160).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📎 Exportar a Excel", command=self.exportar_cuotas_excel,
                     fg_color=self.C_GREEN, text_color="black").pack(side="left", padx=5)
        
        # Tabla con más columnas
        columns = ("id", "contrato", "difunto", "responsable", "cuota", "monto", "vencimiento", "dias_atraso", "telefono")
        self.cuotas_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        self.cuotas_tree.heading("id", text="ID Contrato")
        self.cuotas_tree.heading("contrato", text="N° Contrato")
        self.cuotas_tree.heading("difunto", text="Difunto")
        self.cuotas_tree.heading("responsable", text="Responsable")
        self.cuotas_tree.heading("cuota", text="N° Cuota")
        self.cuotas_tree.heading("monto", text="Monto")
        self.cuotas_tree.heading("vencimiento", text="Fecha Vencimiento")
        self.cuotas_tree.heading("dias_atraso", text="Días Atraso")
        self.cuotas_tree.heading("telefono", text="Teléfono")
        
        self.cuotas_tree.column("id", width=70, anchor="center")
        self.cuotas_tree.column("contrato", width=130)
        self.cuotas_tree.column("difunto", width=130)
        self.cuotas_tree.column("responsable", width=140)
        self.cuotas_tree.column("cuota", width=70, anchor="center")
        self.cuotas_tree.column("monto", width=80, anchor="center")
        self.cuotas_tree.column("vencimiento", width=110, anchor="center")
        self.cuotas_tree.column("dias_atraso", width=80, anchor="center")
        self.cuotas_tree.column("telefono", width=110, anchor="center")
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.cuotas_tree.yview)
        self.cuotas_tree.configure(yscrollcommand=scrollbar.set)
        self.cuotas_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        self.cuotas_tree.bind("<Double-1>", lambda e: self.abrir_pdf_contrato_seleccionado())
        
        aplicar_estilo_treeview()
        self.cargar_cuotas_vencidas()
    
    def cargar_cuotas_vencidas(self):
        for row in self.cuotas_tree.get_children():
            self.cuotas_tree.delete(row)
        
        cuotas = ReporteService.cuotas_vencidas()
        
        from utils.helpers import formatear_fecha_ddmmyyyy
        for c in cuotas:
            self.cuotas_tree.insert("", "end", values=(
                c.get('contrato_id', '—'),
                c['contrato_numero'],
                c['difunto'],
                c['responsable'],
                c['cuota_numero'],
                f"${c['monto']:,.2f}",
                formatear_fecha_ddmmyyyy(c['fecha_vencimiento']),
                c['dias_atraso'],
                c['telefono']
            ))
        
        if cuotas:
            ctk.CTkLabel(self.cuotas_tree.master, text=f"Total: {len(cuotas)} cuotas vencidas | Monto total: ${sum(c['monto'] for c in cuotas):,.2f}", 
                        font=("Segoe UI", 11), text_color=self.C_RED).pack(pady=5)

    def abrir_pdf_contrato_seleccionado(self):
        sel = self.cuotas_tree.selection()
        if not sel:
            mb.showwarning("Selección Requerida", "Seleccione una fila de cuota/contrato en la tabla para ver su documento PDF.")
            return
        vals = self.cuotas_tree.item(sel[0], "values")
        cid = vals[0]
        cnum = vals[1]
        
        from services.pdf_service import generar_pdf_contrato
        import os
        try:
            cid_int = int(cid)
            pdf_ruta = generar_pdf_contrato(cid_int)
        except Exception:
            pdf_ruta = None

        if pdf_ruta and os.path.exists(pdf_ruta):
            mb.showinfo("PDF del Contrato", f"Abriendo PDF oficial del contrato {cnum}:\n{pdf_ruta}")
            try:
                os.startfile(pdf_ruta)
            except Exception:
                pass
        else:
            mb.showerror("Error", f"No se pudo generar el PDF del contrato {cnum}.")

    def exportar_cuotas_pdf(self):
        cuotas = ReporteService.cuotas_vencidas()
        if not cuotas:
            mb.showinfo("Sin Datos", "No hay cuotas vencidas para exportar.")
            return
        columnas = ["N° Contrato", "Titular / Responsable", "Cuota", "Monto", "Vencimiento", "Días Atraso", "Teléfono"]
        filas = []
        from utils.helpers import formatear_fecha_ddmmyyyy
        for c in cuotas:
            filas.append([
                c['contrato_numero'],
                c['responsable'],
                f"#{c['cuota_numero']}",
                f"${c['monto']:,.2f}",
                formatear_fecha_ddmmyyyy(c['fecha_vencimiento']),
                f"{c['dias_atraso']} días",
                c['telefono']
            ])
        ruta = ReporteService.exportar_a_pdf("Cuotas Vencidas en Cartera", columnas, filas, "reporte_cuotas_vencidas")
        if ruta and os.path.exists(ruta):
            self._mostrar_pdf_generado(ruta, "PDF Generado", "Reporte de cuotas vencidas guardado en:")
        else:
            mb.showerror("Error", "No se pudo generar el PDF del reporte.")
    
    def exportar_cuotas_excel(self):
        cuotas = ReporteService.cuotas_vencidas()
        ruta = ReporteService.exportar_a_excel(cuotas, "cuotas_vencidas")
        if ruta:
            mb.showinfo("Exportación Exitosa", f"Archivo guardado en:\n{ruta}")
    
    def crear_tab_productos(self, parent):
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="🔍 Actualizar", command=self.cargar_productos_vendidos,
                     fg_color=self.C_BLUE).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📄 Exportar a PDF", command=self.exportar_productos_pdf,
                     fg_color="#D97706", hover_color="#B45309", text_color="white").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📎 Exportar a Excel", command=self.exportar_productos_excel,
                     fg_color=self.C_GREEN, text_color="black").pack(side="left", padx=5)
        
        columns = ("producto", "cantidad", "ingresos")
        self.productos_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        self.productos_tree.heading("producto", text="Producto")
        self.productos_tree.heading("cantidad", text="Cantidad Vendida")
        self.productos_tree.heading("ingresos", text="Ingresos")
        
        self.productos_tree.column("producto", width=250)
        self.productos_tree.column("cantidad", width=120)
        self.productos_tree.column("ingresos", width=150)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.productos_tree.yview)
        self.productos_tree.configure(yscrollcommand=scrollbar.set)
        self.productos_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        
        aplicar_estilo_treeview()
        self.cargar_productos_vendidos()
    
    def cargar_productos_vendidos(self):
        for row in self.productos_tree.get_children():
            self.productos_tree.delete(row)
        
        productos = ReporteService.productos_mas_vendidos(20)
        
        for p in productos:
            self.productos_tree.insert("", "end", values=(
                p['producto'],
                p['cantidad_vendida'],
                f"${p['ingresos']:,.2f}"
            ))
        
        if productos:
            total_ingresos = sum(p['ingresos'] for p in productos)
            ctk.CTkLabel(self.productos_tree.master, text=f"Total ingresos por productos: ${total_ingresos:,.2f}", 
                        font=("Segoe UI", 11), text_color=self.C_GOLD).pack(pady=5)
    
    def exportar_productos_pdf(self):
        productos = ReporteService.productos_mas_vendidos(20)
        if not productos:
            mb.showinfo("Sin Datos", "No hay datos de productos para exportar.")
            return
        columnas = ["Producto / Ataúd", "Cantidad Vendida", "Total Ingresos"]
        filas = [[p['producto'], str(p['cantidad_vendida']), f"${p['ingresos']:,.2f}"] for p in productos]
        ruta = ReporteService.exportar_a_pdf("Productos Más Vendidos", columnas, filas, "reporte_productos_vendidos")
        if ruta and os.path.exists(ruta):
            self._mostrar_pdf_generado(ruta, "PDF Generado", "Reporte PDF guardado en:")
        else:
            mb.showerror("Error", "No se pudo generar el PDF del reporte.")

    def exportar_productos_excel(self):
        productos = ReporteService.productos_mas_vendidos(20)
        ruta = ReporteService.exportar_a_excel(productos, "productos_vendidos")
        if ruta:
            mb.showinfo("Exportación Exitosa", f"Archivo guardado en:\n{ruta}")
    
    def crear_tab_servicios(self, parent):
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="🔍 Actualizar", command=self.cargar_servicios_solicitados,
                     fg_color=self.C_BLUE).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📄 Exportar a PDF", command=self.exportar_servicios_pdf,
                     fg_color="#D97706", hover_color="#B45309", text_color="white").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📎 Exportar a Excel", command=self.exportar_servicios_excel,
                     fg_color=self.C_GREEN, text_color="black").pack(side="left", padx=5)
        
        columns = ("servicio", "tipo", "veces", "unidades", "ingresos")
        self.servicios_tree = ttk.Treeview(parent, columns=columns, show="headings", height=12)
        self.servicios_tree.heading("servicio", text="Servicio")
        self.servicios_tree.heading("tipo", text="Tipo Velación")
        self.servicios_tree.heading("veces", text="Veces Solicitado")
        self.servicios_tree.heading("unidades", text="Total Unidades")
        self.servicios_tree.heading("ingresos", text="Ingresos")
        
        self.servicios_tree.column("servicio", width=200)
        self.servicios_tree.column("tipo", width=100)
        self.servicios_tree.column("veces", width=100)
        self.servicios_tree.column("unidades", width=100)
        self.servicios_tree.column("ingresos", width=120)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.servicios_tree.yview)
        self.servicios_tree.configure(yscrollcommand=scrollbar.set)
        self.servicios_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        
        aplicar_estilo_treeview()
        self.cargar_servicios_solicitados()
    
    def cargar_servicios_solicitados(self):
        for row in self.servicios_tree.get_children():
            self.servicios_tree.delete(row)
        
        servicios = ReporteService.servicios_adicionales_mas_solicitados(20)
        
        for s in servicios:
            self.servicios_tree.insert("", "end", values=(
                s['servicio'],
                s['tipo_velacion'],
                s['veces_solicitado'],
                s['total_unidades'],
                f"${s['ingresos']:,.2f}"
            ))
        
        if servicios:
            total_ingresos = sum(s['ingresos'] for s in servicios)
            ctk.CTkLabel(self.servicios_tree.master, text=f"Total ingresos por servicios adicionales: ${total_ingresos:,.2f}", 
                        font=("Segoe UI", 11), text_color=self.C_GOLD).pack(pady=5)
    
    def exportar_servicios_pdf(self):
        servicios = ReporteService.servicios_adicionales_mas_solicitados(20)
        if not servicios:
            mb.showinfo("Sin Datos", "No hay datos de servicios para exportar.")
            return
        columnas = ["Servicio Adicional", "Tipo de Velación", "Veces Solicitado", "Total Unidades", "Total Ingresos"]
        filas = [[s['servicio'], s['tipo_velacion'], str(s['veces_solicitado']), str(s['total_unidades']), f"${s['ingresos']:,.2f}"] for s in servicios]
        ruta = ReporteService.exportar_a_pdf("Servicios Adicionales Solicitados", columnas, filas, "reporte_servicios_adicionales")
        if ruta and os.path.exists(ruta):
            self._mostrar_pdf_generado(ruta, "PDF Generado", "Reporte PDF guardado en:")
        else:
            mb.showerror("Error", "No se pudo generar el PDF del reporte.")

    def exportar_servicios_excel(self):
        servicios = ReporteService.servicios_adicionales_mas_solicitados(20)
        ruta = ReporteService.exportar_a_excel(servicios, "servicios_adicionales")
        if ruta:
            mb.showinfo("Exportación Exitosa", f"Archivo guardado en:\n{ruta}")
    
    def crear_tab_mensual(self, parent):
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(btn_frame, text="Año:").pack(side="left", padx=5)
        self.anio_var = ctk.StringVar(value=str(datetime.datetime.now().year))
        anio_combo = ctk.CTkComboBox(btn_frame, values=[str(a) for a in range(2020, 2030)], 
                                     variable=self.anio_var, width=80, state="readonly")
        anio_combo.pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="🔍 Actualizar", command=self.cargar_ingresos_mensuales,
                     fg_color=self.C_BLUE).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📎 Exportar a Excel", command=self.exportar_mensual_excel,
                     fg_color=self.C_GREEN, text_color="black").pack(side="left", padx=5)
        
        columns = ("mes", "total")
        self.mensual_tree = ttk.Treeview(parent, columns=columns, show="headings", height=12)
        self.mensual_tree.heading("mes", text="Mes")
        self.mensual_tree.heading("total", text="Ingresos")
        self.mensual_tree.column("mes", width=150)
        self.mensual_tree.column("total", width=150)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.mensual_tree.yview)
        self.mensual_tree.configure(yscrollcommand=scrollbar.set)
        self.mensual_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        
        aplicar_estilo_treeview()
        self.cargar_ingresos_mensuales()
    
    def cargar_ingresos_mensuales(self):
        for row in self.mensual_tree.get_children():
            self.mensual_tree.delete(row)
        
        anio = int(self.anio_var.get())
        ingresos = ReporteService.ingresos_mensuales(anio)
        
        total_anual = 0
        for i in ingresos:
            self.mensual_tree.insert("", "end", values=(i['mes_nombre'], f"${i['total']:,.2f}"))
            total_anual += i['total']
        
        ctk.CTkLabel(self.mensual_tree.master, text=f"Total {anio}: ${total_anual:,.2f}", 
                    font=("Segoe UI", 12, "bold"), text_color=self.C_GOLD).pack(pady=5)
    
    def exportar_mensual_excel(self):
        anio = int(self.anio_var.get())
        ingresos = ReporteService.ingresos_mensuales(anio)
        ruta = ReporteService.exportar_a_excel(ingresos, f"ingresos_mensuales_{anio}")
        if ruta:
            mb.showinfo("Exportación Exitosa", f"Archivo guardado en:\n{ruta}")
    
    def crear_tab_clientes(self, parent):
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="🔍 Actualizar", command=self.cargar_top_clientes,
                     fg_color=self.C_BLUE).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📎 Exportar a Excel", command=self.exportar_clientes_excel,
                     fg_color=self.C_GREEN, text_color="black").pack(side="left", padx=5)
        
        columns = ("responsable", "cedula", "telefono", "contratos", "total_gastado", "pagado", "saldo")
        self.clientes_tree = ttk.Treeview(parent, columns=columns, show="headings", height=12)
        self.clientes_tree.heading("responsable", text="Responsable")
        self.clientes_tree.heading("cedula", text="Cédula")
        self.clientes_tree.heading("telefono", text="Teléfono")
        self.clientes_tree.heading("contratos", text="Contratos")
        self.clientes_tree.heading("total_gastado", text="Total Gastado")
        self.clientes_tree.heading("pagado", text="Pagado")
        self.clientes_tree.heading("saldo", text="Saldo Pendiente")
        
        for col in columns:
            self.clientes_tree.column(col, width=130)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.clientes_tree.yview)
        self.clientes_tree.configure(yscrollcommand=scrollbar.set)
        self.clientes_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        
        aplicar_estilo_treeview()
        self.cargar_top_clientes()
    
    def cargar_top_clientes(self):
        for row in self.clientes_tree.get_children():
            self.clientes_tree.delete(row)
        
        clientes = ReporteService.top_clientes(20)
        
        for c in clientes:
            self.clientes_tree.insert("", "end", values=(
                c['responsable'],
                c['cedula'],
                c['telefono'],
                c['cantidad_contratos'],
                f"${c['total_gastado']:,.2f}",
                f"${c['total_pagado']:,.2f}",
                f"${c['saldo_pendiente']:,.2f}"
            ))
    
    def exportar_clientes_excel(self):
        clientes = ReporteService.top_clientes(20)
        ruta = ReporteService.exportar_a_excel(clientes, "top_clientes")
        if ruta:
            mb.showinfo("Exportación Exitosa", f"Archivo guardado en:\n{ruta}")
    
    def crear_tab_capillas(self, parent):
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="🔍 Actualizar", command=self.cargar_ocupacion_capillas,
                     fg_color=self.C_BLUE).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📎 Exportar a Excel", command=self.exportar_capillas_excel,
                     fg_color=self.C_GREEN, text_color="black").pack(side="left", padx=5)
        
        columns = ("capilla", "capacidad", "contratos", "detalles")
        self.capillas_tree = ttk.Treeview(parent, columns=columns, show="headings", height=8)
        self.capillas_tree.heading("capilla", text="Capilla")
        self.capillas_tree.heading("capacidad", text="Capacidad")
        self.capillas_tree.heading("contratos", text="Contratos Próximos")
        self.capillas_tree.heading("detalles", text="Detalles")
        
        self.capillas_tree.column("capilla", width=150)
        self.capillas_tree.column("capacidad", width=80)
        self.capillas_tree.column("contratos", width=100)
        self.capillas_tree.column("detalles", width=350)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.capillas_tree.yview)
        self.capillas_tree.configure(yscrollcommand=scrollbar.set)
        self.capillas_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        
        aplicar_estilo_treeview()
        self.cargar_ocupacion_capillas()
    
    def cargar_ocupacion_capillas(self):
        for row in self.capillas_tree.get_children():
            self.capillas_tree.delete(row)
        
        capillas = ReporteService.ocupacion_capillas()
        
        for c in capillas:
            self.capillas_tree.insert("", "end", values=(
                c['capilla'],
                c['capacidad'],
                c['contratos_proximos'],
                c['detalles'][:100] if len(c['detalles']) > 100 else c['detalles']
            ))
    
    def exportar_capillas_excel(self):
        capillas = ReporteService.ocupacion_capillas()
        ruta = ReporteService.exportar_a_excel(capillas, "ocupacion_capillas")
        if ruta:
            mb.showinfo("Exportación Exitosa", f"Archivo guardado en:\n{ruta}")
    
    def crear_tab_resumen(self, parent):
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="🔍 Actualizar", command=self.cargar_resumen_general,
                     fg_color=self.C_BLUE).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📄 Exportar a PDF", command=self.exportar_resumen_pdf,
                     fg_color="#D97706", hover_color="#B45309", text_color="white").pack(side="left", padx=5)
        
        # Frame para tarjetas de resumen
        cards_frame = ctk.CTkFrame(parent, fg_color="transparent")
        cards_frame.pack(fill="x", padx=10, pady=10)
        
        # Primera fila de tarjetas
        self.kpi_familias = self._crear_kpi_resumen(cards_frame, "👨‍👩‍👧 Familias", "0", self.C_BLUE, 0)
        self.kpi_difuntos = self._crear_kpi_resumen(cards_frame, "⚰️ Difuntos", "0", self.C_GRAY, 1)
        self.kpi_productos = self._crear_kpi_resumen(cards_frame, "📦 Productos", "0", self.C_ORANGE, 2)
        self.kpi_inventario = self._crear_kpi_resumen(cards_frame, "💰 Valor Inventario", "$0", self.C_GREEN, 3)
        
        # Segunda fila
        cards_frame2 = ctk.CTkFrame(parent, fg_color="transparent")
        cards_frame2.pack(fill="x", padx=10, pady=10)
        self.kpi_capillas_disp = self._crear_kpi_resumen(cards_frame2, "🏛️ Capillas Disponibles", "0/0", self.C_GOLD, 0)
        
        # Tabla de contratos por estado
        ctk.CTkLabel(parent, text="Contratos por Estado", font=("Segoe UI", 14, "bold"),
                    text_color=self.C_GOLD).pack(anchor="w", padx=15, pady=(10,5))
        
        columns = ("estado", "cantidad", "monto_total", "pagado", "pendiente")
        self.resumen_tree = ttk.Treeview(parent, columns=columns, show="headings", height=5)
        self.resumen_tree.heading("estado", text="Estado")
        self.resumen_tree.heading("cantidad", text="Cantidad")
        self.resumen_tree.heading("monto_total", text="Monto Total")
        self.resumen_tree.heading("pagado", text="Pagado")
        self.resumen_tree.heading("pendiente", text="Pendiente")
        
        for col in columns:
            self.resumen_tree.column(col, width=120)
        
        self.resumen_tree.pack(fill="x", padx=15, pady=5)
        
        aplicar_estilo_treeview()
        self.cargar_resumen_general()
    
    def _crear_kpi_resumen(self, parent, titulo, valor, color, col):
        card = ctk.CTkFrame(parent, fg_color=color, corner_radius=12, width=180, height=80)
        card.grid(row=0, column=col, padx=10, pady=5, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        
        ctk.CTkLabel(card, text=titulo, font=("Segoe UI", 10, "bold"), 
                    text_color="white").pack(pady=(8,0))
        lbl = ctk.CTkLabel(card, text=valor, font=("Segoe UI", 16, "bold"), 
                          text_color="white")
        lbl.pack(pady=5)
        return lbl
    
    def cargar_resumen_general(self):
        resumen = ReporteService.resumen_general()
        
        self.kpi_familias.configure(text=str(resumen['total_familias']))
        self.kpi_difuntos.configure(text=str(resumen['total_difuntos']))
        self.kpi_productos.configure(text=str(resumen['total_productos']))
        self.kpi_inventario.configure(text=f"${resumen['valor_inventario']:,.2f}")
        self.kpi_capillas_disp.configure(text=f"{resumen['capillas_disponibles']}/{resumen['total_capillas']}")
        
        # Limpiar tabla
        for row in self.resumen_tree.get_children():
            self.resumen_tree.delete(row)
        
        # Cargar contratos por estado
        for estado, datos in resumen['contratos_por_estado'].items():
            self.resumen_tree.insert("", "end", values=(
                estado,
                datos['cantidad'],
                f"${datos['monto_total']:,.2f}",
                f"${datos['monto_pagado']:,.2f}",
                f"${datos['monto_pendiente']:,.2f}"
            ))

    def exportar_resumen_pdf(self):
        resumen = ReporteService.resumen_general()
        columnas = ["Estado de Contrato", "Cantidad", "Monto Total", "Monto Pagado", "Monto Pendiente"]
        filas = []
        for estado, datos in resumen['contratos_por_estado'].items():
            filas.append([
                estado,
                str(datos['cantidad']),
                f"${datos['monto_total']:,.2f}",
                f"${datos['monto_pagado']:,.2f}",
                f"${datos['monto_pendiente']:,.2f}"
            ])
        ruta = ReporteService.exportar_a_pdf("Resumen General de Operaciones y Contratos", columnas, filas, "reporte_resumen_general")
        if ruta and os.path.exists(ruta):
            self._mostrar_pdf_generado(ruta, "PDF Generado", "Reporte PDF guardado en:")
        else:
            mb.showerror("Error", "No se pudo generar el PDF del reporte.")