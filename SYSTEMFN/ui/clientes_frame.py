# ui/clientes_frame.py - Registro de FAMILIAS (Responsable + Múltiples Difuntos)
import customtkinter as ctk
import tkinter.messagebox as mb
from tkinter import ttk
import sqlite3
from services.cliente_service import ClienteService
from services.db_service import obtener_conexion, ContratoRepository
from utils.helpers import aplicar_estilo_treeview

class ClientesFrame(ctk.CTkFrame):
    """
    Nuevo flujo:
    1. Se registra la FAMILIA (responsable) UNA sola vez
    2. Se pueden agregar MÚLTIPLES difuntos a la misma familia
    3. ID único de familia: FAM-YYYYMMDD-XXX
    """
    
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.familia_seleccionada = None
        self.crear_interfaz()
        self.cargar_familias()
    
    def crear_interfaz(self):
        ctk.CTkLabel(self, text="Registro de Familias", font=("Segoe UI", 28, "bold"),
                     text_color="#d4af37").pack(pady=20)
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        tab_familias = self.tabview.add("🏠 Familias Registradas")
        tab_nueva_familia = self.tabview.add("➕ Nueva Familia")
        tab_agregar_difunto = self.tabview.add("👤 Agregar Difunto")
        tab_buscar = self.tabview.add("🔍 Buscar")
        
        # ========== TAB: FAMILIAS REGISTRADAS ==========
        self.crear_tabla_familias(tab_familias)
        
        # ========== TAB: NUEVA FAMILIA ==========
        self.crear_formulario_nueva_familia(tab_nueva_familia)
        
        # ========== TAB: AGREGAR DIFUNTO A FAMILIA EXISTENTE ==========
        self.crear_formulario_agregar_difunto(tab_agregar_difunto)
        
        # ========== TAB: BUSCAR ==========
        self.crear_buscador(tab_buscar)
    
    def crear_tabla_familias(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("familia_id", "resp_cedula", "resp_nombre", "resp_telefono", "num_difuntos")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("familia_id", text="ID Familia")
        self.tree.heading("resp_cedula", text="Cédula Responsable")
        self.tree.heading("resp_nombre", text="Responsable")
        self.tree.heading("resp_telefono", text="Teléfono")
        self.tree.heading("num_difuntos", text="Difuntos")
        
        self.tree.column("familia_id", width=150)
        self.tree.column("resp_cedula", width=120)
        self.tree.column("resp_nombre", width=200)
        self.tree.column("resp_telefono", width=120)
        self.tree.column("num_difuntos", width=80)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Botón ver difuntos
        btn_frame = ctk.CTkFrame(parent)
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="📋 Ver Difuntos de Familia", command=self.ver_difuntos_familia,
                     fg_color="#3498db").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🔄 Actualizar", command=self.cargar_familias,
                     fg_color="gray").pack(side="left", padx=5)
        
        aplicar_estilo_treeview()
    
    def crear_formulario_nueva_familia(self, parent):
        form_frame = ctk.CTkFrame(parent)
        form_frame.pack(pady=20, padx=20, fill="x")

        # Mensaje de estado de búsqueda por cédula
        self.responsable_status_label = ctk.CTkLabel(
            form_frame,
            text="Ingrese la cédula del responsable para verificar si ya existe en el sistema.",
            font=("Segoe UI", 12, "italic"),
            text_color="gray"
        )
        self.responsable_status_label.pack(anchor="w", padx=15, pady=(10, 5))

        campos = [
            ("Cédula del Responsable:*", "cedula"),
            ("Nombre:*", "nombre"),
            ("Apellido:*", "apellido"),
            ("Teléfono:", "telefono"),
            ("Email:", "email"),
            ("Dirección:", "direccion")
        ]

        self.familia_entries = {}
        for label, key in campos:
            frame = ctk.CTkFrame(form_frame)
            frame.pack(fill="x", pady=4)
            ctk.CTkLabel(frame, text=label, width=200, anchor="w").pack(side="left", padx=10)
            entry = ctk.CTkEntry(frame, width=300)
            entry.pack(side="left", padx=10)
            self.familia_entries[key] = entry

            if key == "cedula":
                # Botón de verificación y eventos
                ctk.CTkButton(
                    frame,
                    text="🔍 Verificar Cédula",
                    command=self.verificar_cedula_responsable,
                    fg_color="#3498db",
                    width=130
                ).pack(side="left", padx=5)
                entry.bind("<KeyRelease>", lambda e: self.verificar_cedula_responsable())
                entry.bind("<FocusOut>", lambda e: self.verificar_cedula_responsable())

        btn_row = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_row.pack(pady=20)

        ctk.CTkButton(
            btn_row,
            text="✅ Registrar Familia",
            command=self.registrar_familia,
            fg_color="#d4af37",
            text_color="black",
            height=40,
            width=200,
            font=("Segoe UI", 13, "bold")
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_row,
            text="🧹 Limpiar Campos",
            command=self.limpiar_formulario_familia,
            fg_color="gray",
            height=40,
            width=150
        ).pack(side="left", padx=10)

    def verificar_cedula_responsable(self):
        """Verifica en tiempo real si la cédula ingresada ya pertenece a un familiar responsable."""
        cedula = self.familia_entries['cedula'].get().strip()
        if len(cedula) < 4:
            self.responsable_status_label.configure(
                text="Ingrese la cédula del responsable para verificar si ya existe en el sistema.",
                text_color="gray"
            )
            return

        familia = ClienteService.buscar_familia_por_cedula(cedula)
        if familia:
            # Auto-llenar campos con los datos del responsable existente
            self.familia_entries['nombre'].delete(0, 'end')
            self.familia_entries['nombre'].insert(0, familia['resp_nombre'])

            self.familia_entries['apellido'].delete(0, 'end')
            self.familia_entries['apellido'].insert(0, familia['resp_apellido'])

            self.familia_entries['telefono'].delete(0, 'end')
            self.familia_entries['telefono'].insert(0, familia['resp_telefono'] or "")

            self.familia_entries['email'].delete(0, 'end')
            self.familia_entries['email'].insert(0, familia['resp_email'] or "")

            self.familia_entries['direccion'].delete(0, 'end')
            self.familia_entries['direccion'].insert(0, familia['resp_direccion'] or "")

            num_dif = len(familia.get('difuntos', []))
            self.responsable_status_label.configure(
                text=f"✓ Responsable ya existe: {familia['resp_nombre']} {familia['resp_apellido']} "
                     f"(ID: {familia['familia_id']} | {num_dif} difuntos registrados). Datos autocompletados.",
                text_color="#2ecc71"
            )
        else:
            self.responsable_status_label.configure(
                text=f"ℹ️ Cédula '{cedula}' disponible (nuevo responsable).",
                text_color="#f39c12"
            )

    def limpiar_formulario_familia(self):
        for entry in self.familia_entries.values():
            entry.delete(0, 'end')
        self.responsable_status_label.configure(
            text="Ingrese la cédula del responsable para verificar si ya existe en el sistema.",
            text_color="gray"
        )

    def crear_formulario_agregar_difunto(self, parent):
        info_frame = ctk.CTkFrame(parent)
        info_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="ASIGNACIÓN DE FAMILIA / FAMILIAR RESPONSABLE",
            font=("Segoe UI", 13, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", pady=(5, 5))

        # Búsqueda rápida por cédula del responsable
        busq_resp_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        busq_resp_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(busq_resp_frame, text="Buscar Familiar por Cédula:").pack(side="left", padx=5)
        self.buscar_resp_entry = ctk.CTkEntry(busq_resp_frame, width=200, placeholder_text="Ej: V-12345678")
        self.buscar_resp_entry.pack(side="left", padx=5)
        self.buscar_resp_entry.bind("<KeyRelease>", lambda e: self.buscar_responsable_por_cedula_difunto())
        self.buscar_resp_entry.bind("<FocusOut>", lambda e: self.buscar_responsable_por_cedula_difunto())

        ctk.CTkButton(
            busq_resp_frame,
            text="🔍 Buscar",
            command=self.buscar_responsable_por_cedula_difunto,
            fg_color="#3498db",
            width=100
        ).pack(side="left", padx=5)

        # Selector de Familia
        combo_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        combo_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(combo_frame, text="O Seleccionar de la Lista:").pack(side="left", padx=5)
        self.familia_combo = ctk.CTkComboBox(combo_frame, width=380, state="readonly", command=self.on_familia_combo_selected)
        self.familia_combo.pack(side="left", padx=5)

        ctk.CTkButton(
            combo_frame,
            text="↻ Actualizar",
            command=self.cargar_familias_combo,
            fg_color="gray",
            width=90
        ).pack(side="left", padx=5)

        # Badge con información del responsable seleccionado
        self.resp_difunto_info_label = ctk.CTkLabel(
            info_frame,
            text="Seleccione una familia o ingrese la cédula del responsable.",
            font=("Segoe UI", 11, "bold"),
            text_color="gray"
        )
        self.resp_difunto_info_label.pack(anchor="w", pady=5)

        self.cargar_familias_combo()

        # Formulario difunto
        form_frame = ctk.CTkFrame(parent)
        form_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(
            form_frame,
            text="DATOS DEL DIFUNTO (NUEVO FALLECIDO)",
            font=("Segoe UI", 14, "bold"),
            text_color="#d4af37"
        ).pack(anchor="w", pady=(10, 5))

        self.difunto_status_label = ctk.CTkLabel(
            form_frame,
            text="",
            font=("Segoe UI", 11, "italic"),
            text_color="gray"
        )
        self.difunto_status_label.pack(anchor="w", pady=(0, 5))

        campos_dif = [
            ("Cédula:*", "dif_cedula"),
            ("Nombre:*", "dif_nombre"),
            ("Apellido:*", "dif_apellido"),
            ("Fecha Nacimiento (DD/MM/AAAA):", "dif_fecha_nac"),
            ("Fecha Defunción (DD/MM/AAAA):", "dif_fecha_def"),
            ("Causa de Muerte:", "dif_causa")
        ]

        self.dif_entries = {}
        for label, key in campos_dif:
            frame = ctk.CTkFrame(form_frame)
            frame.pack(fill="x", pady=3)
            ctk.CTkLabel(frame, text=label, width=200, anchor="w").pack(side="left", padx=10)
            entry = ctk.CTkEntry(frame, width=300)
            entry.pack(side="left", padx=10)
            self.dif_entries[key] = entry

            if key == "dif_cedula":
                entry.bind("<KeyRelease>", lambda e: self.verificar_cedula_difunto())
                entry.bind("<FocusOut>", lambda e: self.verificar_cedula_difunto())

        ctk.CTkButton(
            form_frame,
            text="➕ Registrar Difunto en la Familia",
            command=self.agregar_difunto,
            fg_color="#2ecc71",
            text_color="black",
            height=40,
            width=280,
            font=("Segoe UI", 13, "bold")
        ).pack(pady=20)

    def buscar_responsable_por_cedula_difunto(self):
        """Busca el responsable por cédula y auto-selecciona su familia en el combobox de difunto"""
        cedula = self.buscar_resp_entry.get().strip()
        if not cedula or len(cedula) < 4:
            return

        familia = ClienteService.buscar_familia_por_cedula(cedula)
        if familia:
            fid = familia['familia_id']
            # Buscar en las opciones del combobox
            opciones = list(self.familia_combo.cget("values"))
            for op in opciones:
                if op.startswith(fid):
                    self.familia_combo.set(op)
                    break
            self.resp_difunto_info_label.configure(
                text=f"✓ Familiar Responsable: {familia['resp_nombre']} {familia['resp_apellido']} | "
                     f"Tel: {familia['resp_telefono'] or 'S/T'} | Dir: {familia['resp_direccion'] or 'S/D'} "
                     f"(Familia ID: {fid})",
                text_color="#2ecc71"
            )
        else:
            self.resp_difunto_info_label.configure(
                text=f"⚠️ No se encontró responsable con cédula '{cedula}'. Regístrelo en '➕ Nueva Familia'.",
                text_color="#e67e22"
            )

    def on_familia_combo_selected(self, valor):
        if not valor or "--" in valor:
            return
        fid = valor.split(" - ")[0]
        conn = obtener_conexion()
        c = conn.cursor()
        c.execute("SELECT resp_cedula, resp_nombre, resp_apellido, resp_telefono, resp_direccion FROM familias WHERE familia_id = ?", (fid,))
        row = c.fetchone()
        conn.close()
        if row:
            self.resp_difunto_info_label.configure(
                text=f"✓ Familiar Responsable: {row[1]} {row[2]} (C.I: {row[0]}) | Tel: {row[3] or 'S/T'} | Dir: {row[4] or 'S/D'}",
                text_color="#2ecc71"
            )

    def verificar_cedula_difunto(self):
        """Verifica si la cédula del difunto ya está en la base de datos"""
        cedula = self.dif_entries['dif_cedula'].get().strip()
        if len(cedula) < 4:
            self.difunto_status_label.configure(text="")
            return
        from services.db_service import FamiliaRepository
        dif = FamiliaRepository.buscar_difunto_por_cedula(cedula)
        if dif:
            self.difunto_status_label.configure(
                text=f"⚠️ Esta cédula ya pertenece a un difunto registrado: {dif['nombre']} {dif['apellido']} (Responsable: {dif['responsable']})",
                text_color="#e74c3c"
            )
        else:
            self.difunto_status_label.configure(
                text="✓ Cédula de difunto disponible para registro.",
                text_color="#2ecc71"
            )
    
    def crear_buscador(self, parent):
        search_frame = ctk.CTkFrame(parent)
        search_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(search_frame, text="Buscar por Cédula o Nombre:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(search_frame, width=250)
        self.search_entry.pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="🔍 Buscar", command=self.buscar_familias,
                     fg_color="#3498db").pack(side="left", padx=5)
        
        self.search_result = ctk.CTkTextbox(parent, height=300, width=700)
        self.search_result.pack(pady=10, padx=20, fill="both", expand=True)
    
    def cargar_familias(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        familias = ClienteService.listar_todas_familias()
        for f in familias:
            self.tree.insert("", "end", values=(
                f['familia_id'],
                f['resp_cedula'],
                f['resp_nombre_completo'],
                f['resp_telefono'],
                f['num_difuntos']
            ))
    
    def cargar_familias_combo(self):
        familias = ClienteService.listar_todas_familias()
        opciones = [f"{f['familia_id']} - {f['resp_nombre_completo']}" for f in familias]
        if opciones:
            self.familia_combo.configure(values=opciones)
            self.familia_combo.set(opciones[0])
        else:
            self.familia_combo.configure(values=["-- No hay familias registradas --"])
    
    def registrar_familia(self):
        if not self.familia_entries['cedula'].get():
            mb.showwarning("Campo requerido", "La cédula del responsable es obligatoria")
            return
        if not self.familia_entries['nombre'].get() or not self.familia_entries['apellido'].get():
            mb.showwarning("Campo requerido", "Nombre y apellido del responsable son obligatorios")
            return
        
        try:
            resp_data = {
                'cedula': self.familia_entries['cedula'].get(),
                'nombre': self.familia_entries['nombre'].get(),
                'apellido': self.familia_entries['apellido'].get(),
                'telefono': self.familia_entries['telefono'].get(),
                'email': self.familia_entries['email'].get(),
                'direccion': self.familia_entries['direccion'].get()
            }
            
            familia_id = ClienteService.registrar_familia(resp_data)
            ContratoRepository.registrar_bitacora(self.usuario[0], "Registro de familia", 
                                                  f"Familia {familia_id} registrada")
            
            mb.showinfo("Éxito", f"Familia registrada correctamente\nID: {familia_id}")
            
            # Limpiar campos
            for entry in self.familia_entries.values():
                entry.delete(0, 'end')
            
            self.cargar_familias()
            self.cargar_familias_combo()
            
        except sqlite3.IntegrityError:
            resp_cedula = self.familia_entries['cedula'].get().strip()
            fam = ClienteService.buscar_familia_por_cedula(resp_cedula)
            if fam:
                resp = mb.askyesno(
                    "Responsable Ya Registrado",
                    f"El familiar con cédula {resp_cedula} ya está registrado:\n"
                    f"{fam['resp_nombre']} {fam['resp_apellido']} (Familia ID: {fam['familia_id']})\n\n"
                    f"¿Desea actualizar su teléfono, email y dirección con los nuevos datos ingresados?"
                )
                if resp:
                    conn = obtener_conexion()
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE familias SET resp_telefono = ?, resp_email = ?, resp_direccion = ?
                        WHERE familia_id = ?
                    """, (resp_data.get('telefono', ''), resp_data.get('email', ''), resp_data.get('direccion', ''), fam['familia_id']))
                    conn.commit()
                    conn.close()
                    mb.showinfo("Actualizado", f"Datos del familiar {fam['familia_id']} actualizados correctamente.")
                    self.cargar_familias()
                    self.cargar_familias_combo()
                    return
            mb.showerror("Error", "Ya existe una familia registrada con esa cédula")
        except Exception as e:
            mb.showerror("Error", f"No se pudo registrar: {str(e)}")
    
    def agregar_difunto(self):
        seleccion = self.familia_combo.get()
        if not seleccion or "-- No hay familias" in seleccion:
            mb.showwarning("Selección", "Seleccione una familia primero")
            return
        
        familia_id = seleccion.split(" - ")[0]
        
        if not self.dif_entries['dif_cedula'].get():
            mb.showwarning("Campo requerido", "La cédula del difunto es obligatoria")
            return
        
        try:
            from utils.helpers import normalizar_fecha_iso
            f_nac = self.dif_entries['dif_fecha_nac'].get().strip()
            f_def = self.dif_entries['dif_fecha_def'].get().strip()
            difunto_data = {
                'cedula': self.dif_entries['dif_cedula'].get(),
                'nombre': self.dif_entries['dif_nombre'].get(),
                'apellido': self.dif_entries['dif_apellido'].get(),
                'fecha_nacimiento': normalizar_fecha_iso(f_nac) if f_nac else None,
                'fecha_defuncion': normalizar_fecha_iso(f_def) if f_def else None,
                'causa_muerte': self.dif_entries['dif_causa'].get() or None
            }
            
            difunto_id = ClienteService.agregar_difunto_a_familia(familia_id, difunto_data)
            ContratoRepository.registrar_bitacora(self.usuario[0], "Agregar difunto",
                                                  f"Difunto agregado a familia {familia_id}")
            
            mb.showinfo("Éxito", f"Difunto agregado correctamente a la familia {familia_id}")
            
            # Limpiar campos
            for entry in self.dif_entries.values():
                entry.delete(0, 'end')
            
            self.cargar_familias()
            
        except sqlite3.IntegrityError:
            mb.showerror("Error", "Ya existe un difunto con esa cédula")
        except Exception as e:
            mb.showerror("Error", f"No se pudo agregar: {str(e)}")
    
    def ver_difuntos_familia(self):
        seleccion = self.tree.selection()
        if not seleccion:
            mb.showwarning("Selección", "Seleccione una familia de la lista")
            return
        
        item = self.tree.item(seleccion[0])
        familia_id = item['values'][0]
        
        difuntos = ClienteService.obtener_difuntos_por_familia(familia_id)
        
        if not difuntos:
            mb.showinfo("Sin difuntos", "Esta familia no tiene difuntos registrados")
            return
        
        # Mostrar en ventana emergente
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Difuntos de {familia_id}")
        dialog.geometry("500x400")
        dialog.grab_set()
        
        text_area = ctk.CTkTextbox(dialog, width=480, height=350)
        text_area.pack(padx=10, pady=10, fill="both", expand=True)
        
        from utils.helpers import formatear_fecha_ddmmyyyy
        for d in difuntos:
            text_area.insert("end", f"ID: {d['id']}\n")
            text_area.insert("end", f"Cédula: {d['cedula']}\n")
            text_area.insert("end", f"Nombre: {d['nombre_completo']}\n")
            f_def_fmt = formatear_fecha_ddmmyyyy(d['fecha_defuncion']) if d['fecha_defuncion'] else 'N/E'
            text_area.insert("end", f"Fecha Defunción: {f_def_fmt}\n")
            text_area.insert("end", f"Causa: {d['causa_muerte'] or 'N/E'}\n")
            text_area.insert("end", "-" * 40 + "\n")
        
        text_area.configure(state="disabled")
    
    def buscar_familias(self):
        texto = self.search_entry.get().strip()
        if not texto:
            mb.showwarning("Texto requerido", "Ingrese cédula o nombre para buscar")
            return
        
        resultados = ClienteService.buscar_por_texto(texto)
        
        self.search_result.delete("1.0", "end")
        if resultados:
            for r in resultados:
                self.search_result.insert("end", 
                    f"ID Familia: {r['familia_id']}\n"
                    f"Cédula: {r['resp_cedula']}\n"
                    f"Responsable: {r['resp_nombre_completo']}\n"
                    f"Teléfono: {r['resp_telefono']}\n"
                    f"{'-'*40}\n")
        else:
            self.search_result.insert("end", "No se encontraron familias con ese criterio")