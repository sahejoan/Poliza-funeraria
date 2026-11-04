# ui/contratos_frame.py - Gestión Integral de Contratos (Inmediatos, Largo Plazo, PNF, Capillas y Costos)
import customtkinter as ctk
import tkinter.messagebox as mb
from tkinter import ttk
import datetime
import sqlite3
import random
import os

from services.db_service import (
    obtener_conexion, PAQUETES, ContratoRepository, CapillaRepository
)
from services.contrato_service import ContratoService
from services.cliente_service import ClienteService
from services.servicio_adicional_service import ServicioAdicionalService
from services.precio_service import (
    PrecioService, COSTO_CREMACION, COSTOS_TRASLADO, DesglosePrecio
)
from utils.helpers import (
    aplicar_estilo_treeview, obtener_fecha_actual, obtener_hora_actual,
    mostrar_dialogo_verificar_total, calcular_edad
)


class ContratosFrame(ctk.CTkFrame):
    """
    Gestión completa de Contratos:
    - Modalidades: Inmediato vs. Largo Plazo (Previsión a futuro).
    - Asociación a PNF (Plan Nacional Funerario) con cobertura de traslado y cremación.
    - Verificación matemática de costos y desglose detallado.
    - Edición directa de hora de llegada y salida del difunto.
    - Reasignación de capillas de velación.
    """

    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.contrato_actual = None
        self.productos_agregados = []
        self.servicios_agregados = []
        self.beneficiarios_pnf = []
        self.pnf_contrato_edit_id = None
        self.pnf_contratos_dict = {}
        self.difunto_dict = {}
        self.familia_dict = {}
        self.capilla_dict = {}
        self.producto_dict = {}
        self.familia_id_actual = None
        self.difunto_id_actual = None
        self.tipo_velacion_actual = "Funeraria"
        self.servicio_keys = []
        self.desglose_actual = None

        self.crear_interfaz()
        self.cargar_contratos()

    def crear_interfaz(self):
        # Título principal
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(
            header,
            text="Gestión de Contratos",
            font=("Segoe UI", 26, "bold"),
            text_color="#d4af37"
        ).pack(side="left")

        # Tabview principal para organizar la gestión de contratos
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=5)

        tab_pnf = self.tabview.add("🛡️ Plan Nacional Funerario (PNF)")
        tab_inmediato = self.tabview.add("⚡ Servicio Inmediato (Capilla)")
        tab_registrados = self.tabview.add("📋 Contratos Registrados")

        # Tab 1: PNF Organizado (1° Titular +18, 2° Beneficiarios 8-15, 3° Plan y Costo, 4° Cancelación, 5° Generar PNF)
        self.crear_formulario_pnf(tab_pnf)

        # Tab 2: Formulario tradicional de Servicio Funerario Inmediato
        self.crear_formulario_inmediato(tab_inmediato)

        # Tab 3: Tabla de Contratos Registrados y acciones
        self.crear_tabla_contratos(tab_registrados)

        aplicar_estilo_treeview()
        self.toggle_financiamiento()
        self.cargar_difuntos_combo()
        self.cargar_capillas()
        self.cargar_productos_combo()
        self.cambiar_tipo_velacion()
        self.actualizar_total()
        self.actualizar_calculo_pnf()

    def crear_formulario_inmediato(self, parent):
        # Contenedor con scroll para creación de contratos inmediatos
        main_frame = ctk.CTkScrollableFrame(parent, height=480)
        main_frame.pack(pady=5, padx=10, fill="both", expand=True)

        # ========== SECCIÓN: MODALIDAD DE CONTRATO (INMEDIATO vs LARGO PLAZO) ==========
        mod_frame = ctk.CTkFrame(main_frame, fg_color=("#F1F5F9", "#1E2229"), border_width=1, border_color=("#CBD5E1", "#2C3444"), corner_radius=8)
        mod_frame.pack(fill="x", pady=8, padx=5)

        ctk.CTkLabel(
            mod_frame,
            text="TIPO / MODALIDAD DE CONTRATO:",

            font=("Segoe UI", 13, "bold"),
            text_color="#d4af37"
        ).pack(side="left", padx=15, pady=10)

        self.tipo_contrato_var = ctk.StringVar(value="Inmediato")
        rb_inm = ctk.CTkRadioButton(
            mod_frame,
            text="⚡ Servicio Inmediato (Fallecimiento actual)",
            variable=self.tipo_contrato_var,
            value="Inmediato",
            command=self.on_cambio_tipo_contrato,
            font=("Segoe UI", 12, "bold")
        )
        rb_inm.pack(side="left", padx=15)

        rb_lp = ctk.CTkRadioButton(
            mod_frame,
            text="🛡️ Plan a Largo Plazo (Previsión a futuro)",
            variable=self.tipo_contrato_var,
            value="Largo Plazo",
            command=self.on_cambio_tipo_contrato,
            font=("Segoe UI", 12, "bold")
        )
        rb_lp.pack(side="left", padx=15)

        self.tipo_contrato_desc = ctk.CTkLabel(
            mod_frame,
            text="Requiere seleccionar el difunto fallecido y la capilla.",
            font=("Segoe UI", 11, "italic"),
            text_color="gray"
        )
        self.tipo_contrato_desc.pack(side="left", padx=15)

        # ========== SECCIÓN: SELECCIÓN DE DIFUNTO / RESPONSABLE ==========
        self.sec_difunto_label = ctk.CTkLabel(
            main_frame,
            text="DATOS DEL DIFUNTO Y FAMILIAR RESPONSABLE",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        )
        self.sec_difunto_label.pack(anchor="w", pady=(10, 5))

        dif_frame = ctk.CTkFrame(main_frame)
        dif_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(dif_frame, text="Buscar Difunto (Cédula o Nombre):").pack(side="left", padx=5)
        self.buscar_difunto_entry = ctk.CTkEntry(dif_frame, width=240, placeholder_text="Buscar cédula...")
        self.buscar_difunto_entry.pack(side="left", padx=5)
        self.buscar_difunto_entry.bind("<Return>", lambda e: self.buscar_difunto())

        ctk.CTkButton(
            dif_frame,
            text="🔍 Buscar",
            command=self.buscar_difunto,
            fg_color="#3498db",
            width=90
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            dif_frame,
            text="↻ Todos los Difuntos",
            command=self.cargar_difuntos_combo,
            fg_color="gray",
            width=140
        ).pack(side="left", padx=5)

        self.difunto_combo_label = ctk.CTkLabel(main_frame, text="Seleccionar Difunto Registrado:")
        self.difunto_combo_label.pack(anchor="w", pady=(6, 0))

        self.difunto_combo = ctk.CTkComboBox(
            main_frame,
            width=500,
            state="readonly",
            values=["-- Cargando... --"],
            command=self.on_difunto_seleccionado
        )
        self.difunto_combo.pack(anchor="w", pady=4)

        # Combo alternativo para planes a largo plazo (seleccionar familia/titular)
        self.familia_lp_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        ctk.CTkLabel(self.familia_lp_frame, text="Seleccionar Titular / Familiar Contratante (Largo Plazo):").pack(anchor="w")
        self.familia_combo = ctk.CTkComboBox(
            self.familia_lp_frame,
            width=500,
            state="readonly",
            values=["-- Cargando... --"],
            command=self.on_familia_lp_seleccionada
        )
        self.familia_combo.pack(anchor="w", pady=4)

        self.responsable_info_label = ctk.CTkLabel(main_frame, text="", font=("Segoe UI", 11, "bold"))
        self.responsable_info_label.pack(anchor="w", pady=3)

        # Panel de reflejo de Carga Familiar cuando se selecciona un contrato o familia con PNF / Largo Plazo
        self.carga_familiar_inm_frame = ctk.CTkFrame(
            main_frame,
            fg_color=("#F8FAFC", "#141B24"),
            border_width=1,
            border_color=("#CBD5E1", "#2D3748"),
            corner_radius=8
        )
        self.carga_familiar_inm_lbl = ctk.CTkLabel(
            self.carga_familiar_inm_frame,
            text="",
            font=("Segoe UI", 11),
            justify="left",
            anchor="w"
        )
        self.carga_familiar_inm_lbl.pack(side="left", padx=12, pady=8, fill="x", expand=True)
        ctk.CTkButton(
            self.carga_familiar_inm_frame,
            text="👨‍👩‍👧‍👦 Ver / Editar Carga Familiar en PNF",
            command=self.ir_a_carga_familiar_pnf,
            fg_color="#d4af37",
            text_color="black",
            font=("Segoe UI", 11, "bold"),
            width=230,
            height=30
        ).pack(side="right", padx=10, pady=6)

        # ========== SECCIÓN: ASOCIACIÓN A PNF (Plan Nacional Funerario) ==========
        pnf_card = ctk.CTkFrame(main_frame, fg_color=("#F0FDF4", "#1C2430"), border_width=1, border_color=("#BBF7D0", "#2E3B4E"), corner_radius=8)
        pnf_card.pack(fill="x", pady=10, padx=2)

        pnf_header = ctk.CTkFrame(pnf_card, fg_color="transparent")
        pnf_header.pack(fill="x", padx=12, pady=(10, 5))

        self.pnf_var = ctk.BooleanVar(value=False)
        self.pnf_check = ctk.CTkCheckBox(
            pnf_header,
            text="Asociar a PNF (Plan Nacional Funerario)",
            variable=self.pnf_var,
            command=self.toggle_pnf_campos,
            font=("Segoe UI", 13, "bold"),
            text_color="#d4af37"
        )
        self.pnf_check.pack(side="left")

        self.pnf_options_frame = ctk.CTkFrame(pnf_card, fg_color="transparent")
        self.pnf_options_frame.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(self.pnf_options_frame, text="N° Afiliación / Certificado PNF:").pack(side="left", padx=5)
        self.pnf_num_entry = ctk.CTkEntry(self.pnf_options_frame, width=160, placeholder_text="PNF-000000")
        self.pnf_num_entry.pack(side="left", padx=5)

        self.pnf_cubre_traslado_var = ctk.BooleanVar(value=False)
        self.pnf_traslado_check = ctk.CTkCheckBox(
            self.pnf_options_frame,
            text="PNF Cubre Traslado (Descuento 100%)",
            variable=self.pnf_cubre_traslado_var,
            command=self.actualizar_total
        )
        self.pnf_traslado_check.pack(side="left", padx=15)

        self.pnf_cubre_cremacion_var = ctk.BooleanVar(value=False)
        self.pnf_cremacion_check = ctk.CTkCheckBox(
            self.pnf_options_frame,
            text="PNF Cubre Cremación (Descuento 100%)",
            variable=self.pnf_cubre_cremacion_var,
            command=self.actualizar_total
        )
        self.pnf_cremacion_check.pack(side="left", padx=15)

        # Estado inicial de PNF (se activará al finalizar de construir los controles)

        # ========== SECCIÓN: SERVICIOS ESPECIALES (CREMACIÓN Y TRASLADOS) ==========
        ctk.CTkLabel(
            main_frame,
            text="SERVICIOS ESPECIALES",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", pady=(10, 4))

        servicios_frame = ctk.CTkFrame(main_frame)
        servicios_frame.pack(fill="x", pady=4)

        self.cremacion_var = ctk.BooleanVar(value=False)
        self.cremacion_check = ctk.CTkCheckBox(
            servicios_frame,
            text="Requiere Cremación (+$250.00)",
            variable=self.cremacion_var,
            command=self.actualizar_total
        )
        self.cremacion_check.pack(side="left", padx=15, pady=8)

        ctk.CTkLabel(servicios_frame, text="Tipo de Traslado:", width=120, anchor="w").pack(side="left", padx=5)
        self.traslado_combo = ctk.CTkComboBox(
            servicios_frame,
            values=["Local ($0.00)", "Regional (+$300.00)", "Nacional (+$800.00)", "Externo ($0.00)"],
            width=220,
            state="readonly",
            command=lambda v: self.actualizar_total()
        )
        self.traslado_combo.set("Local ($0.00)")
        self.traslado_combo.pack(side="left", padx=10)

        # ========== SECCIÓN: CAPILLA DE VELACIÓN ==========
        self.sec_capilla_label = ctk.CTkLabel(
            main_frame,
            text="CAPILLA DE VELACIÓN",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        )
        self.sec_capilla_label.pack(anchor="w", pady=(10, 4))

        capilla_frame = ctk.CTkFrame(main_frame)
        capilla_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(capilla_frame, text="Seleccionar Capilla:").pack(side="left", padx=10)
        self.capilla_combo = ctk.CTkComboBox(capilla_frame, width=280, state="readonly")
        self.capilla_combo.pack(side="left", padx=10)

        ctk.CTkButton(
            capilla_frame,
            text="🔄 Actualizar Capillas",
            command=self.cargar_capillas,
            fg_color="gray",
            width=140
        ).pack(side="left", padx=10)

        # ========== SECCIÓN: PAQUETE DE VELACIÓN ==========
        ctk.CTkLabel(
            main_frame,
            text="PAQUETE DE VELACIÓN",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", pady=(10, 4))

        paquete_frame = ctk.CTkFrame(main_frame)
        paquete_frame.pack(fill="x", pady=4)

        self.paquete_var = ctk.StringVar(value="BRONCE")
        for paq in ["BRONCE", "PLATA", "ORO"]:
            rb = ctk.CTkRadioButton(
                paquete_frame,
                text=f"{paq} (${PAQUETES[paq]['precio']:,.2f})",
                variable=self.paquete_var,
                value=paq,
                command=self.on_paquete_cambiado,
                font=("Segoe UI", 12, "bold")
            )
            rb.pack(side="left", padx=15, pady=8)

        self.paquete_desc = ctk.CTkLabel(
            main_frame,
            text=PAQUETES["BRONCE"]["descripcion"],
            wraplength=700,
            justify="left",
            text_color="#bdc3c7"
        )
        self.paquete_desc.pack(anchor="w", pady=4, padx=5)

        # ========== SECCIÓN: HORARIOS Y LLEGADA DEL DIFUNTO ==========
        self.sec_horarios_label = ctk.CTkLabel(
            main_frame,
            text="HORARIOS DEL SERVICIO Y LLEGADA DEL DIFUNTO",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        )
        self.sec_horarios_label.pack(anchor="w", pady=(10, 4))

        self.horario_frame = ctk.CTkFrame(main_frame)
        self.horario_frame.pack(fill="x", pady=4)

        self.servicio_inmediato_var = ctk.BooleanVar(value=False)
        inmediato_check = ctk.CTkCheckBox(
            self.horario_frame,
            text="Iniciar Servicio de Inmediato (Hoy)",
            variable=self.servicio_inmediato_var,
            command=self.toggle_horario_inmediato
        )
        inmediato_check.pack(anchor="w", padx=10, pady=5)

        f_row = ctk.CTkFrame(self.horario_frame, fg_color="transparent")
        f_row.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(f_row, text="Fecha Velación (DD/MM/AAAA):").pack(side="left", padx=(0, 5))
        self.fecha_velacion = ctk.CTkEntry(f_row, width=130, placeholder_text="DD/MM/AAAA")
        self.fecha_velacion.insert(0, (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d/%m/%Y"))
        self.fecha_velacion.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(f_row, text="Hora Inicio:").pack(side="left", padx=(0, 5))
        self.hora_planificada = ctk.CTkEntry(f_row, width=80)
        self.hora_planificada.insert(0, "10:00")
        self.hora_planificada.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(f_row, text="Hora Fin:").pack(side="left", padx=(0, 5))
        self.hora_fin = ctk.CTkEntry(f_row, width=80)
        self.hora_fin.insert(0, "22:00")
        self.hora_fin.pack(side="left", padx=(0, 20))

        f_llegada = ctk.CTkFrame(self.horario_frame, fg_color="transparent")
        f_llegada.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(f_llegada, text="⏰ Hora Real Llegada a Funeraria:").pack(side="left", padx=(0, 5))
        self.hora_llegada_real = ctk.CTkEntry(f_llegada, width=90, placeholder_text="Ej: 11:30")
        self.hora_llegada_real.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(f_llegada, text="Hora Salida de Capilla:").pack(side="left", padx=(0, 5))
        self.hora_salida_capilla = ctk.CTkEntry(f_llegada, width=90, placeholder_text="Ej: 16:00")
        self.hora_salida_capilla.pack(side="left", padx=(0, 10))

        # ========== SECCIÓN: PRODUCTOS ADICIONALES ==========
        ctk.CTkLabel(
            main_frame,
            text="PRODUCTOS ADICIONALES",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", pady=(10, 4))

        prod_agregar_frame = ctk.CTkFrame(main_frame)
        prod_agregar_frame.pack(fill="x", pady=4)

        self.producto_combo = ctk.CTkComboBox(prod_agregar_frame, width=280, state="readonly")
        self.producto_combo.pack(side="left", padx=5)

        self.cantidad_producto = ctk.CTkEntry(prod_agregar_frame, width=70, placeholder_text="Cant.")
        self.cantidad_producto.pack(side="left", padx=5)
        self.cantidad_producto.insert(0, "1")

        ctk.CTkButton(
            prod_agregar_frame,
            text="➕ Agregar Producto",
            command=self.agregar_producto,
            fg_color="#2ecc71",
            text_color="black",
            width=140
        ).pack(side="left", padx=5)

        self.productos_tree = ttk.Treeview(main_frame, columns=("producto", "cantidad", "precio", "subtotal"),
                                           show="headings", height=3)
        self.productos_tree.heading("producto", text="Producto")
        self.productos_tree.heading("cantidad", text="Cant.")
        self.productos_tree.heading("precio", text="Precio Unit.")
        self.productos_tree.heading("subtotal", text="Subtotal")
        self.productos_tree.column("producto", width=260)
        self.productos_tree.column("cantidad", width=60, anchor="center")
        self.productos_tree.column("precio", width=100, anchor="e")
        self.productos_tree.column("subtotal", width=100, anchor="e")
        self.productos_tree.pack(fill="x", pady=4)

        # ========== SECCIÓN: SERVICIOS ADICIONALES ==========
        ctk.CTkLabel(
            main_frame,
            text="SERVICIOS ADICIONALES",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", pady=(10, 4))

        self.tipo_velacion_var = ctk.StringVar(value="Funeraria")
        vel_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        vel_frame.pack(fill="x", pady=2)
        ctk.CTkRadioButton(vel_frame, text="Velación en Funeraria", variable=self.tipo_velacion_var,
                          value="Funeraria", command=self.cambiar_tipo_velacion).pack(side="left", padx=10)
        ctk.CTkRadioButton(vel_frame, text="Velación a Domicilio", variable=self.tipo_velacion_var,
                          value="Domicilio", command=self.cambiar_tipo_velacion).pack(side="left", padx=10)

        serv_select_frame = ctk.CTkFrame(main_frame)
        serv_select_frame.pack(fill="x", pady=4)

        self.servicio_combo = ctk.CTkComboBox(serv_select_frame, width=280, state="readonly")
        self.servicio_combo.pack(side="left", padx=5)

        self.servicio_cantidad = ctk.CTkEntry(serv_select_frame, width=60)
        self.servicio_cantidad.insert(0, "1")
        self.servicio_cantidad.pack(side="left", padx=5)

        ctk.CTkButton(
            serv_select_frame,
            text="➕ Agregar Servicio",
            command=self.agregar_servicio,
            fg_color="#2ecc71",
            text_color="black",
            width=140
        ).pack(side="left", padx=5)

        self.servicios_tree = ttk.Treeview(main_frame, columns=("servicio", "cantidad", "precio", "subtotal"),
                                           show="headings", height=3)
        self.servicios_tree.heading("servicio", text="Servicio")
        self.servicios_tree.heading("cantidad", text="Cant.")
        self.servicios_tree.heading("precio", text="Precio Unit.")
        self.servicios_tree.heading("subtotal", text="Subtotal")
        self.servicios_tree.column("servicio", width=260)
        self.servicios_tree.column("cantidad", width=60, anchor="center")
        self.servicios_tree.column("precio", width=100, anchor="e")
        self.servicios_tree.column("subtotal", width=100, anchor="e")
        self.servicios_tree.pack(fill="x", pady=4)

        # ========== SECCIÓN: FINANCIAMIENTO & TOTAL ==========
        ctk.CTkLabel(
            main_frame,
            text="CONDICIONES DE PAGO Y DESGLOSE",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", pady=(10, 4))

        pago_frame = ctk.CTkFrame(main_frame)
        pago_frame.pack(fill="x", pady=4)

        self.metodo_var = ctk.StringVar(value="Contado")
        ctk.CTkRadioButton(pago_frame, text="Contado", variable=self.metodo_var,
                          value="Contado", command=self.toggle_financiamiento).pack(side="left", padx=15)
        ctk.CTkRadioButton(pago_frame, text="Financiado (Cuotas)", variable=self.metodo_var,
                          value="Financiado", command=self.toggle_financiamiento).pack(side="left", padx=15)

        self.financiamiento_frame = ctk.CTkFrame(pago_frame, fg_color="transparent")
        self.financiamiento_frame.pack(side="left", padx=15)

        ctk.CTkLabel(self.financiamiento_frame, text="Inicial ($):").pack(side="left", padx=5)
        self.inicial_entry = ctk.CTkEntry(self.financiamiento_frame, width=90)
        self.inicial_entry.pack(side="left", padx=5)

        ctk.CTkLabel(self.financiamiento_frame, text="N° Cuotas:").pack(side="left", padx=5)
        self.cuotas_entry = ctk.CTkEntry(self.financiamiento_frame, width=70)
        self.cuotas_entry.pack(side="left", padx=5)

        # Total Card con Botón de Verificación
        total_card = ctk.CTkFrame(main_frame, fg_color=("#F8FAFC", "#1A252F"), border_width=1, border_color=("#CBD5E1", "#2A3644"), corner_radius=8)
        total_card.pack(fill="x", pady=10)

        ctk.CTkLabel(
            total_card,
            text="TOTAL FINAL A PAGAR:",
            font=("Segoe UI", 15, "bold")
        ).pack(side="left", padx=15, pady=12)

        self.total_label = ctk.CTkLabel(
            total_card,
            text="$0.00",
            font=("Segoe UI", 22, "bold"),
            text_color="#d4af37"
        )
        self.total_label.pack(side="left", padx=10)

        ctk.CTkButton(
            total_card,
            text="🔍 Verificar Total y Costo",
            command=self.verificar_total_en_creacion,
            fg_color="#3498db",
            font=("Segoe UI", 12, "bold"),
            height=34,
            width=180
        ).pack(side="right", padx=15)

        ctk.CTkLabel(main_frame, text="OBSERVACIONES:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
        self.observaciones = ctk.CTkTextbox(main_frame, height=50, width=700)
        self.observaciones.pack(fill="x", pady=4)

        ctk.CTkButton(
            main_frame,
            text="📝 CREAR Y REGISTRAR CONTRATO",
            command=self.crear_contrato,
            fg_color="#d4af37",
            text_color="black",
            height=46,
            font=("Segoe UI", 14, "bold")
        ).pack(pady=15)

    def crear_tabla_contratos(self, parent):
        table_container = ctk.CTkFrame(parent)
        table_container.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(
            table_container,
            text="Contratos Registrados en el Sistema",
            font=("Segoe UI", 18, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", padx=10, pady=(10, 4))

        table_frame = ctk.CTkFrame(table_container)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("id", "numero", "tipo", "difunto", "responsable", "carga", "paquete", "pnf", "total", "estado")
        self.contratos_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)
        self.contratos_tree.heading("id", text="ID")
        self.contratos_tree.heading("numero", text="N° Contrato")
        self.contratos_tree.heading("tipo", text="Tipo")
        self.contratos_tree.heading("difunto", text="Difunto")
        self.contratos_tree.heading("responsable", text="Responsable / Titular")
        self.contratos_tree.heading("carga", text="Carga Familiar")
        self.contratos_tree.heading("paquete", text="Paquete")
        self.contratos_tree.heading("pnf", text="PNF")
        self.contratos_tree.heading("total", text="Total USD")
        self.contratos_tree.heading("estado", text="Estado")

        self.contratos_tree.column("id", width=40, anchor="center")
        self.contratos_tree.column("numero", width=120)
        self.contratos_tree.column("tipo", width=90, anchor="center")
        self.contratos_tree.column("difunto", width=150)
        self.contratos_tree.column("responsable", width=150)
        self.contratos_tree.column("carga", width=125, anchor="center")
        self.contratos_tree.column("paquete", width=70, anchor="center")
        self.contratos_tree.column("pnf", width=55, anchor="center")
        self.contratos_tree.column("total", width=90, anchor="e")
        self.contratos_tree.column("estado", width=75, anchor="center")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.contratos_tree.yview)
        self.contratos_tree.configure(yscrollcommand=scroll.set)
        self.contratos_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.contratos_tree.bind("<Double-1>", lambda e: self.ver_contrato_seleccionado())

        # Barra de Acciones para Contratos
        btn_bar = ctk.CTkFrame(table_container, fg_color="transparent")
        btn_bar.pack(fill="x", padx=10, pady=8)

        ctk.CTkButton(
            btn_bar,
            text="👁️ Ver Detalle",
            command=self.ver_contrato_seleccionado,
            fg_color="#3498db",
            width=110
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_bar,
            text="👨‍👩‍👧‍👦 Ver / Anexar Carga Familiar",
            command=self.cargar_contrato_en_pnf_desde_tabla,
            fg_color="#d4af37",
            text_color="black",
            font=("Segoe UI", 12, "bold"),
            width=210
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_bar,
            text="🔍 Verificar Total",
            command=self.verificar_total_contrato_tabla,
            fg_color="#2980b9",
            width=130
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_bar,
            text="⏰ Modificar Horario / Llegada",
            command=self.abrir_dialogo_modificar_horario,
            fg_color="#e67e22",
            width=180
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_bar,
            text="🏛️ Reasignar Capilla",
            command=self.abrir_dialogo_reasignar_capilla,
            fg_color="#8e44ad",
            width=140
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_bar,
            text="📄 Generar PDF",
            command=self.generar_pdf_seleccionado,
            fg_color="#27ae60",
            width=120
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_bar,
            text="🔄 Actualizar",
            command=self.cargar_contratos,
            fg_color="gray",
            width=90
        ).pack(side="right", padx=4)

    def crear_formulario_pnf(self, parent):
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True, padx=10, pady=5)

        # ----------------------------------------------------
        # 0. SELECCIONAR CONTRATO (NUEVO O EXISTENTE PARA REFLEJAR / ANEXAR CARGA FAMILIAR)
        # ----------------------------------------------------
        card_sel = ctk.CTkFrame(scroll, fg_color=("#EFF6FF", "#162032"), border_width=1, border_color=("#93C5FD", "#2A4365"), corner_radius=10)
        card_sel.pack(fill="x", pady=(4, 8), padx=5)

        ctk.CTkLabel(
            card_sel,
            text="📌 SELECCIONAR CONTRATO (CREAR NUEVO PNF O ANEXAR / VER CARGA FAMILIAR DE UN CONTRATO)",
            font=("Segoe UI", 13, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", padx=15, pady=(10, 4))

        s_row = ctk.CTkFrame(card_sel, fg_color="transparent")
        s_row.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(s_row, text="Contrato:", font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 8))
        self.pnf_contrato_combo = ctk.CTkComboBox(
            s_row,
            values=["-- ➕ Crear Nuevo Contrato PNF --"],
            width=520,
            state="readonly",
            command=self.on_pnf_contrato_seleccionado
        )
        self.pnf_contrato_combo.set("-- ➕ Crear Nuevo Contrato PNF --")
        self.pnf_contrato_combo.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            s_row,
            text="➕ Nuevo PNF",
            command=self.limpiar_formulario_pnf,
            fg_color="#3498db",
            width=110
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            s_row,
            text="🔄 Actualizar Lista",
            command=self.cargar_contratos_pnf_combo,
            fg_color="gray",
            width=130
        ).pack(side="left", padx=4)

        # ----------------------------------------------------
        # 1. DATOS DEL TITULAR (OBLIGATORIO +18 AÑOS)
        # ----------------------------------------------------
        card_tit = ctk.CTkFrame(scroll, fg_color=("#F8FAFC", "#1A222D"), border_width=1, border_color=("#CBD5E1", "#2D3748"), corner_radius=10)
        card_tit.pack(fill="x", pady=8, padx=5)

        ctk.CTkLabel(
            card_tit,
            text="1. DATOS DEL TITULAR DEL PLAN (OBLIGATORIO +18 AÑOS)",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", padx=15, pady=(12, 6))

        # Fila 1: Nombre y Cédula
        f_row1 = ctk.CTkFrame(card_tit, fg_color="transparent")
        f_row1.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(f_row1, text="Nombre Completo:*", width=130, anchor="w").pack(side="left")
        self.pnf_tit_nombre = ctk.CTkEntry(f_row1, width=260, placeholder_text="Ej: Carlos Pérez")
        self.pnf_tit_nombre.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(f_row1, text="Cédula de Identidad:*", width=140, anchor="w").pack(side="left")
        self.pnf_tit_cedula = ctk.CTkEntry(f_row1, width=150, placeholder_text="Ej: V-12345678")
        self.pnf_tit_cedula.pack(side="left", padx=(0, 10))
        self.pnf_tit_cedula.bind("<Return>", lambda e: self.buscar_titular_pnf())

        ctk.CTkButton(
            f_row1,
            text="🔍 Buscar",
            command=self.buscar_titular_pnf,
            fg_color="#3498db",
            width=80
        ).pack(side="left")

        # Fila 2: Fecha de Nacimiento y Edad
        f_row2 = ctk.CTkFrame(card_tit, fg_color="transparent")
        f_row2.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(f_row2, text="Fecha Nacimiento (DD/MM/AAAA):", width=190, anchor="w").pack(side="left")
        self.pnf_tit_fnac = ctk.CTkEntry(f_row2, width=130, placeholder_text="DD/MM/AAAA")
        self.pnf_tit_fnac.pack(side="left", padx=(0, 15))
        self.pnf_tit_fnac.bind("<KeyRelease>", self.on_titular_fnac_cambio)
        self.pnf_tit_fnac.bind("<FocusOut>", self.on_titular_fnac_cambio)

        ctk.CTkLabel(f_row2, text="Edad (Años):*", width=85, anchor="w").pack(side="left")
        self.pnf_tit_edad_entry = ctk.CTkEntry(f_row2, width=65, placeholder_text="Ej: 35")
        self.pnf_tit_edad_entry.pack(side="left", padx=(0, 15))
        self.pnf_tit_edad_entry.bind("<KeyRelease>", self.on_titular_edad_manual_cambio)

        self.pnf_tit_status_lbl = ctk.CTkLabel(
            f_row2,
            text="⚠️ Ingrese Fecha o Edad (Debe ser +18 años)",
            font=("Segoe UI", 11, "italic"),
            text_color="#E67E22"
        )
        self.pnf_tit_status_lbl.pack(side="left")

        # Fila 3: Teléfono y Dirección
        f_row3 = ctk.CTkFrame(card_tit, fg_color="transparent")
        f_row3.pack(fill="x", padx=15, pady=(4, 12))

        ctk.CTkLabel(f_row3, text="Teléfono:", width=130, anchor="w").pack(side="left")
        self.pnf_tit_telefono = ctk.CTkEntry(f_row3, width=180, placeholder_text="Ej: 0414-1234567")
        self.pnf_tit_telefono.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(f_row3, text="Dirección:", width=70, anchor="w").pack(side="left")
        self.pnf_tit_direccion = ctk.CTkEntry(f_row3, width=320, placeholder_text="Dirección de residencia")
        self.pnf_tit_direccion.pack(side="left")

        # ----------------------------------------------------
        # 2. BENEFICIARIOS A SU CARGO / CARGA FAMILIAR (1 A 15 PERSONAS, SIN LÍMITE DE EDAD)
        # ----------------------------------------------------
        card_ben = ctk.CTkFrame(scroll, fg_color=("#F8FAFC", "#1A222D"), border_width=1, border_color=("#CBD5E1", "#2D3748"), corner_radius=10)
        card_ben.pack(fill="x", pady=8, padx=5)

        h_ben = ctk.CTkFrame(card_ben, fg_color="transparent")
        h_ben.pack(fill="x", padx=15, pady=(12, 4))

        ctk.CTkLabel(
            h_ben,
            text="2. CARGA FAMILIAR / BENEFICIARIOS A SU CARGO (HASTA 15 PERSONAS - SIN LÍMITE DE EDAD)",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(side="left")

        self.pnf_ben_contador_lbl = ctk.CTkLabel(
            h_ben,
            text="Carga Familiar: 0 / 15  (Agregue de 1 a 15 beneficiarios)",
            font=("Segoe UI", 12, "bold"),
            text_color="#E67E22"
        )
        self.pnf_ben_contador_lbl.pack(side="right")

        # Subcard: Formulario para añadir beneficiario
        form_ben = ctk.CTkFrame(card_ben, fg_color=("#EDF2F7", "#141A22"), corner_radius=8)
        form_ben.pack(fill="x", padx=15, pady=6)

        # Fila 1 de agregar beneficiario
        b_r1 = ctk.CTkFrame(form_ben, fg_color="transparent")
        b_r1.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(b_r1, text="Nombre Completo:*", width=120, anchor="w").pack(side="left")
        self.ben_nombre_entry = ctk.CTkEntry(b_r1, width=240, placeholder_text="Nombre y Apellido")
        self.ben_nombre_entry.pack(side="left", padx=(0, 15))
        self.ben_nombre_entry.bind("<Return>", lambda e: self.agregar_beneficiario_pnf())

        ctk.CTkLabel(b_r1, text="Tipo Documento:*", width=110, anchor="w").pack(side="left")
        self.ben_tipo_doc_combo = ctk.CTkComboBox(
            b_r1,
            values=["Cédula de Identidad (+9 años)", "Partida de Nacimiento"],
            width=230,
            state="readonly",
            command=self.on_tipo_doc_ben_cambio
        )
        self.ben_tipo_doc_combo.set("Cédula de Identidad (+9 años)")
        self.ben_tipo_doc_combo.pack(side="left")

        # Fila 2: Documento dinámico (Cédula vs Folio/Acta)
        b_r2 = ctk.CTkFrame(form_ben, fg_color="transparent")
        b_r2.pack(fill="x", padx=10, pady=4)

        self.ben_docs_container = ctk.CTkFrame(b_r2, fg_color="transparent")
        self.ben_docs_container.pack(side="left")

        # Frame Cédula
        self.ben_cedula_frame = ctk.CTkFrame(self.ben_docs_container, fg_color="transparent")
        self.ben_cedula_frame.pack(side="left")
        ctk.CTkLabel(self.ben_cedula_frame, text="Cédula (+9):*", width=120, anchor="w").pack(side="left")
        self.ben_cedula_entry = ctk.CTkEntry(self.ben_cedula_frame, width=150, placeholder_text="Ej: V-28123456")
        self.ben_cedula_entry.pack(side="left", padx=(0, 15))
        self.ben_cedula_entry.bind("<Return>", lambda e: self.agregar_beneficiario_pnf())

        # Frame Partida (Folio, Acta)
        self.ben_partida_frame = ctk.CTkFrame(self.ben_docs_container, fg_color="transparent")
        ctk.CTkLabel(self.ben_partida_frame, text="Folio:*", width=50, anchor="w").pack(side="left")
        self.ben_folio_entry = ctk.CTkEntry(self.ben_partida_frame, width=80, placeholder_text="Folio")
        self.ben_folio_entry.pack(side="left", padx=(0, 10))
        self.ben_folio_entry.bind("<Return>", lambda e: self.agregar_beneficiario_pnf())

        ctk.CTkLabel(self.ben_partida_frame, text="Acta:*", width=45, anchor="w").pack(side="left")
        self.ben_acta_entry = ctk.CTkEntry(self.ben_partida_frame, width=80, placeholder_text="Acta")
        self.ben_acta_entry.pack(side="left", padx=(0, 15))
        self.ben_acta_entry.bind("<Return>", lambda e: self.agregar_beneficiario_pnf())

        # Parentesco
        ctk.CTkLabel(b_r2, text="Parentesco:", width=80, anchor="w").pack(side="left")
        self.ben_parentesco_entry = ctk.CTkEntry(b_r2, width=150, placeholder_text="Hijo, Padre, etc.")
        self.ben_parentesco_entry.pack(side="left")
        self.ben_parentesco_entry.bind("<Return>", lambda e: self.agregar_beneficiario_pnf())

        # Fila 3: Fecha de Nacimiento, Edad calculada automáticamente y botón agregar
        b_r3 = ctk.CTkFrame(form_ben, fg_color="transparent")
        b_r3.pack(fill="x", padx=10, pady=(4, 8))

        ctk.CTkLabel(b_r3, text="Fecha Nacimiento (DD/MM/AAAA):*", width=190, anchor="w").pack(side="left")
        self.ben_fnac_entry = ctk.CTkEntry(b_r3, width=120, placeholder_text="DD/MM/AAAA")
        self.ben_fnac_entry.pack(side="left", padx=(0, 15))
        self.ben_fnac_entry.bind("<KeyRelease>", self.on_ben_fnac_cambio)
        self.ben_fnac_entry.bind("<FocusOut>", self.on_ben_fnac_cambio)
        self.ben_fnac_entry.bind("<Return>", lambda e: self.agregar_beneficiario_pnf())

        self.ben_edad_lbl = ctk.CTkLabel(
            b_r3,
            text="Edad calculada automáticamente: —",
            font=("Segoe UI", 11, "bold"),
            text_color="#d4af37"
        )
        self.ben_edad_lbl.pack(side="left", padx=(0, 20))

        ctk.CTkButton(
            b_r3,
            text="➕ Agregar a la Nómina",
            command=self.agregar_beneficiario_pnf,
            fg_color="#2ecc71",
            text_color="black",
            font=("Segoe UI", 12, "bold"),
            width=180
        ).pack(side="right", padx=5)

        # Tabla Treeview de Beneficiarios
        tree_frame = ctk.CTkFrame(card_ben, fg_color="transparent")
        tree_frame.pack(fill="x", padx=15, pady=4)

        ben_cols = ("num", "nombre", "tipo_doc", "ident", "fecha_nac", "edad", "parentesco")
        self.pnf_ben_tree = ttk.Treeview(tree_frame, columns=ben_cols, show="headings", height=5)
        self.pnf_ben_tree.heading("num", text="N°")
        self.pnf_ben_tree.heading("nombre", text="Nombre Completo")
        self.pnf_ben_tree.heading("tipo_doc", text="Tipo Doc.")
        self.pnf_ben_tree.heading("ident", text="Cédula / Folio - Acta")
        self.pnf_ben_tree.heading("fecha_nac", text="F. Nacimiento")
        self.pnf_ben_tree.heading("edad", text="Edad")
        self.pnf_ben_tree.heading("parentesco", text="Parentesco")

        self.pnf_ben_tree.column("num", width=35, anchor="center")
        self.pnf_ben_tree.column("nombre", width=190)
        self.pnf_ben_tree.column("tipo_doc", width=95, anchor="center")
        self.pnf_ben_tree.column("ident", width=170)
        self.pnf_ben_tree.column("fecha_nac", width=95, anchor="center")
        self.pnf_ben_tree.column("edad", width=75, anchor="center")
        self.pnf_ben_tree.column("parentesco", width=95, anchor="center")

        b_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.pnf_ben_tree.yview)
        self.pnf_ben_tree.configure(yscrollcommand=b_scroll.set)
        self.pnf_ben_tree.pack(side="left", fill="both", expand=True)
        b_scroll.pack(side="right", fill="y")

        # Botones de la tabla de beneficiarios
        b_bar = ctk.CTkFrame(card_ben, fg_color="transparent")
        b_bar.pack(fill="x", padx=15, pady=(4, 10))

        ctk.CTkButton(
            b_bar,
            text="🗑️ Eliminar Beneficiario Seleccionado",
            command=self.eliminar_beneficiario_pnf,
            fg_color="#e74c3c",
            width=220
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            b_bar,
            text="🧹 Limpiar Toda la Nómina",
            command=self.limpiar_nomina_pnf,
            fg_color="gray",
            width=170
        ).pack(side="left", padx=5)

        # ----------------------------------------------------
        # 3. TIPO DE PLAN Y COSTO DEL PLAN
        # ----------------------------------------------------
        card_plan = ctk.CTkFrame(scroll, fg_color=("#F8FAFC", "#1A222D"), border_width=1, border_color=("#CBD5E1", "#2D3748"), corner_radius=10)
        card_plan.pack(fill="x", pady=8, padx=5)

        ctk.CTkLabel(
            card_plan,
            text="3. TIPO DE PLAN Y COSTO DEL PLAN",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", padx=15, pady=(12, 6))

        p_row1 = ctk.CTkFrame(card_plan, fg_color="transparent")
        p_row1.pack(fill="x", padx=15, pady=4)

        self.pnf_plan_var = ctk.StringVar(value="BRONCE")
        for p_name in ["BRONCE", "PLATA", "ORO"]:
            p_info = PAQUETES.get(p_name, {})
            rb = ctk.CTkRadioButton(
                p_row1,
                text=f"{p_name} (${p_info.get('precio', 0):,.2f})",
                variable=self.pnf_plan_var,
                value=p_name,
                command=self.on_pnf_plan_cambiado,
                font=("Segoe UI", 12, "bold")
            )
            rb.pack(side="left", padx=15, pady=5)

        self.pnf_plan_desc_lbl = ctk.CTkLabel(
            card_plan,
            text=PAQUETES["BRONCE"]["descripcion"],
            wraplength=700,
            justify="left",
            text_color="#A0AEC0",
            font=("Segoe UI", 11)
        )
        self.pnf_plan_desc_lbl.pack(anchor="w", padx=20, pady=4)

        # Opciones extras de cobertura PNF
        p_row2 = ctk.CTkFrame(card_plan, fg_color="transparent")
        p_row2.pack(fill="x", padx=15, pady=4)

        self.pnf_cremacion_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            p_row2,
            text="Cobertura de Cremación (+$250.00)",
            variable=self.pnf_cremacion_var,
            command=self.actualizar_calculo_pnf
        ).pack(side="left", padx=15)

        ctk.CTkLabel(p_row2, text="Cobertura de Traslado:").pack(side="left", padx=(15, 5))
        self.pnf_traslado_combo = ctk.CTkComboBox(
            p_row2,
            values=["Local ($0.00)", "Regional (+$300.00)", "Nacional (+$800.00)"],
            width=210,
            state="readonly",
            command=lambda v: self.actualizar_calculo_pnf()
        )
        self.pnf_traslado_combo.set("Local ($0.00)")
        self.pnf_traslado_combo.pack(side="left", padx=5)

        # Costo total del plan
        total_card = ctk.CTkFrame(card_plan, fg_color=("#EDF2F7", "#131820"), corner_radius=8)
        total_card.pack(fill="x", padx=15, pady=(8, 12))

        ctk.CTkLabel(total_card, text="COSTO TOTAL DEL PLAN:", font=("Segoe UI", 13, "bold")).pack(side="left", padx=15, pady=10)
        self.pnf_total_lbl = ctk.CTkLabel(
            total_card,
            text="$850.00 USD",
            font=("Segoe UI", 18, "bold"),
            text_color="#d4af37"
        )
        self.pnf_total_lbl.pack(side="left", padx=10)

        # ----------------------------------------------------
        # 4. FORMA Y PERIODICIDAD DE CANCELACIÓN (PAGO)
        # ----------------------------------------------------
        card_pago = ctk.CTkFrame(scroll, fg_color=("#F8FAFC", "#1A222D"), border_width=1, border_color=("#CBD5E1", "#2D3748"), corner_radius=10)
        card_pago.pack(fill="x", pady=8, padx=5)

        ctk.CTkLabel(
            card_pago,
            text="4. FORMA Y PERIODICIDAD DE CANCELACIÓN (SEMANAL, QUINCENAL, MENSUAL, TRIMESTRAL)",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", padx=15, pady=(12, 6))

        # Modalidad
        pay_r1 = ctk.CTkFrame(card_pago, fg_color="transparent")
        pay_r1.pack(fill="x", padx=15, pady=4)

        self.pnf_metodo_pago_var = ctk.StringVar(value="Financiado")
        ctk.CTkRadioButton(
            pay_r1,
            text="Financiado (Pago por cuotas)",
            variable=self.pnf_metodo_pago_var,
            value="Financiado",
            command=self.actualizar_calculo_pnf,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=15)

        ctk.CTkRadioButton(
            pay_r1,
            text="Contado (Pago único total)",
            variable=self.pnf_metodo_pago_var,
            value="Contado",
            command=self.actualizar_calculo_pnf,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=15)

        # Frecuencia de cancelación
        self.pnf_finan_container = ctk.CTkFrame(card_pago, fg_color="transparent")
        self.pnf_finan_container.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(self.pnf_finan_container, text="Periodicidad de Cancelación:*", font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 10))

        self.pnf_frecuencia_var = ctk.StringVar(value="Mensual")
        for freq in ["Semanal", "Quincenal", "Mensual", "Trimestral"]:
            ctk.CTkRadioButton(
                self.pnf_finan_container,
                text=freq,
                variable=self.pnf_frecuencia_var,
                value=freq,
                command=self.on_pnf_frecuencia_cambio,
                font=("Segoe UI", 11)
            ).pack(side="left", padx=10)

        # Cuotas e inicial
        pay_r2 = ctk.CTkFrame(card_pago, fg_color="transparent")
        pay_r2.pack(fill="x", padx=15, pady=6)

        ctk.CTkLabel(pay_r2, text="Inicial ($):", width=70, anchor="w").pack(side="left")
        self.pnf_inicial_entry = ctk.CTkEntry(pay_r2, width=90)
        self.pnf_inicial_entry.insert(0, "0.00")
        self.pnf_inicial_entry.pack(side="left", padx=(0, 20))
        self.pnf_inicial_entry.bind("<KeyRelease>", self.actualizar_calculo_pnf)

        ctk.CTkLabel(pay_r2, text="N° Cuotas:", width=70, anchor="w").pack(side="left")
        self.pnf_cuotas_entry = ctk.CTkEntry(pay_r2, width=70)
        self.pnf_cuotas_entry.insert(0, "12")
        self.pnf_cuotas_entry.pack(side="left", padx=(0, 20))
        self.pnf_cuotas_entry.bind("<KeyRelease>", self.actualizar_calculo_pnf)

        # Badge resumen de cuota
        self.pnf_cuota_info_lbl = ctk.CTkLabel(
            pay_r2,
            text="Monto por cuota: $70.83 USD | Periodicidad: Mensual (12 cuotas)",
            font=("Segoe UI", 12, "bold"),
            text_color="#2ECC71"
        )
        self.pnf_cuota_info_lbl.pack(side="left", padx=10)

        # ----------------------------------------------------
        # 5. REGISTRAR Y GENERAR PNF
        # ----------------------------------------------------
        card_gen = ctk.CTkFrame(scroll, fg_color=("#F8FAFC", "#1A222D"), border_width=1, border_color=("#CBD5E1", "#2D3748"), corner_radius=10)
        card_gen.pack(fill="x", pady=8, padx=5)

        ctk.CTkLabel(card_gen, text="5. OBSERVACIONES Y GENERACIÓN DEL DOCUMENTO PNF", font=("Segoe UI", 14, "bold"), text_color="#d4af37").pack(anchor="w", padx=15, pady=(12, 4))

        self.pnf_obs_entry = ctk.CTkTextbox(card_gen, height=50)
        self.pnf_obs_entry.pack(fill="x", padx=15, pady=4)

        self.pnf_submit_btn = ctk.CTkButton(
            card_gen,
            text="📄 REGISTRAR CONTRATO Y GENERAR PNF (PDF)",
            command=self.crear_contrato_pnf,
            fg_color="#d4af37",
            hover_color="#b8960c",
            text_color="black",
            height=48,
            font=("Segoe UI", 14, "bold")
        )
        self.pnf_submit_btn.pack(fill="x", padx=15, pady=(10, 15))

    def cargar_contratos_pnf_combo(self):
        """Carga en el desplegable superior de PNF los contratos registrados para consultar o anexar su carga familiar"""
        if not hasattr(self, 'pnf_contrato_combo'):
            return
        conn = obtener_conexion()
        c = conn.cursor()
        c.execute("""
            SELECT c.id, c.numero, COALESCE(c.tipo_contrato, 'Inmediato') as tipo,
                   COALESCE(f.resp_nombre || ' ' || f.resp_apellido, 'Sin titular') as titular,
                   COALESCE(f.resp_cedula, '') as cedula,
                   (SELECT COUNT(*) FROM contrato_beneficiarios cb WHERE cb.contrato_id = c.id) as num_ben
            FROM contratos c
            LEFT JOIN familias f ON c.familia_id = f.familia_id
            ORDER BY c.id DESC
        """)
        rows = c.fetchall()
        conn.close()

        self.pnf_contratos_dict = {}
        opciones = ["-- ➕ Crear Nuevo Contrato PNF --"]
        for r in rows:
            cid, num, tipo, tit, ced, nben = r
            etiqueta = f"{num} [{tipo}] — Titular: {tit} ({ced}) — 👨‍👩‍👧‍👦 Carga Familiar: {nben} pers."
            self.pnf_contratos_dict[etiqueta] = cid
            opciones.append(etiqueta)

        self.pnf_contrato_combo.configure(values=opciones)
        if self.pnf_contrato_edit_id:
            encontrado = None
            for k, v in self.pnf_contratos_dict.items():
                if v == self.pnf_contrato_edit_id:
                    encontrado = k
                    break
            if encontrado:
                self.pnf_contrato_combo.set(encontrado)
            else:
                self.pnf_contrato_combo.set(opciones[0])
        else:
            self.pnf_contrato_combo.set(opciones[0])

    def on_pnf_contrato_seleccionado(self, seleccion=None):
        if not seleccion or seleccion == "-- ➕ Crear Nuevo Contrato PNF --" or seleccion not in self.pnf_contratos_dict:
            self.pnf_contrato_edit_id = None
            self.limpiar_formulario_pnf(reset_combo=False)
            return

        cid = self.pnf_contratos_dict[seleccion]
        self.cargar_contrato_existente_en_pnf(cid)

    def cargar_contrato_existente_en_pnf(self, contrato_id: int):
        """Carga los datos y refleja la carga familiar de un contrato existente en la pestaña PNF"""
        datos = ContratoService.obtener_contrato_completo(contrato_id)
        if not datos:
            return

        self.pnf_contrato_edit_id = contrato_id

        # Sincronizar el combo si se llamó desde otra pestaña
        for k, v in self.pnf_contratos_dict.items():
            if v == contrato_id:
                self.pnf_contrato_combo.set(k)
                break

        # 1. Titular
        self.pnf_tit_nombre.delete(0, "end")
        self.pnf_tit_nombre.insert(0, datos.get("responsable") or "")
        self.pnf_tit_cedula.delete(0, "end")
        self.pnf_tit_cedula.insert(0, datos.get("responsable_cedula") or "")
        self.pnf_tit_telefono.delete(0, "end")
        self.pnf_tit_telefono.insert(0, datos.get("responsable_telefono") or "")
        self.pnf_tit_direccion.delete(0, "end")
        self.pnf_tit_direccion.insert(0, datos.get("responsable_direccion") or "")

        self.pnf_tit_fnac.delete(0, "end")
        self.pnf_tit_edad_entry.delete(0, "end")
        edad_guardada = datos.get("titular_edad")
        if edad_guardada:
            self.pnf_tit_edad_entry.insert(0, str(edad_guardada))
            self.on_titular_edad_manual_cambio()
        else:
            self.pnf_tit_edad_entry.insert(0, "18")
            self.on_titular_edad_manual_cambio()

        # 2. Beneficiarios / Carga Familiar
        self.beneficiarios_pnf = []
        for b in (datos.get("beneficiarios") or []):
            self.beneficiarios_pnf.append({
                "nombre_completo": b.get("nombre_completo", ""),
                "tipo_documento": b.get("tipo_documento", "Cedula"),
                "cedula": b.get("cedula") or "",
                "folio": b.get("folio") or "",
                "acta": b.get("acta") or "",
                "fecha_nacimiento": b.get("fecha_nacimiento") or "",
                "edad": b.get("edad") or 0,
                "parentesco": b.get("parentesco") or ""
            })
        self.actualizar_tabla_beneficiarios_pnf()

        # 3. Plan y Coberturas
        paq = datos.get("paquete", "BRONCE")
        if paq in PAQUETES:
            self.pnf_plan_var.set(paq)
            self.on_pnf_plan_cambiado()

        self.pnf_cremacion_var.set(bool(datos.get("requiere_cremacion")))
        tras = datos.get("tipo_traslado", "Local")
        if tras == "Regional":
            self.pnf_traslado_combo.set("Regional (+$300.00)")
        elif tras == "Nacional":
            self.pnf_traslado_combo.set("Nacional (+$800.00)")
        else:
            self.pnf_traslado_combo.set("Local ($0.00)")

        # 4. Forma de pago
        metodo = datos.get("metodo_pago", "Financiado")
        self.pnf_metodo_pago_var.set(metodo if metodo in ("Financiado", "Contado") else "Financiado")
        freq = datos.get("frecuencia_pago") or "Mensual"
        if freq in ("Semanal", "Quincenal", "Mensual", "Trimestral"):
            self.pnf_frecuencia_var.set(freq)

        self.pnf_inicial_entry.delete(0, "end")
        self.pnf_inicial_entry.insert(0, f"{datos.get('inicial', 0.0):.2f}")
        self.pnf_cuotas_entry.delete(0, "end")
        self.pnf_cuotas_entry.insert(0, str(datos.get("numero_cuotas") or 12))

        self.pnf_obs_entry.delete("1.0", "end")
        self.pnf_obs_entry.insert("1.0", datos.get("observaciones") or "")

        self.actualizar_calculo_pnf()

        if hasattr(self, "pnf_submit_btn"):
            self.pnf_submit_btn.configure(
                text=f"💾 GUARDAR CARGA FAMILIAR Y ACTUALIZAR CONTRATO {datos['numero']} (PDF)"
            )

    def on_titular_fnac_cambio(self, event=None):
        fnac = self.pnf_tit_fnac.get().strip()
        edad = calcular_edad(fnac)
        if edad is not None:
            self.pnf_tit_edad_entry.delete(0, "end")
            self.pnf_tit_edad_entry.insert(0, str(edad))
            self._actualizar_estado_edad_titular(edad)
        else:
            # Si no hay fecha válida, intentar leer edad manual
            self.on_titular_edad_manual_cambio()

    def on_titular_edad_manual_cambio(self, event=None):
        val = self.pnf_tit_edad_entry.get().strip()
        if not val:
            if hasattr(self, "pnf_tit_edad_lbl"):
                self.pnf_tit_edad_lbl.configure(text="Edad: —", text_color="gray")
            self.pnf_tit_status_lbl.configure(
                text="⚠️ Ingrese Fecha o Edad (Debe ser +18 años)",
                text_color="#E67E22"
            )
            return
        try:
            edad = int(val)
            self._actualizar_estado_edad_titular(edad)
        except ValueError:
            if hasattr(self, "pnf_tit_edad_lbl"):
                self.pnf_tit_edad_lbl.configure(text="Edad: —", text_color="gray")
            self.pnf_tit_status_lbl.configure(
                text="⚠️ Ingrese un número válido para la edad (+18)",
                text_color="#E67E22"
            )

    def _actualizar_estado_edad_titular(self, edad: int):
        if hasattr(self, "pnf_tit_edad_lbl"):
            self.pnf_tit_edad_lbl.configure(text=f"Edad: {edad} años", text_color="#2ECC71" if edad >= 18 else "#E74C3C")
        if edad < 18:
            self.pnf_tit_status_lbl.configure(
                text=f"❌ El titular DEBE ser mayor de 18 años (+18). Edad: {edad} años",
                text_color="#E74C3C"
            )
        else:
            self.pnf_tit_status_lbl.configure(
                text=f"✅ Titular mayor de edad (+18 años: {edad} años)",
                text_color="#2ECC71"
            )

    def buscar_titular_pnf(self):
        cedula = self.pnf_tit_cedula.get().strip()
        if not cedula:
            mb.showwarning("Buscar Titular", "Ingrese la cédula a buscar.")
            return
        familia = ClienteService.buscar_familia_por_cedula(cedula)
        if familia:
            self.pnf_tit_nombre.delete(0, "end")
            self.pnf_tit_nombre.insert(0, f"{familia['resp_nombre']} {familia['resp_apellido']}".strip())
            self.pnf_tit_telefono.delete(0, "end")
            self.pnf_tit_telefono.insert(0, familia.get("resp_telefono", ""))
            self.pnf_tit_direccion.delete(0, "end")
            self.pnf_tit_direccion.insert(0, familia.get("resp_direccion", ""))
            mb.showinfo("Titular Encontrado", f"Titular {familia['resp_nombre']} {familia['resp_apellido']} cargado correctamente.")
        else:
            mb.showinfo("No Encontrado", f"No se encontró un titular previo con la cédula {cedula}. Complete los datos para registrarlo.")

    def on_tipo_doc_ben_cambio(self, val=None):
        tipo = self.ben_tipo_doc_combo.get()
        if "Cédula" in tipo:
            self.ben_partida_frame.pack_forget()
            self.ben_cedula_frame.pack(side="left")
        else:
            self.ben_cedula_frame.pack_forget()
            self.ben_partida_frame.pack(side="left")
        self.on_ben_fnac_cambio()

    def on_ben_fnac_cambio(self, event=None):
        fnac = self.ben_fnac_entry.get().strip()
        edad = calcular_edad(fnac)
        if edad is None:
            self.ben_edad_lbl.configure(text="Edad calculada automáticamente: —", text_color="gray")
        else:
            tipo = self.ben_tipo_doc_combo.get()
            if "Cédula" in tipo and edad < 9:
                self.ben_edad_lbl.configure(
                    text=f"Edad calculada: {edad} años  (⚠️ Menor a 9 años: Debe usar Partida de Nacimiento)",
                    text_color="#E67E22"
                )
            elif "Partida" in tipo and edad >= 9:
                self.ben_edad_lbl.configure(
                    text=f"Edad calculada: {edad} años  (ℹ️ Mayor a 9 años: Puede usar Cédula)",
                    text_color="#3498DB"
                )
            else:
                self.ben_edad_lbl.configure(
                    text=f"Edad calculada automáticamente: {edad} años",
                    text_color="#2ECC71"
                )

    def agregar_beneficiario_pnf(self):
        if len(self.beneficiarios_pnf) >= 15:
            mb.showwarning("Límite Máximo", "El plan permite un máximo de 15 beneficiarios a su cargo.")
            return

        nombre = self.ben_nombre_entry.get().strip()
        if not nombre:
            mb.showwarning("Campo Requerido", "Ingrese el nombre completo del beneficiario.")
            return

        tipo_sel = self.ben_tipo_doc_combo.get()
        es_ced = "Cédula" in tipo_sel
        tipo_doc = "Cedula" if es_ced else "Partida"

        fnac = self.ben_fnac_entry.get().strip()
        edad = calcular_edad(fnac)
        if edad is None:
            mb.showwarning("Fecha Inválida", "Ingrese una fecha de nacimiento válida (AAAA-MM-DD o DD/MM/AAAA) para calcular la edad automáticamente.")
            return

        cedula = ""
        folio = ""
        acta = ""
        if es_ced:
            cedula = self.ben_cedula_entry.get().strip()
            if not cedula:
                mb.showwarning("Cédula Requerida", "Para beneficiarios con cédula debe ingresar el número de cédula (+9 años).")
                return
            if edad < 9:
                if not mb.askyesno("Confirmar Edad", f"El beneficiario tiene {edad} años (menor a 9 años).\n¿Desea registrarlo con Cédula de todas formas?"):
                    return
        else:
            folio = self.ben_folio_entry.get().strip()
            acta = self.ben_acta_entry.get().strip()
            if not folio or not acta:
                mb.showwarning("Partida Incompleta", "Para partida de nacimiento debe ingresar obligatoriamente Folio y Acta.")
                return

        parentesco = self.ben_parentesco_entry.get().strip()

        self.beneficiarios_pnf.append({
            "nombre_completo": nombre,
            "tipo_documento": tipo_doc,
            "cedula": cedula,
            "folio": folio,
            "acta": acta,
            "fecha_nacimiento": fnac,
            "edad": edad,
            "parentesco": parentesco
        })

        self.actualizar_tabla_beneficiarios_pnf()

        # Limpiar entradas de beneficiario
        self.ben_nombre_entry.delete(0, "end")
        self.ben_cedula_entry.delete(0, "end")
        self.ben_folio_entry.delete(0, "end")
        self.ben_acta_entry.delete(0, "end")
        self.ben_fnac_entry.delete(0, "end")
        self.ben_parentesco_entry.delete(0, "end")
        self.ben_edad_lbl.configure(text="Edad calculada automáticamente: —", text_color="gray")

    def eliminar_beneficiario_pnf(self):
        sel = self.pnf_ben_tree.selection()
        if not sel:
            mb.showwarning("Selección", "Seleccione un beneficiario de la lista para eliminar.")
            return
        item = sel[0]
        vals = self.pnf_ben_tree.item(item, "values")
        if vals:
            idx = int(vals[0]) - 1
            if 0 <= idx < len(self.beneficiarios_pnf):
                del self.beneficiarios_pnf[idx]
                self.actualizar_tabla_beneficiarios_pnf()

    def limpiar_nomina_pnf(self):
        if not self.beneficiarios_pnf:
            return
        if mb.askyesno("Limpiar Nómina", "¿Desea vaciar toda la nómina de beneficiarios registrados?"):
            self.beneficiarios_pnf.clear()
            self.actualizar_tabla_beneficiarios_pnf()

    def actualizar_tabla_beneficiarios_pnf(self):
        for r in self.pnf_ben_tree.get_children():
            self.pnf_ben_tree.delete(r)

        for idx, b in enumerate(self.beneficiarios_pnf, 1):
            if b["tipo_documento"] == "Cedula":
                doc_info = f"C.I: {b['cedula']}"
            else:
                doc_info = f"Folio: {b['folio']} | Acta: {b['acta']}"
            self.pnf_ben_tree.insert("", "end", values=(
                idx, b["nombre_completo"], b["tipo_documento"], doc_info,
                b["fecha_nacimiento"], f"{b['edad']} años", b["parentesco"]
            ))

        cnt = len(self.beneficiarios_pnf)
        if cnt == 0:
            self.pnf_ben_contador_lbl.configure(
                text="Carga Familiar: 0 / 15  (⚠️ Agregue al menos 1 beneficiario a su cargo)",
                text_color="#E67E22"
            )
        elif cnt <= 15:
            self.pnf_ben_contador_lbl.configure(
                text=f"Carga Familiar: {cnt} / 15  (✅ {cnt} beneficiario(s) + Titular = {cnt + 1} personas)",
                text_color="#2ECC71"
            )
        else:
            self.pnf_ben_contador_lbl.configure(
                text=f"Carga Familiar: {cnt} / 15  (❌ Excede el máximo de 15)",
                text_color="#E74C3C"
            )

    def on_pnf_plan_cambiado(self):
        paq = self.pnf_plan_var.get()
        desc = PAQUETES.get(paq, {}).get("descripcion", "")
        self.pnf_plan_desc_lbl.configure(text=desc)
        self.actualizar_calculo_pnf()

    def on_pnf_frecuencia_cambio(self, val=None):
        freq = self.pnf_frecuencia_var.get()
        cuotas_sug = {"Semanal": 52, "Quincenal": 24, "Mensual": 12, "Trimestral": 4}
        if hasattr(self, 'pnf_cuotas_entry'):
            self.pnf_cuotas_entry.delete(0, "end")
            self.pnf_cuotas_entry.insert(0, str(cuotas_sug.get(freq, 12)))
        self.actualizar_calculo_pnf()

    def actualizar_calculo_pnf(self, *args):
        if not hasattr(self, 'pnf_plan_var') or not hasattr(self, 'pnf_total_lbl'):
            return

        paq = self.pnf_plan_var.get()
        base = PAQUETES.get(paq, {}).get("precio", 850.00)

        costo_crem = 250.00 if self.pnf_cremacion_var.get() else 0.00
        tras_str = self.pnf_traslado_combo.get()
        costo_tras = 0.00
        if "Regional" in tras_str:
            costo_tras = 300.00
        elif "Nacional" in tras_str:
            costo_tras = 800.00

        total = base + costo_crem + costo_tras
        self.pnf_total_lbl.configure(text=f"${total:,.2f} USD")

        es_fin = self.pnf_metodo_pago_var.get() == "Financiado"
        if es_fin:
            self.pnf_finan_container.pack(fill="x", padx=15, pady=4)
            try:
                inicial = float(self.pnf_inicial_entry.get() or 0.0)
                if inicial < 0: inicial = 0.0
            except ValueError:
                inicial = 0.0

            try:
                num_c = int(self.pnf_cuotas_entry.get() or 1)
                if num_c < 1: num_c = 1
            except ValueError:
                num_c = 1

            saldo = max(0.0, total - inicial)
            cuota_monto = saldo / num_c
            freq = self.pnf_frecuencia_var.get()
            self.pnf_cuota_info_lbl.configure(
                text=f"Monto por cuota: ${cuota_monto:,.2f} USD  |  {num_c} cuotas ({freq})  |  Saldo: ${saldo:,.2f}"
            )
        else:
            self.pnf_finan_container.pack_forget()
            self.pnf_cuota_info_lbl.configure(
                text="Modalidad Contado: Cancelación total en un solo pago de contado."
            )

    def crear_contrato_pnf(self):
        # 1. Validar titular
        nombre_tit = self.pnf_tit_nombre.get().strip()
        cedula_tit = self.pnf_tit_cedula.get().strip()
        if not nombre_tit or not cedula_tit:
            mb.showwarning("Titular Obligatorio", "Ingrese el Nombre completo y la Cédula del titular.")
            return

        fnac_tit = self.pnf_tit_fnac.get().strip()
        edad_tit = calcular_edad(fnac_tit)
        if edad_tit is None:
            try:
                edad_tit = int(self.pnf_tit_edad_entry.get().strip())
            except ValueError:
                edad_tit = None

        if edad_tit is None:
            mb.showwarning("Edad del Titular", "Ingrese la Fecha de Nacimiento o la Edad del titular (+18 años).")
            return
        if edad_tit < 18:
            mb.showerror("Titular Menor de Edad", f"El titular del plan DEBE ser mayor de edad (+18 años).\nEdad actual: {edad_tit} años.")
            return

        # 2. Validar beneficiarios a su cargo (de 1 a 15 personas)
        num_ben = len(self.beneficiarios_pnf)
        if num_ben < 1:
            mb.showwarning(
                "Carga Familiar Vacía",
                "Debe anexar al menos 1 beneficiario a su cargo en la nómina de Carga Familiar."
            )
            return
        if num_ben > 15:
            mb.showwarning(
                "Límite de Beneficiarios Superado",
                f"El plan permite un máximo de 15 beneficiarios a su cargo.\nActualmente tiene registrados: {num_ben} personas."
            )
            return

        # 3. Plan y Costos
        plan_sel = self.pnf_plan_var.get()
        paq_data = PAQUETES.get(plan_sel, {})
        costo_paq = paq_data.get("precio", 850.00)
        costo_crem = 250.00 if self.pnf_cremacion_var.get() else 0.00

        tras_str = self.pnf_traslado_combo.get()
        costo_tras = 0.00
        tipo_tras = "Local"
        if "Regional" in tras_str:
            tipo_tras = "Regional"
            costo_tras = 300.00
        elif "Nacional" in tras_str:
            tipo_tras = "Nacional"
            costo_tras = 800.00

        total = costo_paq + costo_crem + costo_tras
        metodo = self.pnf_metodo_pago_var.get()
        freq = self.pnf_frecuencia_var.get()

        inicial = 0.0
        num_cuotas = 1
        if metodo == "Financiado":
            try:
                inicial = float(self.pnf_inicial_entry.get() or 0.0)
                if inicial < 0: inicial = 0.0
                num_cuotas = int(self.pnf_cuotas_entry.get() or 1)
                if num_cuotas < 1: num_cuotas = 1
            except ValueError:
                mb.showerror("Error de Número", "Valores numéricos de inicial o cuotas inválidos.")
                return

        conn = obtener_conexion()
        c = conn.cursor()
        try:
            # Registrar o actualizar familia / titular
            c.execute("SELECT familia_id FROM familias WHERE resp_cedula = ?", (cedula_tit,))
            fam_row = c.fetchone()
            partes = nombre_tit.split(" ", 1)
            p_nom = partes[0]
            p_ape = partes[1] if len(partes) > 1 else ""
            tel = self.pnf_tit_telefono.get().strip()
            direc = self.pnf_tit_direccion.get().strip()

            if fam_row:
                familia_id = fam_row[0]
                c.execute("""
                    UPDATE familias
                    SET resp_nombre = ?, resp_apellido = ?, resp_telefono = ?, resp_direccion = ?
                    WHERE familia_id = ?
                """, (p_nom, p_ape, tel, direc, familia_id))
            else:
                from services.db_service import generar_familia_id
                familia_id = generar_familia_id()
                c.execute("""
                    INSERT INTO familias (familia_id, resp_cedula, resp_nombre, resp_apellido, resp_telefono, resp_direccion, fecha_creacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (familia_id, cedula_tit, p_nom, p_ape, tel, direc, datetime.datetime.now().isoformat()))

            ahora = datetime.datetime.now()
            obs_txt = self.pnf_obs_entry.get("1.0", "end-1c").strip()

            if self.pnf_contrato_edit_id:
                # Actualizar contrato existente y su carga familiar
                contrato_id = self.pnf_contrato_edit_id
                c.execute("SELECT numero FROM contratos WHERE id = ?", (contrato_id,))
                row_num = c.fetchone()
                numero_contrato = row_num[0] if row_num else f"PNF-{contrato_id}"

                c.execute("""
                    UPDATE contratos
                    SET familia_id = ?, paquete = ?, monto_total = ?, metodo_pago = ?,
                        inicial = ?, numero_cuotas = ?, observaciones = ?,
                        requiere_cremacion = ?, tipo_traslado = ?,
                        pnf_asociado = 1, pnf_numero = COALESCE(pnf_numero, ?),
                        pnf_cubre_traslado = ?, pnf_cubre_cremacion = ?,
                        costo_paquete = ?, costo_cremacion = ?, costo_traslado = ?,
                        titular_edad = ?, frecuencia_pago = ?
                    WHERE id = ?
                """, (
                    familia_id, plan_sel, total, metodo,
                    inicial, num_cuotas, obs_txt,
                    1 if self.pnf_cremacion_var.get() else 0, tipo_tras,
                    numero_contrato,
                    1 if costo_tras > 0 else 0, 1 if costo_crem > 0 else 0,
                    costo_paq, costo_crem, costo_tras,
                    edad_tit, freq,
                    contrato_id
                ))

                # Reemplazar carga familiar actualizada
                c.execute("DELETE FROM contrato_beneficiarios WHERE contrato_id = ?", (contrato_id,))
                for b in self.beneficiarios_pnf:
                    c.execute("""
                        INSERT INTO contrato_beneficiarios 
                        (contrato_id, nombre_completo, tipo_documento, cedula, folio, acta, fecha_nacimiento, edad, parentesco)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        contrato_id, b["nombre_completo"], b["tipo_documento"],
                        b["cedula"] if b["tipo_documento"] == "Cedula" else None,
                        b["folio"] if b["tipo_documento"] == "Partida" else None,
                        b["acta"] if b["tipo_documento"] == "Partida" else None,
                        b["fecha_nacimiento"], b["edad"], b["parentesco"]
                    ))

                conn.commit()
                ContratoRepository.registrar_bitacora(
                    self.usuario[0],
                    "Actualización Carga Familiar PNF",
                    f"Contrato {numero_contrato} actualizado con {num_ben} beneficiarios a su cargo."
                )
                mb.showinfo(
                    "Carga Familiar Actualizada",
                    f"✅ Se reflejaron y guardaron {num_ben} beneficiario(s) en la Carga Familiar del contrato {numero_contrato}."
                )
            else:
                # Crear nuevo contrato PNF
                numero_contrato = f"PNF-{ahora.year}{ahora.month:02d}{ahora.day:02d}-{random.randint(1000, 9999)}"
                obs_full = obs_txt

                c.execute("""
                    INSERT INTO contratos (
                        numero, fecha_contrato, familia_id, difunto_id, paquete,
                        capilla_id, fecha_velacion, hora_inicio, hora_fin,
                        monto_total, metodo_pago, inicial, numero_cuotas, pagado, estado, observaciones,
                        requiere_cremacion, tipo_traslado, estado_servicio, tipo_velacion, tipo_contrato,
                        pnf_asociado, pnf_numero, pnf_cubre_traslado, pnf_cubre_cremacion, descuento_pnf,
                        costo_paquete, costo_cremacion, costo_traslado, costo_productos, costo_servicios,
                        titular_edad, frecuencia_pago
                    ) VALUES (?, ?, ?, NULL, ?, NULL, 'Plan a Futuro', '00:00', '00:00',
                              ?, ?, ?, ?, 0.0, 'Activo', ?,
                              ?, ?, 'Pendiente', 'Funeraria', 'Largo Plazo',
                              1, ?, ?, ?, 0.0,
                              ?, ?, ?, 0.0, 0.0,
                              ?, ?)
                """, (
                    numero_contrato, ahora.strftime("%Y-%m-%d"), familia_id, plan_sel,
                    total, metodo, inicial, num_cuotas, obs_full,
                    1 if self.pnf_cremacion_var.get() else 0, tipo_tras,
                    numero_contrato, 1 if costo_tras > 0 else 0, 1 if costo_crem > 0 else 0,
                    costo_paq, costo_crem, costo_tras,
                    edad_tit, freq
                ))

                contrato_id = c.lastrowid

                # Guardar beneficiarios
                for b in self.beneficiarios_pnf:
                    c.execute("""
                        INSERT INTO contrato_beneficiarios 
                        (contrato_id, nombre_completo, tipo_documento, cedula, folio, acta, fecha_nacimiento, edad, parentesco)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        contrato_id, b["nombre_completo"], b["tipo_documento"],
                        b["cedula"] if b["tipo_documento"] == "Cedula" else None,
                        b["folio"] if b["tipo_documento"] == "Partida" else None,
                        b["acta"] if b["tipo_documento"] == "Partida" else None,
                        b["fecha_nacimiento"], b["edad"], b["parentesco"]
                    ))

                # Guardar cuotas periódicas según la periodicidad elegida
                if metodo == "Financiado" and num_cuotas > 0:
                    saldo = max(0.0, total - inicial)
                    plan_cuotas = PrecioService.generar_plan_cuotas(saldo, 0.0, num_cuotas, frecuencia=freq)
                    for cu in plan_cuotas:
                        c.execute("""
                            INSERT INTO cuotas (contrato_id, numero, monto, fecha_vencimiento, estado)
                            VALUES (?, ?, ?, ?, 'Pendiente')
                        """, (contrato_id, cu["numero"], cu["monto"], cu["fecha_vencimiento"]))

                    if inicial > 0:
                        c.execute("""
                            INSERT INTO pagos (contrato_id, fecha, monto, metodo, moneda, monto_original)
                            VALUES (?, ?, ?, 'Efectivo (USD)', 'USD', ?)
                        """, (contrato_id, ahora.strftime("%Y-%m-%d"), inicial, inicial))
                        c.execute("UPDATE contratos SET pagado = pagado + ? WHERE id = ?", (inicial, contrato_id))

                conn.commit()

                ContratoRepository.registrar_bitacora(
                    self.usuario[0],
                    "Creación PNF",
                    f"Contrato PNF {numero_contrato} registrado para {nombre_tit} con {num_ben} beneficiarios. Total ${total:,.2f}"
                )

                mb.showinfo("Éxito PNF", f"✅ Plan Nacional Funerario {numero_contrato} registrado exitosamente con {num_ben} beneficiario(s) a su cargo.")

            # Generar y abrir PDF del PNF
            from services.pdf_service import generar_pdf_contrato
            pdf_ruta = generar_pdf_contrato(contrato_id)
            if pdf_ruta and os.path.exists(pdf_ruta):
                try:
                    os.startfile(pdf_ruta)
                except Exception:
                    pass

            self.limpiar_formulario_pnf()
            self.cargar_contratos()
            # Cambiar a la pestaña de contratos registrados
            self.tabview.set("📋 Contratos Registrados")

        except Exception as e:
            conn.rollback()
            mb.showerror("Error al Guardar PNF", f"No se pudo registrar el contrato PNF:\n{str(e)}")
        finally:
            conn.close()

    def limpiar_formulario_pnf(self, reset_combo: bool = True):
        self.pnf_contrato_edit_id = None
        if reset_combo and hasattr(self, "pnf_contrato_combo"):
            self.pnf_contrato_combo.set("-- ➕ Crear Nuevo Contrato PNF --")
        if hasattr(self, "pnf_submit_btn"):
            self.pnf_submit_btn.configure(text="📄 REGISTRAR CONTRATO Y GENERAR PNF (PDF)")
        self.pnf_tit_nombre.delete(0, "end")
        self.pnf_tit_cedula.delete(0, "end")
        self.pnf_tit_fnac.delete(0, "end")
        if hasattr(self, "pnf_tit_edad_entry"):
            self.pnf_tit_edad_entry.delete(0, "end")
        self.pnf_tit_edad_lbl.configure(text="Edad: —", text_color="gray")
        self.pnf_tit_status_lbl.configure(text="⚠️ Ingrese Fecha de Nacimiento o Edad (Debe ser +18 años)", text_color="#E67E22")
        self.pnf_tit_telefono.delete(0, "end")
        self.pnf_tit_direccion.delete(0, "end")
        self.beneficiarios_pnf.clear()
        self.actualizar_tabla_beneficiarios_pnf()
        self.ben_nombre_entry.delete(0, "end")
        self.ben_cedula_entry.delete(0, "end")
        self.ben_folio_entry.delete(0, "end")
        self.ben_acta_entry.delete(0, "end")
        self.ben_fnac_entry.delete(0, "end")
        self.ben_parentesco_entry.delete(0, "end")
        self.ben_edad_lbl.configure(text="Edad calculada automáticamente: —", text_color="gray")
        self.pnf_plan_var.set("BRONCE")
        self.on_pnf_plan_cambiado()
        self.pnf_cremacion_var.set(False)
        self.pnf_traslado_combo.set("Local ($0.00)")
        self.pnf_metodo_pago_var.set("Financiado")
        self.pnf_frecuencia_var.set("Mensual")
        self.pnf_inicial_entry.delete(0, "end")
        self.pnf_inicial_entry.insert(0, "0.00")
        self.pnf_cuotas_entry.delete(0, "end")
        self.pnf_cuotas_entry.insert(0, "12")
        self.pnf_obs_entry.delete("1.0", "end")
        self.actualizar_calculo_pnf()


    # ========== MÉTODOS DE TIPO DE CONTRATO (INMEDIATO vs LARGO PLAZO) ==========
    def on_cambio_tipo_contrato(self):
        tipo = self.tipo_contrato_var.get()
        if tipo == "Largo Plazo":
            self.tipo_contrato_desc.configure(
                text="Plan a futuro: Titular contratante; difunto y capilla se asignan al deceso.",
                text_color="#3498db"
            )
            self.sec_difunto_label.configure(text="TITULAR CONTRATANTE (PLAN A LARGO PLAZO)")
            self.difunto_combo_label.configure(text="Seleccionar Difunto (opcional o por asignar):")
            self.familia_lp_frame.pack(anchor="w", pady=4, after=self.difunto_combo)
            self.cargar_familias_lp_combo()
            self.sec_capilla_label.configure(text="CAPILLA DE VELACIÓN (Opcional en Largo Plazo)")
        else:
            self.tipo_contrato_desc.configure(
                text="Requiere seleccionar el difunto fallecido y la capilla.",
                text_color="gray"
            )
            self.sec_difunto_label.configure(text="DATOS DEL DIFUNTO Y FAMILIAR RESPONSABLE")
            self.difunto_combo_label.configure(text="Seleccionar Difunto Registrado:*")
            self.familia_lp_frame.pack_forget()
            self.sec_capilla_label.configure(text="CAPILLA DE VELACIÓN:*")

        self.cargar_difuntos_combo()
        self.cargar_capillas()
        self.actualizar_vista_carga_familiar_inmediato()
        self.actualizar_total()

    def toggle_pnf_campos(self):
        if self.pnf_var.get():
            self.pnf_num_entry.configure(state="normal")
            self.pnf_traslado_check.configure(state="normal")
            self.pnf_cremacion_check.configure(state="normal")
        else:
            self.pnf_num_entry.configure(state="disabled")
            self.pnf_traslado_check.configure(state="disabled")
            self.pnf_cremacion_check.configure(state="disabled")
            self.pnf_cubre_traslado_var.set(False)
            self.pnf_cubre_cremacion_var.set(False)
        self.actualizar_vista_carga_familiar_inmediato()
        self.actualizar_total()

    def on_paquete_cambiado(self):
        paq = self.paquete_var.get()
        self.paquete_desc.configure(text=PAQUETES[paq]["descripcion"])
        self.actualizar_total()

    def actualizar_total(self, *args):
        if not hasattr(self, 'paquete_var') or not hasattr(self, 'cremacion_var') or not hasattr(self, 'traslado_combo'):
            return 0.0

        paquete = self.paquete_var.get()
        requiere_cremacion = self.cremacion_var.get()
        traslado_str = self.traslado_combo.get()

        if "Regional" in traslado_str:
            tipo_traslado = "Regional"
        elif "Nacional" in traslado_str:
            tipo_traslado = "Nacional"
        elif "Externo" in traslado_str:
            tipo_traslado = "Externo"
        else:
            tipo_traslado = "Local"

        pnf_asoc = self.pnf_var.get()
        pnf_tras = self.pnf_cubre_traslado_var.get()
        pnf_crem = self.pnf_cubre_cremacion_var.get()

        prods = [{"cantidad": p["cantidad"], "precio": p["precio"]} for p in self.productos_agregados]
        servs = [{"subtotal": s["subtotal"]} for s in self.servicios_agregados]

        desglose = PrecioService.calcular_desglose(
            paquete=paquete,
            requiere_cremacion=requiere_cremacion,
            tipo_traslado=tipo_traslado,
            productos=prods,
            servicios=servs,
            pnf_asociado=pnf_asoc,
            pnf_cubre_traslado=pnf_tras,
            pnf_cubre_cremacion=pnf_crem
        )
        self.desglose_actual = desglose
        total = desglose["total"]

        if desglose["descuento_pnf"] > 0:
            self.total_label.configure(
                text=f"${total:,.2f}  (PNF Descontó: -${desglose['descuento_pnf']:,.2f})"
            )
        else:
            self.total_label.configure(text=f"${total:,.2f}")

        return total

    def verificar_total_en_creacion(self):
        """Abre modal interactivo de verificación matemática de costos"""
        self.actualizar_total()
        if self.desglose_actual:
            traslado_raw = self.traslado_combo.get()
            tipo_traslado = "Local"
            if "Regional" in traslado_raw:
                tipo_traslado = "Regional"
            elif "Nacional" in traslado_raw:
                tipo_traslado = "Nacional"
            elif "Externo" in traslado_raw:
                tipo_traslado = "Externo"

            metodo = self.metodo_var.get()
            try:
                inicial = float(self.inicial_entry.get() or 0.0)
            except ValueError:
                inicial = 0.0
            try:
                cuotas = int(self.cuotas_entry.get() or 1)
            except ValueError:
                cuotas = 1

            verif = PrecioService.construir_verificacion_previa(
                self.desglose_actual,
                paquete=self.paquete_var.get(),
                tipo_traslado=tipo_traslado,
                metodo=metodo,
                inicial=inicial,
                cuotas=cuotas
            )
            mostrar_dialogo_verificar_total(self, verif)

    # ========== CARGAS DE COMBOS ==========
    def cargar_difuntos_combo(self):
        conn = obtener_conexion()
        c = conn.cursor()
        c.execute("""
            SELECT d.id, d.nombre, d.apellido, d.cedula,
                   f.familia_id, f.resp_nombre, f.resp_apellido
            FROM difuntos d
            JOIN familias f ON d.familia_id = f.familia_id
            ORDER BY d.id DESC
        """)
        rows = c.fetchall()
        conn.close()

        self.difunto_dict = {}
        opciones = []
        if self.tipo_contrato_var.get() == "Largo Plazo":
            opciones.append("-- Sin Difunto Asignado (Plan a Futuro) --")
            self.difunto_dict["-- Sin Difunto Asignado (Plan a Futuro) --"] = {
                'difunto_id': None, 'familia_id': None, 'responsable_nombre': "A definir"
            }

        for row in rows:
            clave = f"{row[1]} {row[2]} (C.I: {row[3]})"
            self.difunto_dict[clave] = {
                'difunto_id': row[0],
                'familia_id': row[4],
                'responsable_nombre': f"{row[5]} {row[6]}".strip()
            }
            opciones.append(clave)

        if opciones:
            self.difunto_combo.configure(values=opciones)
            self.difunto_combo.set(opciones[0])
            self.on_difunto_seleccionado(opciones[0])
        else:
            self.difunto_combo.configure(values=["-- No hay difuntos registrados --"])

    def cargar_familias_lp_combo(self):
        familias = ClienteService.listar_todas_familias()
        self.familia_dict = {f"{f['familia_id']} - {f['resp_nombre_completo']}": f for f in familias}
        opciones = list(self.familia_dict.keys())
        if opciones:
            self.familia_combo.configure(values=opciones)
            self.familia_combo.set(opciones[0])
            self.on_familia_lp_seleccionada(opciones[0])
        else:
            self.familia_combo.configure(values=["-- No hay familias registradas --"])

    def on_familia_lp_seleccionada(self, seleccion):
        if seleccion in self.familia_dict:
            f = self.familia_dict[seleccion]
            self.familia_id_actual = f['familia_id']
            self.responsable_info_label.configure(
                text=f"👤 Titular Contratante: {f['resp_nombre_completo']} (C.I: {f['resp_cedula']})",
                text_color="#2ecc71"
            )
            self.actualizar_vista_carga_familiar_inmediato()

    def on_difunto_seleccionado(self, seleccion):
        if not seleccion or seleccion in ["-- No hay difuntos registrados --", "-- Cargando... --"]:
            self.responsable_info_label.configure(text="", text_color="gray")
            self.actualizar_vista_carga_familiar_inmediato()
            return

        if seleccion in self.difunto_dict:
            data = self.difunto_dict[seleccion]
            self.difunto_id_actual = data['difunto_id']
            if data['familia_id']:
                self.familia_id_actual = data['familia_id']
            if data['difunto_id']:
                self.responsable_info_label.configure(
                    text=f"👤 Responsable Registrado: {data['responsable_nombre']} (Familia: {data['familia_id']})",
                    text_color="#2ecc71"
                )
            else:
                self.responsable_info_label.configure(
                    text="🛡️ Plan a Futuro: El difunto será asignado al momento de su activación.",
                    text_color="#3498db"
                )
            self.actualizar_vista_carga_familiar_inmediato()

    def actualizar_vista_carga_familiar_inmediato(self):
        """Muestra u oculta el resumen de la Carga Familiar asociada a la familia seleccionada en el formulario"""
        if not hasattr(self, "carga_familiar_inm_frame"):
            return
        if not self.familia_id_actual:
            self.carga_familiar_inm_frame.pack_forget()
            return

        conn = obtener_conexion()
        c = conn.cursor()
        c.execute("""
            SELECT c.id, c.numero, c.pnf_numero
            FROM contratos c
            WHERE c.familia_id = ?
            ORDER BY (SELECT COUNT(*) FROM contrato_beneficiarios cb WHERE cb.contrato_id = c.id) DESC, c.id DESC
            LIMIT 1
        """, (self.familia_id_actual,))
        row_c = c.fetchone()
        if not row_c:
            conn.close()
            if self.tipo_contrato_var.get() == "Largo Plazo" or self.pnf_var.get():
                self.carga_familiar_inm_lbl.configure(
                    text="👨‍👩‍👧‍👦 Carga Familiar: Sin beneficiarios anexados aún. Use el botón para anexar su carga familiar (1 a 15 personas).",
                    text_color="#E67E22"
                )
                self.carga_familiar_inm_frame.pack(fill="x", pady=4, after=self.responsable_info_label)
            else:
                self.carga_familiar_inm_frame.pack_forget()
            return

        cid, cnum, pnf_num = row_c
        c.execute("""
            SELECT nombre_completo, tipo_documento, cedula, folio, acta, edad, parentesco
            FROM contrato_beneficiarios
            WHERE contrato_id = ?
            ORDER BY id ASC
        """, (cid,))
        bens = c.fetchall()
        conn.close()

        self._ultimo_contrato_familia_id = cid
        if bens:
            nombres = ", ".join([f"{b[0]} ({b[6] or 'Familiar'}, {b[5]}a)" for b in bens[:5]])
            if len(bens) > 5:
                nombres += f" ... (+{len(bens) - 5} más)"
            self.carga_familiar_inm_lbl.configure(
                text=f"👨‍👩‍👧‍👦 Carga Familiar Reflejada ({len(bens)} beneficiario(s) en {cnum}):\n{nombres}",
                text_color="#2ECC71"
            )
            self.carga_familiar_inm_frame.pack(fill="x", pady=4, after=self.responsable_info_label)
        elif self.tipo_contrato_var.get() == "Largo Plazo" or self.pnf_var.get():
            self.carga_familiar_inm_lbl.configure(
                text=f"👨‍👩‍👧‍👦 Contrato {cnum}: Aún no tiene beneficiarios en su Carga Familiar. Haga clic en el botón para anexarlos.",
                text_color="#E67E22"
            )
            self.carga_familiar_inm_frame.pack(fill="x", pady=4, after=self.responsable_info_label)
        else:
            self.carga_familiar_inm_frame.pack_forget()

    def ir_a_carga_familiar_pnf(self):
        """Abre la pestaña PNF y carga el contrato de la familia actual para ver o anexar beneficiarios"""
        self.cargar_contratos_pnf_combo()
        cid = getattr(self, "_ultimo_contrato_familia_id", None)
        if cid:
            self.cargar_contrato_existente_en_pnf(cid)
        self.tabview.set("🛡️ Plan Nacional Funerario (PNF)")

    def buscar_difunto(self):
        texto = self.buscar_difunto_entry.get().strip()
        if not texto:
            mb.showwarning("Buscar", "Ingrese cédula o nombre para buscar.")
            return

        conn = obtener_conexion()
        c = conn.cursor()
        c.execute("""
            SELECT d.id, d.nombre, d.apellido, d.cedula,
                   f.familia_id, f.resp_nombre, f.resp_apellido
            FROM difuntos d
            JOIN familias f ON d.familia_id = f.familia_id
            WHERE d.cedula LIKE ? OR d.nombre LIKE ? OR d.apellido LIKE ?
            LIMIT 10
        """, (f"%{texto}%", f"%{texto}%", f"%{texto}%"))
        rows = c.fetchall()
        conn.close()

        if rows:
            self.difunto_dict = {}
            opciones = []
            for row in rows:
                clave = f"{row[1]} {row[2]} (C.I: {row[3]})"
                self.difunto_dict[clave] = {
                    'difunto_id': row[0],
                    'familia_id': row[4],
                    'responsable_nombre': f"{row[5]} {row[6]}".strip()
                }
                opciones.append(clave)
            self.difunto_combo.configure(values=opciones)
            self.difunto_combo.set(opciones[0])
            self.on_difunto_seleccionado(opciones[0])
            mb.showinfo("Encontrado", f"Se encontraron {len(rows)} difunto(s).")
        else:
            mb.showwarning("No Encontrado", "No se encontró difunto con ese criterio.\nRegístrelo en la pestaña Clientes.")

    def cargar_capillas(self):
        capillas = CapillaRepository.obtener_todas()
        self.capilla_dict = {}
        opciones = []

        if self.tipo_contrato_var.get() == "Largo Plazo":
            opciones.append("-- Por Asignar al Activar Plan --")
            self.capilla_dict["-- Por Asignar al Activar Plan --"] = None

        for c in capillas:
            estado_tag = f" ({c['estado']})" if c['estado'] != "Disponible" else ""
            clave = f"{c['nombre']} - Cap: {c['capacidad']}p{estado_tag}"
            self.capilla_dict[clave] = c['id']
            # Para contratos inmediatos solo sugerir disponibles o todas
            opciones.append(clave)

        self.capilla_combo.configure(values=opciones)
        if opciones:
            self.capilla_combo.set(opciones[0])

    def cargar_productos_combo(self):
        conn = obtener_conexion()
        c = conn.cursor()
        c.execute("SELECT id, nombre, precio, stock FROM inventario WHERE stock > 0")
        rows = c.fetchall()
        conn.close()
        self.producto_dict = {f"{r[1]} (${r[2]:.2f}) [Stock: {r[3]}]": {"id": r[0], "precio": r[2], "nombre": r[1], "stock": r[3]} for r in rows}
        opciones = list(self.producto_dict.keys())
        self.producto_combo.configure(values=opciones)
        if opciones:
            self.producto_combo.set(opciones[0])

    def agregar_producto(self):
        sel = self.producto_combo.get()
        if not sel or sel not in self.producto_dict:
            mb.showwarning("Selección", "Seleccione un producto disponible.")
            return

        try:
            cant = int(self.cantidad_producto.get().strip())
            if cant <= 0:
                raise ValueError
        except ValueError:
            mb.showwarning("Cantidad Inválida", "Ingrese una cantidad entera mayor a 0.")
            return

        p_info = self.producto_dict[sel]
        if cant > p_info["stock"]:
            mb.showwarning("Stock Insuficiente", f"Solo hay {p_info['stock']} unidades disponibles.")
            return

        subt = cant * p_info["precio"]
        self.productos_agregados.append({
            "id": p_info["id"],
            "nombre": p_info["nombre"],
            "cantidad": cant,
            "precio": p_info["precio"],
            "subtotal": subt
        })

        self.actualizar_lista_productos()
        self.actualizar_total()
        self.cantidad_producto.delete(0, "end")
        self.cantidad_producto.insert(0, "1")

    def actualizar_lista_productos(self):
        for r in self.productos_tree.get_children():
            self.productos_tree.delete(r)
        for p in self.productos_agregados:
            self.productos_tree.insert("", "end", values=(
                p["nombre"], p["cantidad"], f"${p['precio']:.2f}", f"${p['subtotal']:.2f}"
            ))

    def cambiar_tipo_velacion(self):
        tipo = self.tipo_velacion_var.get()
        self.tipo_velacion_actual = tipo
        servs = (
            ServicioAdicionalService.SERVICIOS_FUNERARIA if tipo == "Funeraria"
            else ServicioAdicionalService.SERVICIOS_DOMICILIO
        )
        self.servicio_keys = list(servs.keys())
        opciones = [f"{servs[k]['nombre']} (${servs[k]['precio']:.2f})" for k in self.servicio_keys]
        self.servicio_combo.configure(values=opciones)
        if opciones:
            self.servicio_combo.set(opciones[0])

    def agregar_servicio(self):
        sel = self.servicio_combo.get()
        if not sel:
            return
        vals = list(self.servicio_combo.cget("values"))
        try:
            idx = vals.index(sel)
            key = self.servicio_keys[idx]
        except (ValueError, IndexError):
            return

        try:
            cant = int(self.servicio_cantidad.get().strip())
            if cant <= 0:
                raise ValueError
        except ValueError:
            mb.showwarning("Cantidad", "Ingrese una cantidad válida mayor a 0.")
            return

        servs = (
            ServicioAdicionalService.SERVICIOS_FUNERARIA if self.tipo_velacion_actual == "Funeraria"
            else ServicioAdicionalService.SERVICIOS_DOMICILIO
        )
        s_data = servs[key]
        subt = s_data["precio"] * cant

        self.servicios_agregados.append({
            "key": key,
            "nombre": s_data["nombre"],
            "cantidad": cant,
            "precio": s_data["precio"],
            "subtotal": subt,
            "tipo": self.tipo_velacion_actual
        })

        self.actualizar_lista_servicios()
        self.actualizar_total()

    def actualizar_lista_servicios(self):
        for r in self.servicios_tree.get_children():
            self.servicios_tree.delete(r)
        for s in self.servicios_agregados:
            self.servicios_tree.insert("", "end", values=(
                s["nombre"], s["cantidad"], f"${s['precio']:.2f}", f"${s['subtotal']:.2f}"
            ))

    def toggle_horario_inmediato(self):
        if self.servicio_inmediato_var.get():
            hoy = datetime.datetime.now().strftime("%d/%m/%Y")
            self.fecha_velacion.delete(0, "end")
            self.fecha_velacion.insert(0, hoy)
            self.fecha_velacion.configure(state="disabled")
        else:
            self.fecha_velacion.configure(state="normal")
            self.fecha_velacion.delete(0, "end")
            self.fecha_velacion.insert(0, (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d/%m/%Y"))

    def toggle_financiamiento(self):
        es_fin = self.metodo_var.get() == "Financiado"
        for w in self.financiamiento_frame.winfo_children():
            if isinstance(w, ctk.CTkEntry):
                w.configure(state="normal" if es_fin else "disabled")

    # ========== CREACIÓN DE CONTRATOS ==========
    def crear_contrato(self):
        tipo_contrato = self.tipo_contrato_var.get()

        # Validación según tipo de contrato
        if tipo_contrato == "Inmediato":
            if not self.difunto_id_actual:
                mb.showwarning("Selección Obligatoria", "Para un contrato inmediato debe seleccionar el difunto fallecido.")
                return
            if not self.familia_id_actual:
                mb.showwarning("Error", "No se identificó la familia del difunto seleccionado.")
                return
            capilla_sel = self.capilla_combo.get()
            capilla_id = self.capilla_dict.get(capilla_sel)
            if not capilla_id:
                mb.showwarning("Selección Obligatoria", "Para un contrato inmediato debe seleccionar una capilla válida.")
                return
        else:  # Largo Plazo
            if not self.familia_id_actual:
                mb.showwarning("Titular Obligatorio", "Debe seleccionar la familia o titular contratante para el plan a largo plazo.")
                return
            capilla_sel = self.capilla_combo.get()
            capilla_id = self.capilla_dict.get(capilla_sel)  # Puede ser None

        # Validación de PNF
        pnf_asociado = 1 if self.pnf_var.get() else 0
        pnf_numero = self.pnf_num_entry.get().strip() if pnf_asociado else None
        if pnf_asociado and not pnf_numero:
            mb.showwarning("PNF", "Ingrese el número de póliza o certificado PNF.")
            return

        # Calcular desglose final y total
        total = self.actualizar_total()
        desglose = self.desglose_actual

        metodo = self.metodo_var.get()
        inicial = 0.0
        num_cuotas = 1

        if metodo == "Financiado":
            try:
                inicial = float(self.inicial_entry.get() or 0.0)
                if inicial < 0:
                    inicial = 0.0
                num_cuotas = int(self.cuotas_entry.get() or 1)
                if num_cuotas < 1:
                    num_cuotas = 1
            except ValueError:
                mb.showerror("Error", "Valores numéricos de financiamiento inválidos.")
                return

        # Validar disponibilidad de capilla si se asignó
        if capilla_id and tipo_contrato == "Inmediato":
            disponible, mensaje = ContratoService.validar_disponibilidad_capilla(
                capilla_id, self.fecha_velacion.get(),
                self.hora_planificada.get(), self.hora_fin.get()
            )
            if not disponible:
                mb.showerror("Capilla Ocupada", mensaje)
                return

        conn = obtener_conexion()
        c = conn.cursor()
        try:
            numero_contrato = ContratoService.generar_numero_contrato()

            traslado_raw = self.traslado_combo.get()
            tipo_traslado = "Local"
            if "Regional" in traslado_raw:
                tipo_traslado = "Regional"
            elif "Nacional" in traslado_raw:
                tipo_traslado = "Nacional"
            elif "Externo" in traslado_raw:
                tipo_traslado = "Externo"

            paquete = self.paquete_var.get()

            c.execute("""
                INSERT INTO contratos (
                    numero, fecha_contrato, familia_id, difunto_id, paquete,
                    capilla_id, fecha_velacion, hora_inicio, hora_fin,
                    monto_total, metodo_pago, inicial, numero_cuotas, pagado, estado, observaciones,
                    requiere_cremacion, tipo_traslado, hora_llegada_real, hora_salida_capilla, estado_servicio,
                    tipo_velacion, tipo_contrato, pnf_asociado, pnf_numero,
                    pnf_cubre_traslado, pnf_cubre_cremacion, descuento_pnf,
                    costo_paquete, costo_cremacion, costo_traslado, costo_productos, costo_servicios
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                numero_contrato, datetime.datetime.now().strftime("%Y-%m-%d"),
                self.familia_id_actual, self.difunto_id_actual, paquete,
                capilla_id,
                self.fecha_velacion.get() if tipo_contrato == "Inmediato" else "Plan a Futuro",
                self.hora_planificada.get(), self.hora_fin.get(),
                total, metodo, inicial, num_cuotas, 0.0, "Activo",
                self.observaciones.get("1.0", "end-1c").strip(),
                1 if self.cremacion_var.get() else 0,
                tipo_traslado,
                self.hora_llegada_real.get().strip() or None,
                self.hora_salida_capilla.get().strip() or None,
                "Pendiente",
                self.tipo_velacion_var.get(),
                tipo_contrato,
                pnf_asociado,
                pnf_numero,
                1 if self.pnf_cubre_traslado_var.get() else 0,
                1 if self.pnf_cubre_cremacion_var.get() else 0,
                desglose["descuento_pnf"],
                desglose["costo_paquete"],
                desglose["costo_cremacion"],
                desglose["costo_traslado"],
                desglose["costo_productos"],
                desglose["costo_servicios"]
            ))

            contrato_id = c.lastrowid

            # Insertar productos y descontar inventario
            for p in self.productos_agregados:
                c.execute("""
                    INSERT INTO contrato_productos (contrato_id, producto_id, cantidad, precio_unitario)
                    VALUES (?, ?, ?, ?)
                """, (contrato_id, p["id"], p["cantidad"], p["precio"]))
                c.execute("UPDATE inventario SET stock = stock - ? WHERE id = ?", (p["cantidad"], p["id"]))

            # Insertar servicios
            for s in self.servicios_agregados:
                c.execute("""
                    INSERT INTO contratos_servicios
                    (contrato_id, tipo_velacion, servicio_key, servicio_nombre, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (contrato_id, s["tipo"], s["key"], s["nombre"], s["cantidad"], s["precio"], s["subtotal"]))

            # Financiamiento y cuotas exactas
            if metodo == "Financiado" and num_cuotas > 0:
                saldo = max(0.0, total - inicial)
                cuotas = PrecioService.calcular_cuotas_exactas(saldo, num_cuotas)
                for i, monto_c in enumerate(cuotas, start=1):
                    venc = (datetime.datetime.now() + datetime.timedelta(days=30 * i)).strftime("%Y-%m-%d")
                    c.execute("""
                        INSERT INTO cuotas (contrato_id, numero, monto, fecha_vencimiento, estado)
                        VALUES (?, ?, ?, ?, 'Pendiente')
                    """, (contrato_id, i, monto_c, venc))

                if inicial > 0:
                    c.execute("""
                        INSERT INTO pagos (contrato_id, fecha, monto, metodo, moneda, monto_original)
                        VALUES (?, ?, ?, ?, 'USD', ?)
                    """, (contrato_id, datetime.datetime.now().strftime("%Y-%m-%d"), inicial, "Efectivo (USD)", inicial))
                    c.execute("UPDATE contratos SET pagado = pagado + ? WHERE id = ?", (inicial, contrato_id))

            # Si es Inmediato y tiene capilla, marcar capilla como Ocupada
            if capilla_id and tipo_contrato == "Inmediato":
                c.execute("UPDATE capillas SET estado = 'Ocupada' WHERE id = ?", (capilla_id,))

            conn.commit()

            ContratoRepository.registrar_bitacora(
                self.usuario[0],
                f"Creación Contrato {tipo_contrato}",
                f"Contrato {numero_contrato} creado por ${total:,.2f} (PNF: {pnf_asociado})"
            )

            mb.showinfo("Éxito", f"✅ Contrato {numero_contrato} ({tipo_contrato}) registrado correctamente.")

            # Ofrecer PDF
            if mb.askyesno("Generar PDF", "¿Desea generar el documento PDF del contrato ahora?"):
                from services.pdf_service import generar_pdf_contrato
                pdf_ruta = generar_pdf_contrato(contrato_id)
                if pdf_ruta and os.path.exists(pdf_ruta):
                    mb.showinfo("PDF Creado", f"Contrato guardado en:\n{pdf_ruta}")
                    try:
                        os.startfile(pdf_ruta)
                    except Exception:
                        pass

            self.limpiar_formulario()
            self.cargar_contratos()
            self.cargar_capillas()
            self.cargar_productos_combo()

        except Exception as e:
            conn.rollback()
            mb.showerror("Error al Guardar", f"No se pudo crear el contrato:\n{str(e)}")
        finally:
            conn.close()

    def limpiar_formulario(self):
        self.productos_agregados.clear()
        self.actualizar_lista_productos()
        self.servicios_agregados.clear()
        self.actualizar_lista_servicios()
        self.inicial_entry.delete(0, "end")
        self.cuotas_entry.delete(0, "end")
        self.observaciones.delete("1.0", "end")
        self.hora_llegada_real.delete(0, "end")
        self.hora_salida_capilla.delete(0, "end")
        self.cremacion_var.set(False)
        self.traslado_combo.set("Local ($0.00)")
        self.servicio_inmediato_var.set(False)
        self.pnf_var.set(False)
        self.toggle_pnf_campos()
        self.tipo_velacion_var.set("Funeraria")
        self.cambiar_tipo_velacion()
        self.fecha_velacion.configure(state="normal")
        self.fecha_velacion.delete(0, "end")
        self.fecha_velacion.insert(0, (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d/%m/%Y"))
        self.actualizar_total()
        self.cargar_difuntos_combo()

    # ========== CARGA DE CONTRATOS Y ACCIONES ==========
    def cargar_contratos(self):
        for r in self.contratos_tree.get_children():
            self.contratos_tree.delete(r)

        conn = obtener_conexion()
        c = conn.cursor()
        c.execute("""
            SELECT c.id, c.numero, COALESCE(c.tipo_contrato, 'Inmediato') as tipo,
                   COALESCE(d.nombre || ' ' || d.apellido, 'Por asignar (A futuro)') as difunto_nombre,
                   COALESCE(f.resp_nombre || ' ' || f.resp_apellido, 'Sin titular') as resp_nombre,
                   (SELECT COUNT(*) FROM contrato_beneficiarios cb WHERE cb.contrato_id = c.id) as num_ben,
                   c.paquete,
                   CASE WHEN c.pnf_asociado = 1 THEN 'Sí' ELSE 'No' END as tiene_pnf,
                   c.monto_total, c.estado
            FROM contratos c
            LEFT JOIN difuntos d ON c.difunto_id = d.id
            LEFT JOIN familias f ON c.familia_id = f.familia_id
            ORDER BY c.id DESC
        """)
        for row in c.fetchall():
            nben = row[5] or 0
            carga_str = f"👨‍👩‍👧‍👦 {nben} Beneficiario(s)" if nben > 0 else "Sin anexar"
            self.contratos_tree.insert("", "end", values=(
                row[0], row[1], row[2], row[3], row[4], carga_str, row[6], row[7], f"${row[8]:,.2f}", row[9]
            ))
        conn.close()

        # Mantener sincronizado el selector de contratos en la pestaña PNF
        self.cargar_contratos_pnf_combo()

    def cargar_contrato_en_pnf_desde_tabla(self):
        """Carga el contrato seleccionado de la tabla en la pestaña PNF para reflejar o anexar su Carga Familiar"""
        sel = self.contratos_tree.selection()
        if not sel:
            mb.showwarning("Selección Requerida", "Seleccione un contrato de la tabla para ver o anexar su Carga Familiar.")
            return
        cid = int(self.contratos_tree.item(sel[0])['values'][0])
        self.cargar_contratos_pnf_combo()
        self.cargar_contrato_existente_en_pnf(cid)
        self.tabview.set("🛡️ Plan Nacional Funerario (PNF)")

    def ver_contrato_seleccionado(self):
        sel = self.contratos_tree.selection()
        if not sel:
            mb.showwarning("Selección Requerida", "Seleccione un contrato de la tabla.")
            return
        cid = self.contratos_tree.item(sel[0])['values'][0]
        from ui.visor_contrato import VisorContrato
        VisorContrato(self, int(cid))

    def verificar_total_contrato_tabla(self):
        sel = self.contratos_tree.selection()
        if not sel:
            mb.showwarning("Selección Requerida", "Seleccione un contrato de la tabla.")
            return
        cid = int(self.contratos_tree.item(sel[0])['values'][0])
        num = self.contratos_tree.item(sel[0])['values'][1]
        desglose = PrecioService.verificar_contrato(cid)
        if desglose:
            mostrar_dialogo_verificar_total(self, desglose, f"Verificación de Costos - Contrato {num}")
        else:
            mb.showerror("Error", "No se pudo calcular el desglose del contrato.")

    def generar_pdf_seleccionado(self):
        sel = self.contratos_tree.selection()
        if not sel:
            mb.showwarning("Selección Requerida", "Seleccione un contrato de la tabla.")
            return
        cid = int(self.contratos_tree.item(sel[0])['values'][0])
        num = self.contratos_tree.item(sel[0])['values'][1]

        from services.pdf_service import generar_pdf_contrato
        pdf_ruta = generar_pdf_contrato(cid)
        if pdf_ruta and os.path.exists(pdf_ruta):
            mb.showinfo("PDF Generado", f"Contrato {num} generado correctamente:\n{pdf_ruta}")
            try:
                os.startfile(pdf_ruta)
            except Exception:
                pass
        else:
            mb.showerror("Error", "No se pudo generar el PDF del contrato.")

    # ========== MODALES DE HORARIOS Y REASIGNACIÓN DE CAPILLA ==========
    def abrir_dialogo_modificar_horario(self):
        """Abre ventana modal para modificar la hora de llegada del difunto y salida de capilla"""
        sel = self.contratos_tree.selection()
        if not sel:
            mb.showwarning("Selección Requerida", "Seleccione un contrato de la tabla.")
            return
        cid = int(self.contratos_tree.item(sel[0])['values'][0])
        numero = self.contratos_tree.item(sel[0])['values'][1]

        conn = obtener_conexion()
        c = conn.cursor()
        c.execute("""
            SELECT hora_llegada_real, hora_salida_capilla, estado_servicio, fecha_velacion, hora_inicio, hora_fin
            FROM contratos WHERE id = ?
        """, (cid,))
        row = c.fetchone()
        conn.close()

        if not row:
            mb.showerror("Error", "No se encontró el contrato.")
            return

        hora_llegada_actual = row[0] or ""
        hora_salida_actual = row[1] or ""
        estado_servicio_actual = row[2] or "Pendiente"
        fecha_vel = row[3] or ""

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Gestión de Horarios - Contrato {numero}")
        dialog.geometry("450x380")
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=f"⏰ Horarios de Velación y Llegada",
            font=("Segoe UI", 16, "bold"),
            text_color="#d4af37"
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            dialog,
            text=f"Contrato: {numero} | Fecha: {fecha_vel}",
            font=("Segoe UI", 12),
            text_color="gray"
        ).pack(pady=(0, 15))

        f_body = ctk.CTkFrame(dialog, fg_color="transparent")
        f_body.pack(fill="x", padx=30)

        ctk.CTkLabel(f_body, text="Hora Real de Llegada del Difunto a Funeraria:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
        e_llegada = ctk.CTkEntry(f_body, width=200, placeholder_text="Ej: 11:30")
        e_llegada.insert(0, hora_llegada_actual)
        e_llegada.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(f_body, text="Hora de Salida de Capilla:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
        e_salida = ctk.CTkEntry(f_body, width=200, placeholder_text="Ej: 16:00")
        e_salida.insert(0, hora_salida_actual)
        e_salida.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(f_body, text="Estado del Servicio Funerario:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
        c_estado = ctk.CTkComboBox(f_body, values=["Pendiente", "En Velación", "En Traslado", "En Cremación", "Finalizado"], state="readonly", width=220)
        c_estado.set(estado_servicio_actual)
        c_estado.pack(anchor="w", pady=(0, 15))

        def guardar_horarios():
            hl = e_llegada.get().strip() or None
            hs = e_salida.get().strip() or None
            es = c_estado.get()

            ok, msg = ContratoService.actualizar_horarios_llegada(cid, hl, hs, es)
            if ok:
                ContratoRepository.registrar_bitacora(
                    self.usuario[0],
                    "Modificación Horario Difunto",
                    f"Contrato {numero}: Llegada={hl}, Salida={hs}, Estado={es}"
                )
                mb.showinfo("Horario Actualizado", f"Horarios del difunto en contrato {numero} guardados.", parent=dialog)
                dialog.destroy()
                self.cargar_contratos()
            else:
                mb.showerror("Error", f"No se pudo actualizar: {msg}", parent=dialog)

        ctk.CTkButton(
            dialog,
            text="💾 Guardar Horarios",
            command=guardar_horarios,
            fg_color="#d4af37",
            text_color="black",
            font=("Segoe UI", 13, "bold"),
            height=38,
            width=200
        ).pack(pady=10)

    def abrir_dialogo_reasignar_capilla(self):
        """Abre ventana modal para reasignar la capilla de velación a un contrato"""
        sel = self.contratos_tree.selection()
        if not sel:
            mb.showwarning("Selección Requerida", "Seleccione un contrato de la tabla.")
            return
        cid = int(self.contratos_tree.item(sel[0])['values'][0])
        numero = self.contratos_tree.item(sel[0])['values'][1]

        conn = obtener_conexion()
        c = conn.cursor()
        c.execute("""
            SELECT c.capilla_id, cap.nombre, c.fecha_velacion
            FROM contratos c
            LEFT JOIN capillas cap ON c.capilla_id = cap.id
            WHERE c.id = ?
        """, (cid,))
        row = c.fetchone()
        conn.close()

        cap_actual_id = row[0] if row else None
        cap_actual_nombre = row[1] if row and row[1] else "Sin Capilla Asignada"

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Reasignar Capilla - Contrato {numero}")
        dialog.geometry("460x320")
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="🏛️ Reasignar Capilla de Velación",
            font=("Segoe UI", 16, "bold"),
            text_color="#d4af37"
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            dialog,
            text=f"Contrato: {numero}\nCapilla Actual: {cap_actual_nombre}",
            font=("Segoe UI", 12),
            text_color="#bdc3c7"
        ).pack(pady=(0, 15))

        capillas = CapillaRepository.obtener_todas()
        cap_dict = {f"{cap['nombre']} (Cap: {cap['capacidad']}p - {cap['estado']})": cap['id'] for cap in capillas}

        f_body = ctk.CTkFrame(dialog, fg_color="transparent")
        f_body.pack(fill="x", padx=30)

        ctk.CTkLabel(f_body, text="Seleccione la Nueva Capilla:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(5, 2))
        combo_cap = ctk.CTkComboBox(f_body, values=list(cap_dict.keys()), state="readonly", width=380)
        if cap_dict:
            combo_cap.set(list(cap_dict.keys())[0])
        combo_cap.pack(anchor="w", pady=(0, 15))

        def reasignar():
            sel_nombre = combo_cap.get()
            nueva_id = cap_dict.get(sel_nombre)
            if not nueva_id:
                mb.showwarning("Selección Inválida", "Seleccione una capilla válida.", parent=dialog)
                return

            ok, msg = ContratoService.reasignar_capilla(cid, nueva_id)
            if ok:
                ContratoRepository.registrar_bitacora(
                    self.usuario[0],
                    "Reasignación Capilla",
                    f"Contrato {numero} reasignado a capilla #{nueva_id}"
                )
                mb.showinfo("Capilla Reasignada", f"Capilla reasignada correctamente al contrato {numero}.", parent=dialog)
                dialog.destroy()
                self.cargar_contratos()
                self.cargar_capillas()
            else:
                mb.showerror("Error", f"No se pudo reasignar: {msg}", parent=dialog)

        ctk.CTkButton(
            dialog,
            text="🏛️ Confirmar Reasignación",
            command=reasignar,
            fg_color="#8e44ad",
            font=("Segoe UI", 13, "bold"),
            height=38,
            width=220
        ).pack(pady=10)