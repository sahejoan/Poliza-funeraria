# ui/visor_pago.py - Visor de detalle de pago con formato profesional para impresión
import customtkinter as ctk
from tkinter import ttk
import tkinter.messagebox as mb
import datetime
from services.db_service import obtener_conexion
from services.pago_service import PagoService
from utils.helpers import aplicar_estilo_treeview

class VisorPago(ctk.CTkToplevel):
    """Ventana para ver detalle de pago con formato de impresión"""
    
    def __init__(self, parent, pago_id):
        super().__init__(parent)
        self.parent = parent
        self.pago_id = pago_id
        self.title("Detalle de Pago - Memoriales Altagracia")
        self.geometry("700x900")
        self.resizable(False, False)
        self.grab_set()
        
        # Centrar ventana
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.winfo_screenheight() // 2) - (900 // 2)
        self.geometry(f'700x900+{x}+{y}')
        
        self.cargar_datos()
        self.crear_interfaz()
    
    def cargar_datos(self):
        """Carga los datos del pago y del contrato"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Obtener datos del pago
        cursor.execute("""
            SELECT p.id, p.fecha, p.monto, p.metodo, p.referencia, p.moneda, p.tasa_cambio,
                   p.contrato_id, p.cuota_id, p.mes_periodo
            FROM pagos p
            WHERE p.id = ?
        """, (self.pago_id,))
        self.pago = cursor.fetchone()
        
        if not self.pago:
            conn.close()
            return
        
        # Obtener datos del contrato
        cursor.execute("""
            SELECT c.numero, c.fecha_contrato, c.monto_total, c.pagado,
                   COALESCE(d.nombre, 'Por asignar'), COALESCE(d.apellido, ''), COALESCE(d.cedula, 'N/E'),
                   COALESCE(f.resp_nombre, ''), COALESCE(f.resp_apellido, ''), COALESCE(f.resp_cedula, ''),
                   COALESCE(f.resp_telefono, ''), COALESCE(f.resp_email, ''),
                   COALESCE(cap.nombre, 'Sin Capilla Asignada') as capilla
            FROM contratos c
            LEFT JOIN difuntos d ON c.difunto_id = d.id
            LEFT JOIN familias f ON c.familia_id = f.familia_id
            LEFT JOIN capillas cap ON c.capilla_id = cap.id
            WHERE c.id = ?
        """, (self.pago[7],))
        self.contrato = cursor.fetchone()
        
        # Si es pago de cuota, obtener datos de la cuota
        self.cuota = None
        if self.pago[8]:
            cursor.execute("""
                SELECT numero, monto, fecha_vencimiento
                FROM cuotas
                WHERE id = ?
            """, (self.pago[8],))
            self.cuota = cursor.fetchone()
        
        conn.close()
    
    def crear_interfaz(self):
        if not self.pago or not self.contrato:
            ctk.CTkLabel(self, text="Error: No se encontraron datos del pago",
                        font=("Segoe UI", 16), text_color="red").pack(expand=True)
            return
        
        # Frame principal con scroll
        main_frame = ctk.CTkScrollableFrame(self, fg_color="#FFFFFF")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ========== ENCABEZADO CON LOGO ==========
        header_frame = ctk.CTkFrame(main_frame, fg_color="#1A1A2E", corner_radius=10)
        header_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header_frame, text="🏛️", font=("Segoe UI", 40),
                    text_color="#D4AF37").pack(pady=(15,0))
        ctk.CTkLabel(header_frame, text="SERVICIOS MEMORIALES ALTAGRACIA C.A.",
                    font=("Segoe UI", 16, "bold"), text_color="#D4AF37").pack()
        ctk.CTkLabel(header_frame, text="RIF: J-41234567-8",
                    font=("Segoe UI", 11), text_color="#BDC3C7").pack()
        ctk.CTkLabel(header_frame, text="Carrera 13 entre Calles 9 y 10, Calabozo, Estado Guárico, Venezuela",
                    font=("Segoe UI", 10), text_color="#BDC3C7").pack()
        ctk.CTkLabel(header_frame, text="Tel: +58 246-1234567 | Email: contacto@memorialesaltagracia.com",
                    font=("Segoe UI", 10), text_color="#BDC3C7").pack(pady=(0,15))
        
        # ========== TÍTULO DEL DOCUMENTO ==========
        ctk.CTkLabel(main_frame, text="COMPROBANTE DE PAGO",
                    font=("Segoe UI", 22, "bold"), text_color="#1A1A2E").pack(pady=10)
        
        # ========== INFORMACIÓN DEL PAGO ==========
        info_frame = ctk.CTkFrame(main_frame, fg_color="#F4F4F4", corner_radius=10)
        info_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(info_frame, text="INFORMACIÓN DEL PAGO",
                    font=("Segoe UI", 14, "bold"), text_color="#D4AF37").pack(anchor="w", padx=15, pady=(10,5))
        
        # Datos del pago
        from utils.helpers import formatear_fecha_ddmmyyyy
        fecha_pago = formatear_fecha_ddmmyyyy(self.pago[1])
        
        self._crear_fila(info_frame, "N° Comprobante:", f"PAG-{self.pago[0]:06d}")
        self._crear_fila(info_frame, "Fecha y Hora:", fecha_pago)
        if len(self.pago) > 9 and self.pago[9]:
            self._crear_fila(info_frame, "Mes / Período Cancelado:", self.pago[9])
        self._crear_fila(info_frame, "Monto:", f"${self.pago[2]:,.2f}")
        self._crear_fila(info_frame, "Método de Pago:", self.pago[3])
        self._crear_fila(info_frame, "Moneda:", self.pago[5] or "USD")
        
        if self.pago[4]:
            self._crear_fila(info_frame, "Referencia:", self.pago[4])
        
        if self.pago[6]:
            self._crear_fila(info_frame, "Tasa de Cambio:", f"1 USD = {self.pago[6]:,.2f} BS")
        
        if self.cuota:
            self._crear_fila(info_frame, "Cuota N°:", str(self.cuota[0]))
            self._crear_fila(info_frame, "Monto de Cuota:", f"${self.cuota[1]:,.2f}")
            vcto = formatear_fecha_ddmmyyyy(self.cuota[2])
            self._crear_fila(info_frame, "Fecha Vencimiento:", vcto)
        
        # ========== INFORMACIÓN DEL CONTRATO ==========
        contrato_frame = ctk.CTkFrame(main_frame, fg_color="#F4F4F4", corner_radius=10)
        contrato_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(contrato_frame, text="INFORMACIÓN DEL CONTRATO",
                    font=("Segoe UI", 14, "bold"), text_color="#D4AF37").pack(anchor="w", padx=15, pady=(10,5))
        
        self._crear_fila(contrato_frame, "N° Contrato:", self.contrato[0])
        fecha_cont = formatear_fecha_ddmmyyyy(self.contrato[1])
        self._crear_fila(contrato_frame, "Fecha Contrato:", fecha_cont)
        self._crear_fila(contrato_frame, "Monto Total:", f"${self.contrato[2]:,.2f}")
        self._crear_fila(contrato_frame, "Monto Pagado:", f"${self.contrato[3]:,.2f}")
        saldo = self.contrato[2] - self.contrato[3]
        self._crear_fila(contrato_frame, "Saldo Pendiente:", f"${saldo:,.2f}")
        self._crear_fila(contrato_frame, "Capilla:", self.contrato[11])
        
        # ========== DATOS DEL DIFUNTO ==========
        difunto_frame = ctk.CTkFrame(main_frame, fg_color="#F4F4F4", corner_radius=10)
        difunto_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(difunto_frame, text="DATOS DEL DIFUNTO",
                    font=("Segoe UI", 14, "bold"), text_color="#D4AF37").pack(anchor="w", padx=15, pady=(10,5))
        
        self._crear_fila(difunto_frame, "Nombre Completo:", f"{self.contrato[4]} {self.contrato[5]}")
        self._crear_fila(difunto_frame, "Cédula:", self.contrato[6])
        
        # ========== DATOS DEL RESPONSABLE ==========
        resp_frame = ctk.CTkFrame(main_frame, fg_color="#F4F4F4", corner_radius=10)
        resp_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(resp_frame, text="DATOS DEL FAMILIAR RESPONSABLE",
                    font=("Segoe UI", 14, "bold"), text_color="#D4AF37").pack(anchor="w", padx=15, pady=(10,5))
        
        self._crear_fila(resp_frame, "Nombre Completo:", f"{self.contrato[7]} {self.contrato[8]}")
        self._crear_fila(resp_frame, "Cédula:", self.contrato[9])
        self._crear_fila(resp_frame, "Teléfono:", self.contrato[10] or "—")
        self._crear_fila(resp_frame, "Email:", self.contrato[11] or "—")
        
        # ========== FIRMAS ==========
        firmas_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        firmas_frame.pack(fill="x", pady=30)
        
        # Línea divisoria
        separator = ttk.Separator(firmas_frame, orient='horizontal')
        separator.pack(fill='x', pady=20)
        
        # Fila de firmas
        firmas_row = ctk.CTkFrame(firmas_frame, fg_color="transparent")
        firmas_row.pack(fill="x")
        
        firma_empresa = ctk.CTkFrame(firmas_row, fg_color="transparent")
        firma_empresa.pack(side="left", expand=True, fill="x")
        ctk.CTkLabel(firma_empresa, text="_________________________",
                    font=("Segoe UI", 10), text_color="black").pack()
        ctk.CTkLabel(firma_empresa, text="Firma y sello autorizado",
                    font=("Segoe UI", 9), text_color="gray").pack()
        ctk.CTkLabel(firma_empresa, text="SERVICIOS MEMORIALES ALTAGRACIA",
                    font=("Segoe UI", 9), text_color="gray").pack()
        
        firma_cliente = ctk.CTkFrame(firmas_row, fg_color="transparent")
        firma_cliente.pack(side="right", expand=True, fill="x")
        ctk.CTkLabel(firma_cliente, text="_________________________",
                    font=("Segoe UI", 10), text_color="black").pack()
        ctk.CTkLabel(firma_cliente, text="Firma del Familiar Responsable",
                    font=("Segoe UI", 9), text_color="gray").pack()
        ctk.CTkLabel(firma_cliente, text=f"{self.contrato[7]} {self.contrato[8]}",
                    font=("Segoe UI", 9), text_color="gray").pack()
        
        # ========== PIE DE PÁGINA ==========
        pie_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        pie_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(pie_frame, text="Este documento es un comprobante de pago válido para todos los efectos legales.",
                    font=("Segoe UI", 9), text_color="gray").pack()
        ctk.CTkLabel(pie_frame, text=f"Documento generado el {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                    font=("Segoe UI", 8), text_color="gray").pack()
        
        # ========== BOTONES DE ACCIÓN ==========
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(btn_frame, text="📄 Generar Recibo PDF", command=self.generar_pdf,
                     fg_color="#D4AF37", hover_color="#B8860B", text_color="black", font=("Segoe UI", 11, "bold"), height=40, width=180).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="🖨️ Imprimir Recibo", command=self.imprimir,
                     fg_color="#2ECC71", text_color="black", height=40, width=140).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="📋 Copiar al Portapapeles", command=self.copiar,
                     fg_color="#3498DB", text_color="white", height=40, width=180).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="❌ Cerrar", command=self.destroy,
                     fg_color="#E74C3C", text_color="white", height=40, width=110).pack(side="right", padx=8)
    
    def _crear_fila(self, parent, label, valor):
        """Crea una fila con label y valor"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=3)
        
        ctk.CTkLabel(frame, text=label, font=("Segoe UI", 11, "bold"),
                    width=180, anchor="w", text_color="#333333").pack(side="left")
        ctk.CTkLabel(frame, text=valor, font=("Segoe UI", 11),
                    anchor="w", text_color="#555555").pack(side="left", padx=10)
    
    def imprimir(self):
        """Envía el contenido a imprimir generando el recibo PDF oficial"""
        self.generar_pdf()

    def generar_pdf(self):
        from services.pdf_service import generar_pdf_recibo_pago
        import os
        try:
            ruta = generar_pdf_recibo_pago(self.pago_id)
            if ruta and os.path.exists(ruta):
                try:
                    os.startfile(ruta)
                except Exception:
                    pass
                mb.showinfo("Recibo Oficial PDF", f"✅ Recibo de Pago Oficial generado con éxito:\n{ruta}", parent=self)
            else:
                mb.showerror("Error", "No se pudo generar el documento PDF del recibo.", parent=self)
        except Exception as e:
            mb.showerror("Error", f"Error al generar recibo: {str(e)}", parent=self)
    
    def copiar(self):
        """Copia los datos principales al portapapeles"""
        texto = f"""SERVICIOS MEMORIALES ALTAGRACIA C.A.
COMPROBANTE DE PAGO
====================
N° Comprobante: PAG-{self.pago[0]:06d}
Fecha: {self.pago[1]}
Monto: ${self.pago[2]:,.2f}
Método: {self.pago[3]}
Contrato: {self.contrato[0]}
Difunto: {self.contrato[4]} {self.contrato[5]}
Responsable: {self.contrato[7]} {self.contrato[8]}
"""
        self.clipboard_clear()
        self.clipboard_append(texto)
        mb.showinfo("Copiado", "Información copiada al portapapeles")