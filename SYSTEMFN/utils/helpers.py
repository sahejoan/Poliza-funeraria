# utils/helpers.py - Funciones auxiliares, estilos y personalización visual
from tkinter import ttk
import tkinter.messagebox as mb
import customtkinter as ctk
import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, Tuple

# Constantes de diseño visual corporativo
FONT_FAMILY = "Segoe UI"
COLOR_GOLD = "#D4AF37"
COLOR_GOLD_HOVER = "#B8960C"
COLOR_BG_DARK = "#1A1A2E"
COLOR_CARD_DARK = "#16213E"
COLOR_NAVY = "#0F3460"
COLOR_GREEN = "#2ECC71"
COLOR_RED = "#E74C3C"
COLOR_BLUE = "#3498DB"
COLOR_GRAY = "#7F8C8D"


def obtener_fuente(size: int = 12, weight: str = "normal") -> Tuple[str, int, str]:
    """Retorna una tupla de fuente estándar para widgets"""
    return (FONT_FAMILY, size, weight)


def aplicar_estilo_treeview(modo_oscuro: bool = True):
    """Aplica estilo global al Treeview para evitar texto superpuesto y mejorar legibilidad y contraste"""
    style = ttk.Style()
    try:
        style.theme_use('clam')
    except Exception:
        style.theme_use('default')

    bg = "#181C24" if modo_oscuro else "#FFFFFF"
    fg = "#E2E8F0" if modo_oscuro else "#1A1A1A"
    sel_bg = "#2A3C52" if modo_oscuro else "#CBD5E1"
    sel_fg = "#F1C40F" if modo_oscuro else "#000000"
    head_bg = "#12151B" if modo_oscuro else "#E2E8F0"
    head_fg = COLOR_GOLD if modo_oscuro else "#1E293B"

    style.configure(
        "Treeview",
        background=bg,
        foreground=fg,
        fieldbackground=bg,
        rowheight=32,
        font=(FONT_FAMILY, 10),
        borderwidth=0
    )
    style.configure(
        "Treeview.Heading",
        background=head_bg,
        foreground=head_fg,
        font=(FONT_FAMILY, 10, "bold"),
        relief="flat",
        padding=(8, 6)
    )
    style.map(
        "Treeview",
        background=[("selected", sel_bg)],
        foreground=[("selected", sel_fg)]
    )
    style.map(
        "Treeview.Heading",
        background=[("active", "#1E2430" if modo_oscuro else "#CBD5E1")]
    )
    habilitar_navegacion_teclado()


_NAVEGACION_TECLADO_ACTIVA = False


def habilitar_navegacion_teclado():
    """
    Habilita globalmente el despliegue y navegación con teclado (Flecha Abajo ↓, Flecha Arriba ↑,
    Enter, Espacio y clic en cualquier parte de un desplegable readonly) para todos los
    CTkComboBox, CTkOptionMenu y CTkScrollableFrame del sistema.
    """
    global _NAVEGACION_TECLADO_ACTIVA
    if _NAVEGACION_TECLADO_ACTIVA:
        return
    _NAVEGACION_TECLADO_ACTIVA = True

    # 1. Parche para CTkComboBox
    orig_combo_init = ctk.CTkComboBox.__init__

    def _patched_combo_init(self, *args, **kwargs):
        orig_combo_init(self, *args, **kwargs)

        def _on_entry_click(event=None):
            if self._state != "disabled":
                try:
                    self._entry.focus_set()
                except Exception:
                    pass
                if self._state == "readonly":
                    self._clicked()

        def _on_key_nav(event):
            if self._state == "disabled" or not self._values:
                return
            actual = self.get()
            try:
                idx = list(self._values).index(actual)
            except ValueError:
                idx = -1
            if event.keysym == "Down":
                nuevo_idx = (idx + 1) % len(self._values)
            else:
                nuevo_idx = (idx - 1) % len(self._values)
            nuevo_val = self._values[nuevo_idx]
            self._dropdown_callback(nuevo_val)
            return "break"

        def _on_open_dropdown(event):
            if self._state != "disabled" and self._values:
                self._open_dropdown_menu()
                return "break"

        orig_clicked = self._clicked

        def _patched_clicked(event=None):
            try:
                self._entry.focus_set()
            except Exception:
                pass
            orig_clicked(event)

        self._clicked = _patched_clicked
        self._navegar_teclado = _on_key_nav
        try:
            self._canvas.tag_bind("right_parts", "<Button-1>", self._clicked)
            self._canvas.tag_bind("dropdown_arrow", "<Button-1>", self._clicked)
        except Exception:
            pass

        self._entry.bind("<Button-1>", _on_entry_click, add="+")
        self._entry.bind("<Down>", _on_key_nav)
        self._entry.bind("<Up>", _on_key_nav)
        self._entry.bind("<Alt-Down>", _on_open_dropdown)
        self._entry.bind("<F4>", _on_open_dropdown)
        self.bind("<Down>", _on_key_nav)
        self.bind("<Up>", _on_key_nav)

    ctk.CTkComboBox.__init__ = _patched_combo_init

    # 2. Parche para CTkOptionMenu
    orig_om_init = ctk.CTkOptionMenu.__init__

    def _patched_om_init(self, *args, **kwargs):
        orig_om_init(self, *args, **kwargs)
        try:
            self._canvas.configure(takefocus=1)
        except Exception:
            pass

        def _on_om_click(event=None):
            if self._state != "disabled":
                try:
                    self._canvas.focus_set()
                except Exception:
                    pass

        def _on_om_key_nav(event):
            if self._state == "disabled" or not self._values:
                return
            actual = self.get()
            try:
                idx = list(self._values).index(actual)
            except ValueError:
                idx = -1
            if event.keysym == "Down":
                nuevo_idx = (idx + 1) % len(self._values)
            else:
                nuevo_idx = (idx - 1) % len(self._values)
            nuevo_val = self._values[nuevo_idx]
            self._dropdown_callback(nuevo_val)
            return "break"

        def _on_om_open(event):
            if self._state != "disabled" and self._values:
                self._open_dropdown_menu()
                return "break"

        self._navegar_teclado = _on_om_key_nav
        self._canvas.bind("<Button-1>", _on_om_click, add="+")
        self._text_label.bind("<Button-1>", _on_om_click, add="+")
        self._canvas.bind("<Down>", _on_om_key_nav)
        self._canvas.bind("<Up>", _on_om_key_nav)
        self._canvas.bind("<Alt-Down>", _on_om_open)
        self._canvas.bind("<space>", _on_om_open)
        self.bind("<Down>", _on_om_key_nav)
        self.bind("<Up>", _on_om_key_nav)

    ctk.CTkOptionMenu.__init__ = _patched_om_init

    # 3. Parche para CTkScrollableFrame (desplazamiento con flechas ↓ / ↑ y RePág / AvPág)
    orig_sf_init = ctk.CTkScrollableFrame.__init__

    def _patched_sf_init(self, *args, **kwargs):
        orig_sf_init(self, *args, **kwargs)
        try:
            self._parent_canvas.configure(takefocus=1)
        except Exception:
            pass

        def _scroll_teclado(event):
            if not self.winfo_ismapped():
                return
            focus_w = self.focus_get()
            if focus_w is not None:
                w_cls = focus_w.winfo_class()
                if w_cls in ("Treeview", "Text", "Listbox"):
                    return
                parent_w = getattr(focus_w, "master", None)
                if isinstance(parent_w, (ctk.CTkComboBox, ctk.CTkOptionMenu, ctk.CTkTextbox)):
                    return
                # Verificar si el foco pertenece a este scrollable frame
                curr = focus_w
                pertenece = False
                while curr is not None:
                    if curr == self or curr == self._parent_frame or curr == self._parent_canvas:
                        pertenece = True
                        break
                    curr = getattr(curr, "master", None)
                if not pertenece:
                    return

            if event.keysym == "Down":
                self._parent_canvas.yview_scroll(3, "units")
            elif event.keysym == "Up":
                self._parent_canvas.yview_scroll(-3, "units")
            elif event.keysym == "Next":
                self._parent_canvas.yview_scroll(1, "pages")
            elif event.keysym == "Prior":
                self._parent_canvas.yview_scroll(-1, "pages")

        self.bind_all("<Down>", _scroll_teclado, add="+")
        self.bind_all("<Up>", _scroll_teclado, add="+")
        self.bind_all("<Next>", _scroll_teclado, add="+")
        self.bind_all("<Prior>", _scroll_teclado, add="+")

    ctk.CTkScrollableFrame.__init__ = _patched_sf_init


# Activar inmediatamente al importar el módulo para cubrir todos los widgets creados
habilitar_navegacion_teclado()


def centrar_ventana(ventana, ancho: int, alto: int):
    """Centra una ventana en la pantalla del usuario"""
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
    y = (ventana.winfo_screenheight() // 2) - (alto // 2)
    ventana.geometry(f'{ancho}x{alto}+{x}+{y}')


def formatear_moneda(valor: float) -> str:
    """Formatea un número como moneda en USD"""
    return f"${(valor or 0):,.2f}"


def parsear_decimal_monetario(valor: str) -> float:
    """Interpreta importes con punto o coma decimal y redondea a dos decimales."""
    texto = str(valor or "").strip().replace("$", "").replace("Bs", "").replace(" ", "")
    if not texto:
        raise ValueError("El importe está vacío")

    if "," in texto and "." in texto:
        separador_decimal = "," if texto.rfind(",") > texto.rfind(".") else "."
        separador_miles = "." if separador_decimal == "," else ","
        texto = texto.replace(separador_miles, "")
        if separador_decimal == ",":
            texto = texto.replace(",", ".")
    elif "," in texto:
        if texto.count(",") > 1:
            raise ValueError("El importe tiene separadores inválidos")
        texto = texto.replace(",", ".")
    elif texto.count(".") > 1:
        grupos = texto.split(".")
        if any(not grupo.isdigit() for grupo in grupos) or any(len(grupo) != 3 for grupo in grupos[1:]):
            raise ValueError("El importe tiene separadores inválidos")
        texto = "".join(grupos)

    try:
        importe = Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError("El importe no es válido") from exc
    if not importe.is_finite():
        raise ValueError("El importe debe ser un número finito")
    return float(importe.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calcular_edad(fecha_nacimiento_str: str):
    """Calcula la edad en años a partir de una fecha en formato YYYY-MM-DD o DD/MM/YYYY"""
    if not fecha_nacimiento_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            fn = datetime.datetime.strptime(str(fecha_nacimiento_str).strip(), fmt).date()
            hoy = datetime.date.today()
            edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
            return max(0, edad)
        except ValueError:
            continue
    return None



def validar_fecha(fecha_str: str) -> bool:
    """Valida que la fecha tenga formato válido (DD/MM/AAAA, DD-MM-AAAA o YYYY-MM-DD)"""
    if not fecha_str:
        return False
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            datetime.datetime.strptime(str(fecha_str).strip(), fmt)
            return True
        except (ValueError, AttributeError):
            continue
    return False


def normalizar_fecha_iso(fecha_str: str) -> str:
    """Normaliza cualquier fecha (DD/MM/AAAA, etc.) a formato ISO YYYY-MM-DD para la base de datos"""
    if not fecha_str:
        return ""
    texto = str(fecha_str).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            dt = datetime.datetime.strptime(texto, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return texto


def formatear_fecha_ddmmyyyy(fecha_str: str) -> str:
    """Formatea cualquier fecha a DD/MM/AAAA para visualización clara al usuario"""
    if not fecha_str or fecha_str in ("—", "N/E", "None"):
        return "—"
    texto = str(fecha_str).strip()
    # Si contiene hora
    if " " in texto:
        partes = texto.split(" ")
        f_part = partes[0]
        h_part = partes[1] if len(partes) > 1 else ""
        norm_f = formatear_fecha_ddmmyyyy(f_part)
        return f"{norm_f} {h_part}".strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.datetime.strptime(texto, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue
    return texto


def obtener_fecha_actual_ddmmyyyy() -> str:
    """Retorna la fecha actual en formato amigable DD/MM/AAAA"""
    return datetime.datetime.now().strftime("%d/%m/%Y")


def validar_hora(hora_str: str) -> bool:
    """Valida que la hora tenga formato HH:MM"""
    try:
        datetime.datetime.strptime(hora_str.strip(), "%H:%M")
        return True
    except (ValueError, AttributeError):
        return False


def obtener_fecha_actual() -> str:
    """Retorna la fecha actual en formato YYYY-MM-DD"""
    return datetime.datetime.now().strftime("%Y-%m-%d")


def obtener_hora_actual() -> str:
    """Retorna la hora actual en formato HH:MM"""
    return datetime.datetime.now().strftime("%H:%M")


def mostrar_dialogo_verificar_total(parent, verificacion: Dict):
    """
    Muestra un diálogo profesional e interactivo con el desglose exacto de costos del contrato,
    confirmando si el total guardado coincide con la suma de sus componentes o alertando sobre anomalías.
    """
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Verificación de Total y Costos del Contrato")
    dialog.geometry("620x650")
    dialog.resizable(False, False)
    dialog.grab_set()
    centrar_ventana(dialog, 620, 650)

    scroll = ctk.CTkScrollableFrame(dialog)
    scroll.pack(fill="both", expand=True, padx=20, pady=20)

    # Estado general
    ok = verificacion.get("ok", False)
    color_estado = COLOR_GREEN if ok else COLOR_RED
    icono_estado = "✅" if ok else "⚠️"
    texto_estado = "TOTAL CORRECTO Y VERIFICADO" if ok else "SE DETECTARON DISCREPANCIAS"

    ctk.CTkLabel(scroll, text=f"{icono_estado} {texto_estado}",
                 font=obtener_fuente(16, "bold"), text_color=color_estado).pack(pady=(5, 15))

    # Tarjetas de totales
    kpi_frame = ctk.CTkFrame(scroll, fg_color="transparent")
    kpi_frame.pack(fill="x", pady=5)

    c1 = ctk.CTkFrame(kpi_frame, fg_color="#1E3A5F", corner_radius=10)
    c1.pack(side="left", fill="both", expand=True, padx=5)
    ctk.CTkLabel(c1, text="Total Guardado", font=obtener_fuente(10), text_color="#BDC3C7").pack(pady=(8, 0))
    ctk.CTkLabel(c1, text=formatear_moneda(verificacion.get('total_guardado', 0)),
                 font=obtener_fuente(16, "bold"), text_color="white").pack(pady=(2, 8))

    c2 = ctk.CTkFrame(kpi_frame, fg_color="#1B4D3E", corner_radius=10)
    c2.pack(side="left", fill="both", expand=True, padx=5)
    ctk.CTkLabel(c2, text="Total Calculado", font=obtener_fuente(10), text_color="#BDC3C7").pack(pady=(8, 0))
    ctk.CTkLabel(c2, text=formatear_moneda(verificacion.get('total_calculado', 0)),
                 font=obtener_fuente(16, "bold"), text_color=COLOR_GOLD).pack(pady=(2, 8))

    c3 = ctk.CTkFrame(kpi_frame, fg_color="#3A1C28", corner_radius=10)
    c3.pack(side="left", fill="both", expand=True, padx=5)
    ctk.CTkLabel(c3, text="Saldo Pendiente", font=obtener_fuente(10), text_color="#BDC3C7").pack(pady=(8, 0))
    ctk.CTkLabel(c3, text=formatear_moneda(verificacion.get('saldo', 0)),
                 font=obtener_fuente(16, "bold"), text_color="white").pack(pady=(2, 8))

    # Tabla de desglose
    ctk.CTkLabel(scroll, text="DESGLOSE DETALLADO DE COSTOS",
                 font=obtener_fuente(12, "bold"), text_color=COLOR_GOLD).pack(anchor="w", pady=(15, 5))

    tabla_frame = ctk.CTkFrame(scroll)
    tabla_frame.pack(fill="x", pady=5)

    for i, (concepto, monto) in enumerate(verificacion.get("lineas", [])):
        fila = ctk.CTkFrame(tabla_frame, fg_color="#222222" if i % 2 == 0 else "#2A2A2A")
        fila.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(fila, text=concepto, font=obtener_fuente(11), anchor="w").pack(side="left", padx=10, pady=5)

        color_monto = COLOR_GREEN if monto < 0 else "white"
        prefix = "- " if monto < 0 else ""
        ctk.CTkLabel(fila, text=f"{prefix}{formatear_moneda(abs(monto))}",
                     font=obtener_fuente(11, "bold"), text_color=color_monto).pack(side="right", padx=10)

    # Problemas detectados
    problemas = verificacion.get("problemas", [])
    if problemas:
        ctk.CTkLabel(scroll, text="OBSERVACIONES TÉCNICAS:",
                     font=obtener_fuente(12, "bold"), text_color=COLOR_RED).pack(anchor="w", pady=(15, 5))
        for p in problemas:
            ctk.CTkLabel(scroll, text=f"• {p}", font=obtener_fuente(10),
                         text_color="#FF8A8A", wraplength=550, justify="left").pack(anchor="w", padx=10, pady=2)

    ctk.CTkButton(scroll, text="Entendido / Cerrar", command=dialog.destroy,
                 fg_color=COLOR_GOLD, text_color="black", hover_color=COLOR_GOLD_HOVER,
                 height=36).pack(pady=20)