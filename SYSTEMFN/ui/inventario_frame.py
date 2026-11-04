# ui/inventario_frame.py - Gestión de inventario con movimientos y alertas
import customtkinter as ctk
import tkinter.messagebox as mb
from tkinter import ttk
import datetime
from services.db_service import obtener_conexion, ContratoRepository
from utils.helpers import parsear_decimal_monetario
from utils.helpers import aplicar_estilo_treeview, formatear_moneda

class InventarioFrame(ctk.CTkFrame):
    """Gestión de inventario con control de stock mínimo y movimientos"""
    
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.crear_interfaz()
        self.cargar_inventario()
    
    def crear_interfaz(self):
        # Título
        ctk.CTkLabel(self, text="Gestión de Inventario", font=("Segoe UI", 28, "bold"),
                     text_color="#d4af37").pack(pady=20)
        
        # TabView
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        tab_stock = self.tabview.add("📦 Stock Actual")
        tab_movimientos = self.tabview.add("📊 Movimientos")
        tab_nuevo = self.tabview.add("➕ Nuevo Producto")
        
        # ========== TAB STOCK ACTUAL ==========
        self.crear_tabla_stock(tab_stock)
        
        # Botones de acción en stock
        btn_frame = ctk.CTkFrame(tab_stock)
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="➕ Agregar Stock", command=self.abrir_dialogo_aumentar_stock,
                     fg_color="#2ecc71", text_color="black", width=140).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="➖ Reducir Stock", command=self.abrir_dialogo_reducir_stock,
                     fg_color="#e74c3c", width=140).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="✏️ Modificar Precio / Producto", command=self.abrir_dialogo_modificar_producto,
                     fg_color="#d4af37", text_color="black", width=200).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🔄 Actualizar", command=self.cargar_inventario,
                     fg_color="#3498db", width=110).pack(side="left", padx=5)
        
        # ========== TAB MOVIMIENTOS ==========
        self.crear_tabla_movimientos(tab_movimientos)
        
        # ========== TAB NUEVO PRODUCTO ==========
        self.crear_formulario_nuevo_producto(tab_nuevo)
    
    def crear_tabla_stock(self, parent):
        """Crea la tabla de stock actual"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("id", "nombre", "stock", "stock_minimo", "precio", "estado")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("nombre", text="Producto")
        self.tree.heading("stock", text="Stock")
        self.tree.heading("stock_minimo", text="Stock Mínimo")
        self.tree.heading("precio", text="Precio")
        self.tree.heading("estado", text="Estado")
        
        self.tree.column("id", width=50)
        self.tree.column("nombre", width=300)
        self.tree.column("stock", width=80)
        self.tree.column("stock_minimo", width=100)
        self.tree.column("precio", width=100)
        self.tree.column("estado", width=100)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Configurar colores para stock bajo
        self.tree.tag_configure('critico', background='#8b0000', foreground='white')
        self.tree.tag_configure('bajo', background='#b8860b', foreground='white')
        self.tree.tag_configure('ok', background='#1a4731', foreground='white')
        
        self.tree.bind("<Double-1>", lambda e: self.abrir_dialogo_modificar_producto())
        aplicar_estilo_treeview()
    
    def crear_tabla_movimientos(self, parent):
        """Crea la tabla de movimientos de inventario"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Filtros
        filtros_frame = ctk.CTkFrame(frame)
        filtros_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(filtros_frame, text="Filtrar por producto:").pack(side="left", padx=5)
        self.filtro_producto = ctk.CTkEntry(filtros_frame, width=200)
        self.filtro_producto.pack(side="left", padx=5)
        ctk.CTkButton(filtros_frame, text="🔍 Buscar", command=self.cargar_movimientos,
                     fg_color="#3498db", width=100).pack(side="left", padx=5)
        ctk.CTkButton(filtros_frame, text="Mostrar Todos", command=lambda: self.cargar_movimientos(limpiar=True),
                     fg_color="gray", width=120).pack(side="left", padx=5)
        
        # Tabla de movimientos
        columns = ("fecha", "producto", "tipo", "cantidad", "usuario", "motivo")
        self.mov_tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        
        self.mov_tree.heading("fecha", text="Fecha")
        self.mov_tree.heading("producto", text="Producto")
        self.mov_tree.heading("tipo", text="Tipo")
        self.mov_tree.heading("cantidad", text="Cantidad")
        self.mov_tree.heading("usuario", text="Usuario")
        self.mov_tree.heading("motivo", text="Motivo")
        
        self.mov_tree.column("fecha", width=120)
        self.mov_tree.column("producto", width=250)
        self.mov_tree.column("tipo", width=80)
        self.mov_tree.column("cantidad", width=80)
        self.mov_tree.column("usuario", width=150)
        self.mov_tree.column("motivo", width=200)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.mov_tree.yview)
        self.mov_tree.configure(yscrollcommand=scrollbar.set)
        self.mov_tree.pack(side="left", fill="both", expand=True, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        aplicar_estilo_treeview()
        self.crear_tabla_movimientos_db()
    
    def crear_tabla_movimientos_db(self):
        """Crea la tabla de movimientos en la BD si no existe"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventario_movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                producto_nombre TEXT NOT NULL,
                tipo TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                usuario_id INTEGER,
                usuario_nombre TEXT,
                motivo TEXT,
                fecha TEXT NOT NULL,
                FOREIGN KEY (producto_id) REFERENCES inventario(id)
            )
        """)
        conn.commit()
        conn.close()
    
    def crear_formulario_nuevo_producto(self, parent):
        """Formulario para agregar nuevo producto"""
        form_frame = ctk.CTkFrame(parent)
        form_frame.pack(pady=20, padx=20, fill="x")
        
        campos = [
            ("Nombre del Producto:*", "nombre"),
            ("Stock Inicial:", "stock"),
            ("Precio de Venta ($ ej. 25.50 o 25,50):*", "precio"),
            ("Stock Mínimo de Alerta:", "stock_minimo")
        ]
        
        self.nuevo_entries = {}
        for label, key in campos:
            frame = ctk.CTkFrame(form_frame)
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=label, width=240, anchor="w").pack(side="left", padx=10)
            entry = ctk.CTkEntry(frame, width=250)
            entry.pack(side="left", padx=10)
            self.nuevo_entries[key] = entry
        
        # Valores por defecto
        self.nuevo_entries["stock"].insert(0, "0")
        self.nuevo_entries["precio"].insert(0, "0.00")
        self.nuevo_entries["stock_minimo"].insert(0, "5")
        
        ctk.CTkButton(form_frame, text="✅ Crear Producto", command=self.crear_producto,
                     fg_color="#d4af37", text_color="black", height=40, width=200).pack(pady=20)
    
    def cargar_inventario(self):
        """Carga la lista de productos con alertas de stock"""
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, stock, stock_minimo, precio FROM inventario ORDER BY nombre")
        
        for row in cursor:
            producto_id, nombre, stock, stock_minimo, precio = row
            estado = "OK"
            tag = 'ok'
            
            if stock <= 0:
                estado = "⚠️ AGOTADO"
                tag = 'critico'
            elif stock <= stock_minimo:
                estado = f"⚠️ STOCK BAJO (mín: {stock_minimo})"
                tag = 'bajo'
            else:
                estado = "✓ Normal"
            
            self.tree.insert("", "end", values=(
                producto_id, nombre, stock, stock_minimo, f"${precio:.2f}", estado
            ), tags=(tag,))
        
        conn.close()
    
    def cargar_movimientos(self, limpiar=False):
        """Carga el historial de movimientos"""
        if limpiar:
            self.filtro_producto.delete(0, "end")
        
        for row in self.mov_tree.get_children():
            self.mov_tree.delete(row)
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        filtro = self.filtro_producto.get().strip()
        if filtro:
            cursor.execute("""
                SELECT fecha, producto_nombre, tipo, cantidad, usuario_nombre, motivo
                FROM inventario_movimientos
                WHERE producto_nombre LIKE ?
                ORDER BY fecha DESC
                LIMIT 100
            """, (f"%{filtro}%",))
        else:
            cursor.execute("""
                SELECT fecha, producto_nombre, tipo, cantidad, usuario_nombre, motivo
                FROM inventario_movimientos
                ORDER BY fecha DESC
                LIMIT 100
            """)
        
        for row in cursor:
            self.mov_tree.insert("", "end", values=row)
        
        conn.close()
    
    def registrar_movimiento(self, producto_id, producto_nombre, tipo, cantidad, motivo):
        """Registra un movimiento en el historial"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventario_movimientos 
            (producto_id, producto_nombre, tipo, cantidad, usuario_id, usuario_nombre, motivo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            producto_id, producto_nombre, tipo, cantidad,
            self.usuario[0], self.usuario[1], motivo,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
    
    def abrir_dialogo_aumentar_stock(self):
        """Diálogo para aumentar stock de un producto"""
        seleccion = self.tree.selection()
        if not seleccion:
            mb.showwarning("Selección", "Seleccione un producto de la lista")
            return
        
        item = self.tree.item(seleccion[0])
        producto_id = item['values'][0]
        producto_nombre = item['values'][1]
        
        dialog = ctk.CTkInputDialog(
            text=f"Agregar stock a:\n{producto_nombre}\n\nCantidad a agregar:",
            title="Agregar Stock"
        )
        cantidad_str = dialog.get_input()
        
        if not cantidad_str:
            return
        
        try:
            cantidad = int(cantidad_str)
            if cantidad <= 0:
                raise ValueError
        except:
            mb.showerror("Error", "Ingrese una cantidad válida (número positivo)")
            return
        
        motivo = self.pedir_motivo("Motivo del ingreso:")
        if motivo is False:
            return
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("UPDATE inventario SET stock = stock + ? WHERE id = ?", (cantidad, producto_id))
        conn.commit()
        conn.close()
        
        self.registrar_movimiento(producto_id, producto_nombre, "ENTRADA", cantidad, motivo)
        ContratoRepository.registrar_bitacora(self.usuario[0], "Aumento de stock",
                                              f"{producto_nombre}: +{cantidad}")
        
        mb.showinfo("Éxito", f"Se agregaron {cantidad} unidades a {producto_nombre}")
        self.cargar_inventario()
        self.cargar_movimientos()
    
    def abrir_dialogo_reducir_stock(self):
        """Diálogo para reducir stock de un producto"""
        seleccion = self.tree.selection()
        if not seleccion:
            mb.showwarning("Selección", "Seleccione un producto de la lista")
            return
        
        item = self.tree.item(seleccion[0])
        producto_id = item['values'][0]
        producto_nombre = item['values'][1]
        stock_actual = item['values'][2]
        
        if stock_actual <= 0:
            mb.showwarning("Stock agotado", "Este producto no tiene stock para reducir")
            return
        
        dialog = ctk.CTkInputDialog(
            text=f"Reducir stock de:\n{producto_nombre}\nStock actual: {stock_actual}\n\nCantidad a retirar:",
            title="Reducir Stock"
        )
        cantidad_str = dialog.get_input()
        
        if not cantidad_str:
            return
        
        try:
            cantidad = int(cantidad_str)
            if cantidad <= 0:
                raise ValueError
            if cantidad > stock_actual:
                mb.showerror("Error", f"No hay suficiente stock. Stock actual: {stock_actual}")
                return
        except:
            mb.showerror("Error", "Ingrese una cantidad válida")
            return
        
        motivo = self.pedir_motivo("Motivo de la salida:")
        if motivo is False:
            return
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("UPDATE inventario SET stock = stock - ? WHERE id = ?", (cantidad, producto_id))
        conn.commit()
        conn.close()
        
        self.registrar_movimiento(producto_id, producto_nombre, "SALIDA", cantidad, motivo)
        ContratoRepository.registrar_bitacora(self.usuario[0], "Reducción de stock",
                                              f"{producto_nombre}: -{cantidad}")
        
        mb.showinfo("Éxito", f"Se retiraron {cantidad} unidades de {producto_nombre}")
        self.cargar_inventario()
        self.cargar_movimientos()
    
    def abrir_dialogo_modificar_producto(self):
        """Diálogo para editar precio, nombre y stock mínimo de un producto seleccionado"""
        seleccion = self.tree.selection()
        if not seleccion:
            mb.showwarning("Selección Requerida", "Seleccione un producto de la lista para modificar su precio o información.")
            return

        item = self.tree.item(seleccion[0])
        producto_id = item['values'][0]
        producto_nombre = item['values'][1]
        stock_actual = item['values'][2]
        stock_min_actual = item['values'][3]
        precio_actual_str = str(item['values'][4]).replace("$", "").replace(",", "").strip()

        # Modal
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Modificar Producto: {producto_nombre}")
        dialog.geometry("450x380")
        dialog.resizable(False, False)
        dialog.grab_set()

        # Centrar
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (380 // 2)
        dialog.geometry(f"450x380+{x}+{y}")

        ctk.CTkLabel(dialog, text="✏️ Modificar Producto y Precio", font=("Segoe UI", 16, "bold"), text_color="#d4af37").pack(pady=(15, 10))

        content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        content_frame.pack(fill="x", padx=25, pady=5)

        # Nombre
        ctk.CTkLabel(content_frame, text="Nombre del Producto:*", font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x", pady=(5, 2))
        nombre_entry = ctk.CTkEntry(content_frame, width=380)
        nombre_entry.insert(0, producto_nombre)
        nombre_entry.pack(fill="x", pady=(0, 8))

        # Precio de Venta (con soporte de decimales tanto con punto como con coma)
        ctk.CTkLabel(content_frame, text="Precio de Venta ($ ej. 25.50 o 25,50):*", font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x", pady=(5, 2))
        precio_entry = ctk.CTkEntry(content_frame, width=380)
        precio_entry.insert(0, precio_actual_str)
        precio_entry.pack(fill="x", pady=(0, 8))

        # Stock Mínimo
        ctk.CTkLabel(content_frame, text="Stock Mínimo para Alerta:", font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x", pady=(5, 2))
        stock_min_entry = ctk.CTkEntry(content_frame, width=380)
        stock_min_entry.insert(0, str(stock_min_actual))
        stock_min_entry.pack(fill="x", pady=(0, 15))

        # Label informativo
        info_lbl = ctk.CTkLabel(content_frame, text=f"Stock físico actual: {stock_actual} unidades (no se modifica aquí)", font=("Segoe UI", 10), text_color="gray")
        info_lbl.pack(pady=(0, 10))

        # Guardar cambios
        def guardar_modificacion():
            nuevo_nombre = nombre_entry.get().strip()
            if not nuevo_nombre:
                mb.showwarning("Campo Obligatorio", "El nombre del producto no puede estar vacío.", parent=dialog)
                return

            try:
                nuevo_precio = parsear_decimal_monetario(precio_entry.get())
                if nuevo_precio <= 0:
                    raise ValueError
            except ValueError:
                mb.showerror("Precio Inválido", "Ingrese un precio de venta numérico válido (ej. 25.50 o 25,50 mayor a 0).", parent=dialog)
                return

            try:
                nuevo_stock_min = int(stock_min_entry.get().strip() or 5)
            except Exception:
                nuevo_stock_min = 5

            conn = obtener_conexion()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE inventario
                    SET nombre = ?, precio = ?, stock_minimo = ?
                    WHERE id = ?
                """, (nuevo_nombre, nuevo_precio, nuevo_stock_min, producto_id))
                conn.commit()

                ContratoRepository.registrar_bitacora(
                    self.usuario[0],
                    "Modificación de producto",
                    f"ID #{producto_id}: '{nuevo_nombre}' | Precio: ${nuevo_precio:.2f} | Stock Mín: {nuevo_stock_min}"
                )

                mb.showinfo("Éxito", f"✅ Producto actualizado correctamente:\nPrecio de venta: ${nuevo_precio:,.2f}", parent=dialog)
                dialog.destroy()
                self.cargar_inventario()
            except Exception as ex:
                mb.showerror("Error", f"No se pudo actualizar el producto: {str(ex)}", parent=dialog)
            finally:
                conn.close()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=25, pady=10)
        ctk.CTkButton(btn_row, text="💾 Guardar Cambios", command=guardar_modificacion,
                     fg_color="#2ecc71", text_color="black", font=("Segoe UI", 12, "bold"), height=35).pack(side="left", expand=True, fill="x", padx=5)
        ctk.CTkButton(btn_row, text="Cancelar", command=dialog.destroy,
                     fg_color="#e74c3c", height=35).pack(side="left", expand=True, fill="x", padx=5)

    def pedir_motivo(self, titulo):
        """Solicita un motivo para el movimiento"""
        dialog = ctk.CTkInputDialog(text=titulo, title="Motivo")
        motivo = dialog.get_input()
        if not motivo:
            return False
        return motivo
    
    def crear_producto(self):
        """Crea un nuevo producto en el inventario"""
        nombre = self.nuevo_entries["nombre"].get().strip()
        if not nombre:
            mb.showwarning("Campo requerido", "El nombre del producto es obligatorio")
            return
        
        try:
            stock = int(self.nuevo_entries["stock"].get() or 0)
            if stock < 0:
                stock = 0
        except:
            stock = 0
        
        try:
            precio = parsear_decimal_monetario(self.nuevo_entries["precio"].get())
            if precio <= 0:
                mb.showwarning("Precio inválido", "El precio de venta debe ser mayor a 0 (ej. 25.50 o 25,50)")
                return
        except ValueError:
            mb.showerror("Error", "Ingrese un precio de venta numérico válido (ej. 25.50 o 25,50)")
            return
        
        try:
            stock_minimo = int(self.nuevo_entries["stock_minimo"].get() or 5)
        except:
            stock_minimo = 5
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO inventario (nombre, stock, precio, stock_minimo)
                VALUES (?, ?, ?, ?)
            """, (nombre, stock, precio, stock_minimo))
            conn.commit()
            
            producto_id = cursor.lastrowid
            if stock > 0:
                self.registrar_movimiento(producto_id, nombre, "ENTRADA INICIAL", stock, "Creación de producto")
            
            ContratoRepository.registrar_bitacora(self.usuario[0], "Creación de producto",
                                                  f"Nuevo producto: {nombre}")
            
            mb.showinfo("Éxito", f"Producto '{nombre}' creado correctamente")
            
            # Limpiar formulario
            self.nuevo_entries["nombre"].delete(0, "end")
            self.nuevo_entries["stock"].delete(0, "end")
            self.nuevo_entries["stock"].insert(0, "0")
            self.nuevo_entries["precio"].delete(0, "end")
            self.nuevo_entries["stock_minimo"].delete(0, "end")
            self.nuevo_entries["stock_minimo"].insert(0, "5")
            
            self.cargar_inventario()
            self.cargar_movimientos()
            
        except sqlite3.IntegrityError:
            mb.showerror("Error", "Ya existe un producto con ese nombre")
        except Exception as e:
            mb.showerror("Error", f"No se pudo crear: {str(e)}")
        finally:
            conn.close()