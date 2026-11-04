# ui/dashboard_frame.py - Panel de control ejecutivo y operacional en tiempo real
import customtkinter as ctk
from tkinter import ttk
import datetime
from services.db_service import obtener_conexion, CapillaRepository
from utils.helpers import aplicar_estilo_treeview, formatear_moneda

class DashboardFrame(ctk.CTkFrame):
    """
    Panel de Control Ejecutivo y Operacional:
    - Indicadores clave de rendimiento (KPIs) con micro-métricas.
    - Barra de acceso rápido a operaciones frecuentes.
    - Monitor en tiempo real de servicios funerarios y velaciones activas.
    - Radar visual de ocupación de capillas y alertas operativas.
    """

    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.parent = parent
        self.usuario = usuario
        self.app = getattr(parent, 'app', parent)
        self.crear_interfaz()
        self.actualizar_datos()

    def crear_interfaz(self):
        # Contenedor principal con scroll suave
        scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=20, pady=15)

        # 1. ENCABEZADO EJECUTIVO
        header_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Panel de Control Ejecutivo",
            font=("Segoe UI", 26, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w")

        self.subtitulo_label = ctk.CTkLabel(
            title_box,
            text=f"Bienvenido, {self.usuario[2]}  •  Servicios Memoriales Altagracia  •  Resumen Operacional",
            font=("Segoe UI", 12),
            text_color="#9da3ae"
        )
        self.subtitulo_label.pack(anchor="w", pady=(2, 0))

        # Botón de actualización manual y timestamp
        refresh_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        refresh_box.pack(side="right")

        self.last_update_label = ctk.CTkLabel(
            refresh_box,
            text="Última actualización: --:--:--",
            font=("Segoe UI", 10),
            text_color="#7f8c8d"
        )
        self.last_update_label.pack(side="top", pady=(0, 4))

        ctk.CTkButton(
            refresh_box,
            text="🔄 Actualizar Datos",
            command=self.actualizar_datos,
            fg_color="#2c3e50",
            hover_color="#34495e",
            font=("Segoe UI", 11, "bold"),
            height=32,
            width=140
        ).pack(side="top")

        # 2. TARJETAS DE INDICADORES CLAVE (KPIs)
        kpi_grid = ctk.CTkFrame(scroll_container, fg_color="transparent")
        kpi_grid.pack(fill="x", pady=(0, 15))
        for col in range(4):
            kpi_grid.grid_columnconfigure(col, weight=1)

        self.cards = {}
        kpi_configs = [
            ("📄", "Contratos Activos", "0", "Cargando...", "#2ecc71", ("#E8F8F0", "#143625"), "contratos"),
            ("💰", "Ingresos del Mes", "$0.00", "0 pagos registrados", "#d4af37", ("#FEF9E7", "#3a3015"), "ingresos"),
            ("🏛️", "Capillas", "0/0", "0 disponibles", "#3498db", ("#EBF5FB", "#152a3a"), "capillas"),
            ("📦", "Inventario Crítico", "0", "Bajo stock mínimo", "#e74c3c", ("#FDEDEC", "#3a181a"), "inventario")
        ]

        for idx, (icon, title, val_def, sub_def, accent_col, bg_col, key) in enumerate(kpi_configs):
            card = ctk.CTkFrame(kpi_grid, fg_color=("#FFFFFF", "#1e222b"), corner_radius=12, border_width=1, border_color=("#E2E8F0", "#2a303c"))
            card.grid(row=0, column=idx, padx=6, pady=4, sticky="nsew")

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=14, pady=(12, 0))

            icon_box = ctk.CTkFrame(top_row, width=42, height=42, corner_radius=10, fg_color=bg_col)
            icon_box.pack(side="left")
            icon_box.pack_propagate(False)
            ctk.CTkLabel(icon_box, text=icon, font=("Segoe UI", 18)).pack(expand=True)

            ctk.CTkLabel(top_row, text=title, font=("Segoe UI", 12, "bold"), text_color=("#475569", "#bdc3c7")).pack(side="left", padx=10)

            val_lbl = ctk.CTkLabel(card, text=val_def, font=("Segoe UI", 26, "bold"), text_color=accent_col)
            val_lbl.pack(anchor="w", padx=14, pady=(8, 0))

            sub_lbl = ctk.CTkLabel(card, text=sub_def, font=("Segoe UI", 10), text_color=("#64748B", "#7f8c8d"))
            sub_lbl.pack(anchor="w", padx=14, pady=(2, 12))

            self.cards[key] = {
                "valor": val_lbl,
                "sub": sub_lbl
            }

        # 3. BARRA DE ACCIONES RÁPIDAS
        actions_card = ctk.CTkFrame(scroll_container, fg_color=("#F8FAFC", "#181b22"), corner_radius=12, border_width=1, border_color=("#E2E8F0", "#262c37"))
        actions_card.pack(fill="x", pady=(0, 20), padx=2)

        ctk.CTkLabel(
            actions_card,
            text="⚡ Accesos Rápidos Operacionales:",
            font=("Segoe UI", 12, "bold"),
            text_color="#d4af37"
        ).pack(side="left", padx=(16, 12), pady=12)

        quick_buttons = [
            ("➕ Nuevo Contrato", self.ir_a_contratos, "#d4af37", "black"),
            ("👥 Registrar Familia", self.ir_a_clientes, "#34495e", "white"),
            ("🏛️ Gestionar Capillas", self.ir_a_capillas, "#34495e", "white"),
            ("💰 Cobros y Pagos", self.ir_a_pagos, "#27ae60", "white"),
            ("📦 Ver Inventario", self.ir_a_inventario, "#34495e", "white"),
        ]

        for txt, cmd, bg_c, fg_c in quick_buttons:
            ctk.CTkButton(
                actions_card,
                text=txt,
                command=cmd,
                fg_color=bg_c,
                text_color=fg_c,
                hover_color="#506173" if bg_c == "#34495e" else ("#b8960c" if bg_c == "#d4af37" else "#219653"),
                font=("Segoe UI", 11, "bold"),
                height=32,
                corner_radius=8
            ).pack(side="left", padx=5, pady=8)

        # 4. MONITOR OPERACIONAL DIVIDIDO EN 2 PANELES
        monitor_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        monitor_frame.pack(fill="both", expand=True)
        monitor_frame.grid_columnconfigure(0, weight=6)
        monitor_frame.grid_columnconfigure(1, weight=4)
        monitor_frame.grid_rowconfigure(0, weight=1)

        # PANEL IZQUIERDO: Servicios Activos y Velaciones
        tabla_card = ctk.CTkFrame(monitor_frame, fg_color=("#FFFFFF", "#1e222b"), corner_radius=12, border_width=1, border_color=("#E2E8F0", "#2a303c"))
        tabla_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        t_header = ctk.CTkFrame(tabla_card, fg_color="transparent")
        t_header.pack(fill="x", padx=15, pady=(15, 8))

        ctk.CTkLabel(
            t_header,
            text="🕊️ Servicios Funerarios en Curso y Recientes",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(side="left")

        ctk.CTkButton(
            t_header,
            text="Ver Todos en Contratos",
            command=self.ir_a_contratos,
            fg_color="transparent",
            text_color=("#1D4ED8", "#3498db"),
            hover_color=("#F1F5F9", "#252b36"),
            font=("Segoe UI", 11, "underline"),
            width=160
        ).pack(side="right")

        cols = ("numero", "tipo", "difunto", "capilla", "fecha", "estado")
        self.servicios_tree = ttk.Treeview(tabla_card, columns=cols, show="headings", height=8)
        self.servicios_tree.heading("numero", text="N° Contrato")
        self.servicios_tree.heading("tipo", text="Tipo")
        self.servicios_tree.heading("difunto", text="Difunto / Titular")
        self.servicios_tree.heading("capilla", text="Capilla")
        self.servicios_tree.heading("fecha", text="Fecha Velación")
        self.servicios_tree.heading("estado", text="Estado Servicio")

        self.servicios_tree.column("numero", width=110)
        self.servicios_tree.column("tipo", width=85, anchor="center")
        self.servicios_tree.column("difunto", width=160)
        self.servicios_tree.column("capilla", width=120)
        self.servicios_tree.column("fecha", width=100, anchor="center")
        self.servicios_tree.column("estado", width=110, anchor="center")

        tree_scroll = ttk.Scrollbar(tabla_card, orient="vertical", command=self.servicios_tree.yview)
        self.servicios_tree.configure(yscrollcommand=tree_scroll.set)
        self.servicios_tree.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=(0, 15))
        tree_scroll.pack(side="right", fill="y", padx=(0, 15), pady=(0, 15))

        # PANEL DERECHO: Radar de Capillas y Alertas
        radar_card = ctk.CTkFrame(monitor_frame, fg_color=("#FFFFFF", "#1e222b"), corner_radius=12, border_width=1, border_color=("#E2E8F0", "#2a303c"))
        radar_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        r_header = ctk.CTkFrame(radar_card, fg_color="transparent")
        r_header.pack(fill="x", padx=15, pady=(15, 8))

        ctk.CTkLabel(
            r_header,
            text="🏛️ Radar de Capillas en Tiempo Real",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(side="left")

        # Contenedor de fichas de capillas
        self.capillas_container = ctk.CTkFrame(radar_card, fg_color="transparent")
        self.capillas_container.pack(fill="both", expand=True, padx=15, pady=5)

        # Sección de Alertas Financieras / Stock
        self.alertas_box = ctk.CTkFrame(radar_card, fg_color=("#F1F5F9", "#252a36"), corner_radius=8)
        self.alertas_box.pack(fill="x", padx=15, pady=(5, 15))

        self.alertas_label = ctk.CTkLabel(
            self.alertas_box,
            text="🔔 Cargando alertas del sistema...",
            font=("Segoe UI", 10),
            text_color=("#334155", "#bdc3c7"),
            wraplength=320,
            justify="left"
        )
        self.alertas_label.pack(padx=12, pady=10, anchor="w")

        aplicar_estilo_treeview()

    # ========== MÉTODOS DE NAVEGACIÓN RÁPIDA ==========
    def ir_a_contratos(self):
        from ui.contratos_frame import ContratosFrame
        self._navegar(ContratosFrame)

    def ir_a_clientes(self):
        from ui.clientes_frame import ClientesFrame
        self._navegar(ClientesFrame)

    def ir_a_capillas(self):
        from ui.capillas_frame import CapillasFrame
        self._navegar(CapillasFrame)

    def ir_a_pagos(self):
        from ui.pagos_frame import PagosFrame
        self._navegar(PagosFrame)

    def ir_a_inventario(self):
        from ui.inventario_frame import InventarioFrame
        self._navegar(InventarioFrame)

    def _navegar(self, clase_frame):
        # Buscar el App o Toplevel padre que tiene el método mostrar_frame
        curr = self.master
        while curr:
            if hasattr(curr, 'mostrar_frame'):
                curr.mostrar_frame(clase_frame)
                return
            curr = getattr(curr, 'master', None)

    # ========== ACTUALIZACIÓN DE DATOS ==========
    def actualizar_datos(self):
        ahora = datetime.datetime.now()
        self.last_update_label.configure(text=f"Última actualización: {ahora.strftime('%H:%M:%S')}")

        conn = obtener_conexion()
        c = conn.cursor()

        # 1. Contratos Activos (desglose Inmediatos vs Largo Plazo)
        c.execute("""
            SELECT 
                COUNT(*),
                COALESCE(SUM(CASE WHEN tipo_contrato = 'Largo Plazo' THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN tipo_contrato != 'Largo Plazo' OR tipo_contrato IS NULL THEN 1 ELSE 0 END), 0)
            FROM contratos WHERE estado = 'Activo'
        """)
        row_c = c.fetchone()
        tot_activos = row_c[0] if row_c else 0
        lp_activos = row_c[1] if row_c else 0
        inm_activos = row_c[2] if row_c else 0

        self.cards["contratos"]["valor"].configure(text=str(tot_activos))
        self.cards["contratos"]["sub"].configure(text=f"{inm_activos} Inmediatos • {lp_activos} Largo Plazo")

        # 2. Ingresos del Mes y total cobros
        mes_actual = ahora.strftime("%Y-%m")
        c.execute("SELECT COALESCE(SUM(monto), 0), COUNT(*) FROM pagos WHERE fecha LIKE ? || '%'", (mes_actual,))
        row_p = c.fetchone()
        ingresos_mes = row_p[0] if row_p else 0.0
        num_pagos_mes = row_p[1] if row_p else 0

        self.cards["ingresos"]["valor"].configure(text=formatear_moneda(ingresos_mes))
        self.cards["ingresos"]["sub"].configure(text=f"{num_pagos_mes} pago(s) en {ahora.strftime('%B %Y')}")

        # 3. Capillas (Disponibles / Ocupadas)
        c.execute("""
            SELECT 
                COUNT(*),
                COALESCE(SUM(CASE WHEN estado = 'Disponible' THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN estado = 'Ocupada' THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN estado = 'Mantenimiento' THEN 1 ELSE 0 END), 0)
            FROM capillas WHERE activo = 1
        """)
        row_cap = c.fetchone()
        tot_cap = row_cap[0] if row_cap else 0
        disp_cap = row_cap[1] if row_cap else 0
        ocup_cap = row_cap[2] if row_cap else 0

        self.cards["capillas"]["valor"].configure(text=f"{disp_cap}/{tot_cap}")
        self.cards["capillas"]["sub"].configure(text=f"{ocup_cap} Ocupada(s) • {disp_cap} Libre(s)")

        # 4. Stock Bajo
        c.execute("SELECT COUNT(*) FROM inventario WHERE stock <= stock_minimo")
        stock_critico = c.fetchone()[0] or 0
        self.cards["inventario"]["valor"].configure(text=str(stock_critico))
        if stock_critico > 0:
            self.cards["inventario"]["sub"].configure(text="⚠️ Requiere reposición urgente", text_color="#e74c3c")
        else:
            self.cards["inventario"]["sub"].configure(text="✓ Niveles de inventario óptimos", text_color="#2ecc71")

        # 5. Llenar tabla de Servicios Activos
        for item in self.servicios_tree.get_children():
            self.servicios_tree.delete(item)

        c.execute("""
            SELECT c.numero, COALESCE(c.tipo_contrato, 'Inmediato'),
                   COALESCE(d.nombre || ' ' || d.apellido, f.resp_nombre || ' ' || f.resp_apellido || ' (Titular)'),
                   COALESCE(cap.nombre, 'Sin Capilla'),
                   COALESCE(c.fecha_velacion, 'N/E'),
                   COALESCE(c.estado_servicio, 'Pendiente')
            FROM contratos c
            LEFT JOIN difuntos d ON c.difunto_id = d.id
            LEFT JOIN familias f ON c.familia_id = f.familia_id
            LEFT JOIN capillas cap ON c.capilla_id = cap.id
            WHERE c.estado = 'Activo'
            ORDER BY c.id DESC
            LIMIT 15
        """)
        for s_row in c.fetchall():
            self.servicios_tree.insert("", "end", values=(
                s_row[0], s_row[1], s_row[2], s_row[3], s_row[4], s_row[5]
            ))

        # 6. Actualizar Fichas de Capillas en Radar
        for widget in self.capillas_container.winfo_children():
            widget.destroy()

        capillas = CapillaRepository.obtener_todas()
        for cap in capillas:
            f_cap = ctk.CTkFrame(self.capillas_container, fg_color=("#F8FAFC", "#181c24"), corner_radius=8, border_width=1, border_color=("#E2E8F0", "#2a303d"))
            f_cap.pack(fill="x", pady=4)

            badge_col = "#2ecc71" if cap['estado'] == "Disponible" else ("#e74c3c" if cap['estado'] == "Ocupada" else "#f39c12")
            badge_icon = "🟢" if cap['estado'] == "Disponible" else ("🔴" if cap['estado'] == "Ocupada" else "🟡")

            left_box = ctk.CTkFrame(f_cap, fg_color="transparent")
            left_box.pack(side="left", padx=10, pady=8)

            ctk.CTkLabel(left_box, text=cap['nombre'], font=("Segoe UI", 12, "bold")).pack(anchor="w")
            ctk.CTkLabel(left_box, text=f"Capacidad: {cap['capacidad']} personas  •  {cap['descripcion'] or 'Equipada'}", font=("Segoe UI", 9), text_color=("#64748B", "#7f8c8d")).pack(anchor="w")

            status_pill = ctk.CTkFrame(f_cap, fg_color=("#EDF2F7", "#12151b"), corner_radius=12)
            status_pill.pack(side="right", padx=10, pady=8)
            ctk.CTkLabel(status_pill, text=f"{badge_icon} {cap['estado']}", font=("Segoe UI", 10, "bold"), text_color=badge_col).pack(padx=8, pady=3)

        # 7. Cuotas pendientes y alertas operativas
        c.execute("""
            SELECT COUNT(*), COALESCE(SUM(monto), 0)
            FROM cuotas 
            WHERE estado = 'Pendiente' AND fecha_vencimiento < ?
        """, (ahora.strftime("%Y-%m-%d"),))
        row_venc = c.fetchone()
        cuotas_vencidas = row_venc[0] if row_venc else 0
        monto_vencido = row_venc[1] if row_venc else 0.0

        alertas_txt = []
        if cuotas_vencidas > 0:
            alertas_txt.append(f"⚠️ {cuotas_vencidas} cuota(s) vencida(s) pendientes de cobro ({formatear_moneda(monto_vencido)}).")
        if stock_critico > 0:
            alertas_txt.append(f"📦 {stock_critico} producto(s) en inventario alcanzaron nivel crítico.")
        if not alertas_txt:
            alertas_txt.append("✓ Sin alertas críticas: Sistema funcionando con normalidad.")

        self.alertas_label.configure(text="\n".join(alertas_txt))

        conn.close()

        # Auto-refrescar cada 45 segundos
        self.after(45000, self.actualizar_datos)