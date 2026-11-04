# ui/capillas_frame.py - Gestión completa y modificación de capillas de velación
import customtkinter as ctk
import tkinter.messagebox as mb
from tkinter import ttk
from services.db_service import CapillaRepository, ContratoRepository
from utils.helpers import aplicar_estilo_treeview

ESTADOS_VALIDOS = ["Disponible", "Ocupada", "Mantenimiento"]

class CapillasFrame(ctk.CTkFrame):
    """
    Panel para gestión, modificación y control de estado de las capillas de velación.
    Permite:
    - Ver todas las capillas registradas y su estado en tiempo real.
    - Modificar nombre, capacidad, descripción y estado (Disponible/Ocupada/Mantenimiento).
    - Registrar nuevas capillas.
    - Cambios rápidos de estado con un clic.
    """

    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.capilla_seleccionada_id = None
        self.crear_interfaz()
        self.cargar_capillas()

    def crear_interfaz(self):
        # Cabecera
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header,
            text="🏛️ Gestión y Modificación de Capillas",
            font=("Segoe UI", 26, "bold"),
            text_color="#d4af37"
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="➕ Nueva Capilla",
            command=self.abrir_dialogo_nueva_capilla,
            fg_color="#2ecc71",
            text_color="black",
            font=("Segoe UI", 12, "bold"),
            width=140
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            header,
            text="🔄 Actualizar",
            command=self.cargar_capillas,
            fg_color="gray",
            font=("Segoe UI", 12),
            width=100
        ).pack(side="right", padx=5)

        # Contenedor principal con 2 columnas (Tabla a la izquierda, detalles/edición a la derecha)
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        content_frame.grid_columnconfigure(0, weight=3)
        content_frame.grid_columnconfigure(1, weight=2)
        content_frame.grid_rowconfigure(0, weight=1)

        # --- Panel Izquierdo: Tabla de Capillas ---
        tabla_card = ctk.CTkFrame(content_frame)
        tabla_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ctk.CTkLabel(
            tabla_card,
            text="Capillas Registradas",
            font=("Segoe UI", 16, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", padx=15, pady=(15, 5))

        columns = ("id", "nombre", "capacidad", "estado", "descripcion")
        self.tree = ttk.Treeview(tabla_card, columns=columns, show="headings", height=14)
        self.tree.heading("id", text="ID")
        self.tree.heading("nombre", text="Nombre Capilla")
        self.tree.heading("capacidad", text="Capacidad (pers.)")
        self.tree.heading("estado", text="Estado Actual")
        self.tree.heading("descripcion", text="Descripción")

        self.tree.column("id", width=45, anchor="center")
        self.tree.column("nombre", width=170)
        self.tree.column("capacidad", width=110, anchor="center")
        self.tree.column("estado", width=120, anchor="center")
        self.tree.column("descripcion", width=220)

        scrollbar = ttk.Scrollbar(tabla_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 15), pady=10)

        self.tree.bind("<<TreeviewSelect>>", self.on_capilla_seleccionada)
        self.tree.bind("<Double-1>", lambda e: self.cargar_datos_en_formulario())

        # --- Panel Derecho: Modificación Rápida ---
        self.form_card = ctk.CTkFrame(content_frame)
        self.form_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        ctk.CTkLabel(
            self.form_card,
            text="Editar / Modificar Capilla",
            font=("Segoe UI", 16, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", padx=15, pady=(15, 5))

        self.info_id_label = ctk.CTkLabel(
            self.form_card,
            text="Seleccione una capilla de la lista",
            font=("Segoe UI", 12),
            text_color="gray"
        )
        self.info_id_label.pack(anchor="w", padx=15, pady=(0, 10))

        # Campos de edición
        ctk.CTkLabel(self.form_card, text="Nombre de la Capilla:*", font=("Segoe UI", 12)).pack(anchor="w", padx=15, pady=(5, 2))
        self.nombre_entry = ctk.CTkEntry(self.form_card, width=280)
        self.nombre_entry.pack(anchor="w", padx=15, pady=(0, 8))

        ctk.CTkLabel(self.form_card, text="Capacidad (Personas):*", font=("Segoe UI", 12)).pack(anchor="w", padx=15, pady=(5, 2))
        self.capacidad_entry = ctk.CTkEntry(self.form_card, width=150)
        self.capacidad_entry.pack(anchor="w", padx=15, pady=(0, 8))

        ctk.CTkLabel(self.form_card, text="Estado de la Capilla:*", font=("Segoe UI", 12)).pack(anchor="w", padx=15, pady=(5, 2))
        self.estado_combo = ctk.CTkComboBox(self.form_card, values=ESTADOS_VALIDOS, state="readonly", width=200)
        self.estado_combo.pack(anchor="w", padx=15, pady=(0, 8))

        ctk.CTkLabel(self.form_card, text="Descripción / Equipamiento:", font=("Segoe UI", 12)).pack(anchor="w", padx=15, pady=(5, 2))
        self.desc_text = ctk.CTkTextbox(self.form_card, height=80, width=300)
        self.desc_text.pack(anchor="w", padx=15, pady=(0, 15))

        # Botones de acción del formulario
        btn_action_frame = ctk.CTkFrame(self.form_card, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=15, pady=5)

        self.btn_guardar = ctk.CTkButton(
            btn_action_frame,
            text="💾 Guardar Cambios",
            command=self.guardar_modificaciones,
            fg_color="#d4af37",
            text_color="black",
            font=("Segoe UI", 13, "bold"),
            height=38
        )
        self.btn_guardar.pack(fill="x", pady=4)

        # Acciones rápidas de estado
        ctk.CTkLabel(self.form_card, text="Cambio Rápido de Estado:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=15, pady=(15, 4))
        quick_frame = ctk.CTkFrame(self.form_card, fg_color="transparent")
        quick_frame.pack(fill="x", padx=15, pady=2)

        ctk.CTkButton(
            quick_frame,
            text="🟢 Disponible",
            command=lambda: self.cambiar_estado_rapido("Disponible"),
            fg_color="#27ae60",
            width=90,
            height=30
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            quick_frame,
            text="🔴 Ocupada",
            command=lambda: self.cambiar_estado_rapido("Ocupada"),
            fg_color="#c0392b",
            width=90,
            height=30
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            quick_frame,
            text="🟡 Mantenimiento",
            command=lambda: self.cambiar_estado_rapido("Mantenimiento"),
            fg_color="#d35400",
            width=105,
            height=30
        ).pack(side="left", padx=2)

        aplicar_estilo_treeview()

    def cargar_capillas(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        capillas = CapillaRepository.obtener_todas()
        for c in capillas:
            estado_icono = "🟢 " if c['estado'] == "Disponible" else ("🔴 " if c['estado'] == "Ocupada" else "🟡 ")
            self.tree.insert("", "end", values=(
                c['id'],
                c['nombre'],
                c['capacidad'],
                f"{estado_icono}{c['estado']}",
                c['descripcion'] or ""
            ))

    def on_capilla_seleccionada(self, event):
        self.cargar_datos_en_formulario()

    def cargar_datos_en_formulario(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        cid, nombre, capacidad, estado_str, desc = item['values']
        self.capilla_seleccionada_id = int(cid)

        # Limpiar icono
        estado = estado_str.replace("🟢 ", "").replace("🔴 ", "").replace("🟡 ", "").strip()

        self.info_id_label.configure(
            text=f"Editando Capilla ID #{cid}: {nombre}",
            text_color="#d4af37"
        )
        self.nombre_entry.delete(0, "end")
        self.nombre_entry.insert(0, str(nombre))

        self.capacidad_entry.delete(0, "end")
        self.capacidad_entry.insert(0, str(capacidad))

        if estado in ESTADOS_VALIDOS:
            self.estado_combo.set(estado)

        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("1.0", str(desc or ""))

    def guardar_modificaciones(self):
        if not self.capilla_seleccionada_id:
            mb.showwarning("Selección Requerida", "Seleccione una capilla de la tabla para modificar.")
            return

        nombre = self.nombre_entry.get().strip()
        if not nombre:
            mb.showwarning("Campo Obligatorio", "El nombre de la capilla no puede estar vacío.")
            return

        try:
            capacidad = int(self.capacidad_entry.get().strip())
            if capacidad <= 0:
                raise ValueError
        except ValueError:
            mb.showwarning("Valor Inválido", "La capacidad debe ser un número entero mayor a 0.")
            return

        estado = self.estado_combo.get()
        descripcion = self.desc_text.get("1.0", "end-1c").strip()

        ok, msg = CapillaRepository.actualizar(
            self.capilla_seleccionada_id,
            nombre=nombre,
            capacidad=capacidad,
            descripcion=descripcion,
            estado=estado
        )

        if ok:
            ContratoRepository.registrar_bitacora(
                self.usuario[0],
                "Modificación Capilla",
                f"Capilla #{self.capilla_seleccionada_id} ({nombre}) modificada a estado {estado}"
            )
            mb.showinfo("Éxito", f"Capilla '{nombre}' actualizada correctamente.")
            self.cargar_capillas()
        else:
            mb.showerror("Error", f"No se pudo actualizar la capilla: {msg}")

    def cambiar_estado_rapido(self, nuevo_estado: str):
        if not self.capilla_seleccionada_id:
            mb.showwarning("Selección Requerida", "Seleccione una capilla de la lista primero.")
            return

        ok, msg = CapillaRepository.cambiar_estado(self.capilla_seleccionada_id, nuevo_estado)
        if ok:
            self.estado_combo.set(nuevo_estado)
            ContratoRepository.registrar_bitacora(
                self.usuario[0],
                "Cambio Estado Capilla",
                f"Capilla #{self.capilla_seleccionada_id} cambio de estado a {nuevo_estado}"
            )
            self.cargar_capillas()
            mb.showinfo("Estado Actualizado", f"Estado de la capilla cambiado a '{nuevo_estado}'.")
        else:
            mb.showerror("Error", f"No se pudo cambiar el estado: {msg}")

    def abrir_dialogo_nueva_capilla(self):
        """Abre ventana modal para crear una nueva capilla"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nueva Capilla de Velación")
        dialog.geometry("450x420")
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="🏛️ Registrar Nueva Capilla",
            font=("Segoe UI", 18, "bold"),
            text_color="#d4af37"
        ).pack(pady=(20, 15))

        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="x", padx=30)

        ctk.CTkLabel(form, text="Nombre de la Capilla:*", font=("Segoe UI", 12)).pack(anchor="w", pady=(5, 2))
        n_entry = ctk.CTkEntry(form, width=350, placeholder_text="Ej: Capilla Señorial San Juan")
        n_entry.pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(form, text="Capacidad (Personas):*", font=("Segoe UI", 12)).pack(anchor="w", pady=(5, 2))
        c_entry = ctk.CTkEntry(form, width=150, placeholder_text="Ej: 50")
        c_entry.pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(form, text="Estado Inicial:", font=("Segoe UI", 12)).pack(anchor="w", pady=(5, 2))
        e_combo = ctk.CTkComboBox(form, values=ESTADOS_VALIDOS, state="readonly", width=200)
        e_combo.set("Disponible")
        e_combo.pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(form, text="Descripción / Equipamiento:", font=("Segoe UI", 12)).pack(anchor="w", pady=(5, 2))
        d_text = ctk.CTkTextbox(form, height=70, width=350)
        d_text.pack(anchor="w", pady=(0, 15))

        def guardar_nueva():
            nombre = n_entry.get().strip()
            if not nombre:
                mb.showwarning("Campo Obligatorio", "Ingrese el nombre de la capilla.", parent=dialog)
                return
            try:
                capacidad = int(c_entry.get().strip())
                if capacidad <= 0:
                    raise ValueError
            except ValueError:
                mb.showwarning("Valor Inválido", "La capacidad debe ser un número entero mayor a 0.", parent=dialog)
                return

            estado = e_combo.get()
            desc = d_text.get("1.0", "end-1c").strip()

            cid = CapillaRepository.crear(nombre, capacidad, desc, estado)
            if cid:
                ContratoRepository.registrar_bitacora(
                    self.usuario[0],
                    "Creación de Capilla",
                    f"Capilla #{cid} ({nombre}) registrada con estado {estado}"
                )
                mb.showinfo("Éxito", f"Capilla '{nombre}' registrada con ID #{cid}.", parent=dialog)
                dialog.destroy()
                self.cargar_capillas()
            else:
                mb.showerror("Error", "No se pudo registrar la capilla.", parent=dialog)

        ctk.CTkButton(
            dialog,
            text="✅ Crear Capilla",
            command=guardar_nueva,
            fg_color="#2ecc71",
            text_color="black",
            font=("Segoe UI", 13, "bold"),
            height=38,
            width=200
        ).pack(pady=10)

