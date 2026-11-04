# main.py - Aplicación principal del sistema funerario
import sys
import os

# Agregar el directorio actual al path para poder importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from tkinter import ttk
import tkinter.messagebox as mb
import datetime
from services.db_service import obtener_conexion, init_db, ContratoRepository
from services.auth_service import (
    autenticar, configurar_administrador, obtener_configuracion_administrador,
)
from services.cliente_service import ClienteService
from services.contrato_service import ContratoService
from utils.helpers import aplicar_estilo_treeview, centrar_ventana

# Importar frames UI
from ui.dashboard_frame import DashboardFrame
from ui.clientes_frame import ClientesFrame
from ui.contratos_frame import ContratosFrame
from ui.pagos_frame import PagosFrame
from ui.inventario_frame import InventarioFrame
from ui.reportes_frame import ReportesFrame
from ui.capillas_frame import CapillasFrame
from ui.solvencias_frame import SolvenciasFrame

# Configuración inicial de customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Datos de la empresa (para mostrar en sidebar)
EMPRESA = {
    "nombre": "SERVICIOS MEMORIALES ALTAGRACIA C.A.",
    "rif": "J-41234567-8",
    "direccion": "Carrera 13 entre Calles 9 y 10, Calabozo, Estado Guárico, Venezuela",
    "telefono": "+58 246-1234567",
    "correo": "contacto@memorialesaltagracia.com"
}


class LoginWindow(ctk.CTkToplevel):
    """Ventana de login independiente"""
    
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success
        self.title("Iniciar Sesión - Memoriales Altagracia")
        self.geometry("450x500")
        self.resizable(False, False)
        self.grab_set()
        
        # Centrar ventana
        centrar_ventana(self, 450, 500)
        
        self.crear_interfaz()
    
    def crear_interfaz(self):
        self.configure(fg_color=("#F1F5F9", "#101318"))
        
        card = ctk.CTkFrame(self, fg_color=("#FFFFFF", "#181c24"), corner_radius=16, border_width=1, border_color=("#CBD5E1", "#2a303d"))
        card.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Logo y título
        ctk.CTkLabel(card, text="🏛️", font=("Segoe UI", 42)).pack(pady=(25, 4))
        ctk.CTkLabel(card, text="MEMORIALES ALTAGRACIA", font=("Segoe UI", 18, "bold"),
                     text_color="#d4af37").pack()
        ctk.CTkLabel(card, text="Sistema de Gestión Funeraria Integral",
                     font=("Segoe UI", 11), text_color=("#64748B", "#9da3ae")).pack(pady=(2, 20))
        
        # Formulario
        form_box = ctk.CTkFrame(card, fg_color="transparent")
        form_box.pack(fill="x", padx=30)

        ctk.CTkLabel(form_box, text="Usuario:", font=("Segoe UI", 11, "bold"), text_color=("#1E293B", "#cbd5e1")).pack(anchor="w", pady=(0, 3))
        self.usuario_entry = ctk.CTkEntry(
            form_box, width=280, height=38, font=("Segoe UI", 12),
            placeholder_text="Ej: admin", fg_color=("#F8FAFC", "#12151b"), border_color=("#CBD5E1", "#2d3545"),
            text_color=("#0F172A", "#F8FAFC")
        )
        self.usuario_entry.pack(fill="x", pady=(0, 14))
        self.usuario_entry.focus()
        
        ctk.CTkLabel(form_box, text="Contraseña:", font=("Segoe UI", 11, "bold"), text_color=("#1E293B", "#cbd5e1")).pack(anchor="w", pady=(0, 3))
        self.password_entry = ctk.CTkEntry(
            form_box, width=280, height=38, show="*", font=("Segoe UI", 12),
            placeholder_text="••••••••", fg_color=("#F8FAFC", "#12151b"), border_color=("#CBD5E1", "#2d3545"),
            text_color=("#0F172A", "#F8FAFC")
        )
        self.password_entry.pack(fill="x", pady=(0, 20))
        
        # Botón
        ctk.CTkButton(
            form_box, text="Iniciar Sesión", command=self.login,
            height=42, font=("Segoe UI", 13, "bold"),
            fg_color="#d4af37", text_color="#101318",
            hover_color="#e5c158", corner_radius=8
        ).pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(card, text="🔒 Conexión local protegida  •  v2.0", font=("Segoe UI", 9), text_color=("#94A3B8", "#555f70")).pack(side="bottom", pady=12)
        
        self.bind('<Return>', lambda e: self.login())
    
    def login(self):
        usuario = self.usuario_entry.get().strip()
        password = self.password_entry.get()
        
        if not usuario or not password:
            mb.showwarning("Campos vacíos", "Ingrese usuario y contraseña")
            return
        
        user = autenticar(usuario, password)
        
        if user:
            ContratoRepository.registrar_bitacora(user[0], "Inicio de sesión", f"Usuario {usuario} inició sesión")
            self.destroy()
            self.on_success(user)
        else:
            mb.showerror("Error", "Usuario o contraseña incorrectos")


class AdminSetupWindow(ctk.CTkToplevel):
    """Crea el administrador inicial o reemplaza una clave heredada conocida."""

    def __init__(self, parent, admin, on_success):
        super().__init__(parent)
        self.admin = admin
        self.on_success = on_success
        self.title("Configurar administrador")
        self.geometry("460x520")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.cancelar)
        centrar_ventana(self, 460, 520)
        self.crear_interfaz()

    def crear_interfaz(self):
        card = ctk.CTkFrame(self, fg_color=("#FFFFFF", "#181c24"), corner_radius=16)
        card.pack(fill="both", expand=True, padx=24, pady=24)
        ctk.CTkLabel(
            card, text="CONFIGURAR ACCESO DE ADMINISTRADOR",
            font=("Segoe UI", 17, "bold"), text_color="#D4AF37",
            wraplength=360,
        ).pack(pady=(24, 8))
        ctk.CTkLabel(
            card,
            text="Crea una contraseña propia de al menos 12 caracteres. "
                 "No existe una clave predeterminada.",
            font=("Segoe UI", 11), wraplength=360, justify="center",
        ).pack(padx=16, pady=(0, 14))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=28)
        ctk.CTkLabel(form, text="Usuario administrador").pack(anchor="w")
        self.usuario_entry = ctk.CTkEntry(form, placeholder_text="admin")
        self.usuario_entry.pack(fill="x", pady=(2, 10))
        self.usuario_entry.insert(0, self.admin["usuario"])

        ctk.CTkLabel(form, text="Nombre").pack(anchor="w")
        self.nombre_entry = ctk.CTkEntry(form, placeholder_text="Administrador")
        self.nombre_entry.pack(fill="x", pady=(2, 10))
        self.nombre_entry.insert(0, self.admin["nombre"] or "Administrador")

        ctk.CTkLabel(form, text="Nueva contraseña").pack(anchor="w")
        self.password_entry = ctk.CTkEntry(form, show="*", placeholder_text="12 caracteres o más")
        self.password_entry.pack(fill="x", pady=(2, 10))
        ctk.CTkLabel(form, text="Confirmar contraseña").pack(anchor="w")
        self.confirmar_entry = ctk.CTkEntry(form, show="*")
        self.confirmar_entry.pack(fill="x", pady=(2, 16))

        ctk.CTkButton(
            form, text="Guardar acceso seguro", command=self.guardar,
            fg_color="#D4AF37", text_color="#101318",
        ).pack(fill="x")

    def guardar(self):
        password = self.password_entry.get()
        if password != self.confirmar_entry.get():
            mb.showerror("Error", "Las contraseñas no coinciden.", parent=self)
            return
        try:
            configurar_administrador(
                self.usuario_entry.get(),
                self.nombre_entry.get(),
                password,
            )
        except ValueError as exc:
            mb.showerror("No se pudo configurar", str(exc), parent=self)
            return
        except Exception as exc:
            mb.showerror(
                "Error al configurar",
                f"No se pudo guardar el acceso del administrador:\n{exc}",
                parent=self,
            )
            return
        mb.showinfo(
            "Acceso configurado",
            "El administrador quedó configurado. Inicia sesión con el usuario y "
            "la contraseña que acabas de establecer.",
            parent=self,
        )
        self.destroy()
        self.on_success()

    def cancelar(self):
        self.master.destroy()


class App(ctk.CTk):
    """Aplicación principal"""
    
    def __init__(self):
        super().__init__()
        self.title("Servicios Memoriales Altagracia - Sistema de Gestión Integral")
        self.geometry("1400x850")
        self.minsize(1200, 700)
        
        # Inicializar base de datos
        try:
            init_db()
        except Exception as e:
            mb.showerror("Error crítico", f"No se pudo inicializar la base de datos: {str(e)}")
            self.destroy()
            return
        
        # Aplicar estilo a las tablas
        aplicar_estilo_treeview()
        
        self.usuario_actual = None
        admin_setup = obtener_configuracion_administrador()
        if admin_setup:
            self.admin_setup_window = AdminSetupWindow(
                self, admin_setup, self.mostrar_login
            )
        else:
            self.mostrar_login()
    
    def mostrar_login(self):
        self.login_window = LoginWindow(self, self.iniciar_sesion)
    
    def iniciar_sesion(self, usuario):
        self.usuario_actual = usuario
        self.crear_interfaz_principal()
    
    def crear_interfaz_principal(self):
        # Configurar grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=("#F1F5F9", "#14171F"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)
        
        # Logo
        ctk.CTkLabel(self.sidebar, text="🏛️", font=("Segoe UI", 40)).pack(pady=(20, 5))
        ctk.CTkLabel(self.sidebar, text="MEMORIALES", font=("Segoe UI", 14, "bold"),
                     text_color="#d4af37").pack()
        ctk.CTkLabel(self.sidebar, text="ALTAGRACIA", font=("Segoe UI", 16, "bold"),
                     text_color="#d4af37").pack()
        
        # Datos empresa
        empresa_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        empresa_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(empresa_frame, text=EMPRESA["nombre"], font=("Segoe UI", 10, "bold"),
                     text_color=("#1E293B", "#F1F5F9"), wraplength=250).pack()
        ctk.CTkLabel(empresa_frame, text=EMPRESA["direccion"], font=("Segoe UI", 9),
                     text_color=("#64748B", "#94A3B8"), wraplength=250).pack()
        
        # Separador
        separator = ttk.Separator(self.sidebar, orient='horizontal')
        separator.pack(fill='x', pady=10, padx=10)
        
        # Botones de navegación con estado activo
        modulos = [
            ("📊 Dashboard", DashboardFrame),
            ("👥 Clientes y Familias", ClientesFrame),
            ("📄 Gestión Contratos", ContratosFrame),
            ("🏛️ Capillas Velación", CapillasFrame),
            ("💰 Cobros y Horarios", PagosFrame),
            ("📦 Control Inventario", InventarioFrame),
            ("📈 Reportes y Finanzas", ReportesFrame),
            ("📃 Solvencias de Contratos", SolvenciasFrame)
        ]
        
        self.frames = {}
        self.nav_buttons = {}

        for texto, clase in modulos:
            btn = ctk.CTkButton(
                self.sidebar,
                text=texto,
                anchor="w",
                command=lambda c=clase: self.mostrar_frame(c),
                fg_color="transparent",
                text_color=("#334155", "#cbd5e1"),
                hover_color=("#E2E8F0", "#262d3a"),
                height=38,
                corner_radius=8,
                font=("Segoe UI", 11)
            )
            btn.pack(pady=3, padx=12, fill="x")
            self.nav_buttons[clase] = btn
            
            frame = clase(self, self.usuario_actual)
            frame.app = self
            self.frames[clase] = frame
            frame.grid(row=0, column=1, sticky="nsew")
            frame.grid_remove()
        
        # Selector de Modo Visual (Oscuro / Claro)
        theme_frame = ctk.CTkFrame(self.sidebar, fg_color=("#E2E8F0", "#181c24"), corner_radius=8)
        theme_frame.pack(side="bottom", fill="x", pady=6, padx=12)
        ctk.CTkLabel(theme_frame, text="🎨 Modo Visual:", font=("Segoe UI", 10, "bold"), text_color="#d4af37").pack(anchor="w", padx=8, pady=(6, 2))
        self.modo_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["Oscuro", "Claro", "Sistema"],
            command=self.cambiar_modo_visual,
            height=28,
            font=("Segoe UI", 10),
            fg_color=("#CBD5E1", "#2c3545"),
            text_color=("#0F172A", "#F8FAFC"),
            button_color=("#94A3B8", "#3d495c"),
            button_hover_color=("#64748B", "#4f5e77")
        )
        self.modo_menu.set("Oscuro")
        self.modo_menu.pack(fill="x", padx=8, pady=(0, 6))

        # Tarjeta de Usuario y Perfil
        user_frame = ctk.CTkFrame(self.sidebar, fg_color=("#E2E8F0", "#181c24"), corner_radius=10, border_width=1, border_color=("#CBD5E1", "#262d3a"))
        user_frame.pack(side="bottom", fill="x", pady=6, padx=12)
        
        u_top = ctk.CTkFrame(user_frame, fg_color="transparent")
        u_top.pack(fill="x", padx=8, pady=(8, 4))

        iniciales = "".join([part[0] for part in self.usuario_actual[2].split()[:2]]).upper() or "US"
        avatar_box = ctk.CTkFrame(u_top, width=34, height=34, corner_radius=17, fg_color="#d4af37")
        avatar_box.pack(side="left")
        avatar_box.pack_propagate(False)
        ctk.CTkLabel(avatar_box, text=iniciales, font=("Segoe UI", 11, "bold"), text_color="black").pack(expand=True)

        u_info = ctk.CTkFrame(u_top, fg_color="transparent")
        u_info.pack(side="left", padx=8)
        ctk.CTkLabel(u_info, text=self.usuario_actual[2], font=("Segoe UI", 11, "bold"), text_color=("#0F172A", "#FFFFFF")).pack(anchor="w")
        rol_txt = "🛡️ Administrador" if self.usuario_actual[3].lower() == 'admin' else f"👤 {self.usuario_actual[3].capitalize()}"
        ctk.CTkLabel(u_info, text=rol_txt, font=("Segoe UI", 9), text_color="#d4af37").pack(anchor="w")

        ctk.CTkButton(
            user_frame,
            text="🚪 Cerrar Sesión",
            command=self.cerrar_sesion,
            fg_color=("#FEE2E2", "#3a181a"),
            hover_color=("#FECACA", "#5c2024"),
            text_color="#DC2626",
            font=("Segoe UI", 10, "bold"),
            height=28
        ).pack(fill="x", padx=8, pady=(2, 8))
        
        # Fecha y hora
        self.fecha_label = ctk.CTkLabel(self.sidebar, text="", font=("Segoe UI", 9), text_color=("#64748B", "#7f8c8d"))
        self.fecha_label.pack(side="bottom", pady=4)
        self.actualizar_fecha_hora()
        
        # Mostrar dashboard inicial
        self.mostrar_frame(DashboardFrame)
    
    def cambiar_modo_visual(self, modo: str):
        mapa = {"Oscuro": "dark", "Claro": "light", "Sistema": "system"}
        modo_str = mapa.get(modo, "dark")
        ctk.set_appearance_mode(modo_str)
        # Actualizar estilo de tablas Treeview en tiempo real
        es_oscuro = (modo_str == "dark") if modo_str != "system" else (ctk.get_appearance_mode() == "Dark")
        aplicar_estilo_treeview(es_oscuro)
        # Refrescar frame activo para redibujar árboles y tarjetas
        if hasattr(self, 'clase_actual'):
            self.mostrar_frame(self.clase_actual)

    def mostrar_frame(self, clase):
        self.clase_actual = clase
        for frame in self.frames.values():
            frame.grid_remove()
        frame = self.frames[clase]
        frame.grid()
        
        # Actualizar estilo de botón activo en la barra lateral
        for c, btn in self.nav_buttons.items():
            if c == clase:
                btn.configure(
                    fg_color="#d4af37",
                    text_color="#101318",
                    font=("Segoe UI", 12, "bold"),
                    hover_color="#e5c158"
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("#334155", "#cbd5e1"),
                    font=("Segoe UI", 11),
                    hover_color=("#E2E8F0", "#262d3a")
                )

        # Actualizar datos según el frame
        if hasattr(frame, 'actualizar_datos'):
            frame.actualizar_datos()
        elif hasattr(frame, 'cargar_clientes'):
            frame.cargar_clientes()
        elif hasattr(frame, 'cargar_contratos'):
            frame.cargar_contratos()
        elif hasattr(frame, 'cargar_inventario'):
            frame.cargar_inventario()
        elif hasattr(frame, 'cargar_capillas'):
            frame.cargar_capillas()
    
    def cerrar_sesion(self):
        ContratoRepository.registrar_bitacora(self.usuario_actual[0], "Cierre de sesión",
                                              f"Usuario {self.usuario_actual[1]} cerró sesión")
        self.usuario_actual = None
        self.destroy()
        # Reiniciar la app
        new_app = App()
        new_app.mainloop()
    
    def actualizar_fecha_hora(self):
        ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.fecha_label.configure(text=ahora)
        self.after(1000, self.actualizar_fecha_hora)


# Punto de entrada
if __name__ == "__main__":
    app = App()
    app.mainloop()