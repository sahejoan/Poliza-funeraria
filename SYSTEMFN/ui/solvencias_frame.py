"""Interfaz de consulta y emisión de certificados de solvencia."""
import os
import tkinter.messagebox as mb
from tkinter import ttk

import customtkinter as ctk

from services.solvencia_service import SolvenciaService
from utils.helpers import aplicar_estilo_treeview, formatear_fecha_ddmmyyyy


class SolvenciasFrame(ctk.CTkFrame):
    """Permite consultar el saldo de contratos y emitir solvencias verificadas."""

    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.usuario = usuario
        self.contratos = {}
        self.configure(fg_color="transparent")
        self.crear_interfaz()
        self.buscar_contratos()

    def crear_interfaz(self):
        ctk.CTkLabel(
            self, text="Consultas de Solvencia de Contratos",
            font=("Segoe UI", 26, "bold"), text_color="#D4AF37"
        ).pack(pady=(20, 8))
        ctk.CTkLabel(
            self,
            text="Busque por número de contrato, nombre, apellido o cédula. "
                 "La mora se determina por cuotas vencidas; también se muestran períodos con pagos "
                 "y el saldo pendiente del contrato.",
            font=("Segoe UI", 11), wraplength=950
        ).pack(pady=(0, 12))

        filtros = ctk.CTkFrame(self, fg_color=("#FFFFFF", "#1A1E26"), corner_radius=10)
        filtros.pack(fill="x", padx=20, pady=8)
        self.busqueda = ctk.CTkEntry(
            filtros, width=420,
            placeholder_text="N° contrato, nombre o cédula"
        )
        self.busqueda.pack(side="left", padx=12, pady=12)
        self.busqueda.bind("<Return>", lambda _event: self.buscar_contratos())
        ctk.CTkButton(
            filtros, text="Buscar / Actualizar", command=self.buscar_contratos,
            fg_color="#3498DB"
        ).pack(side="left", padx=5)
        self.btn_pdf = ctk.CTkButton(
            filtros, text="Generar PDF de solvencia",
            command=self.generar_pdf_seleccionado,
            fg_color="#D4AF37", hover_color="#B8960C", text_color="#101318",
            state="disabled"
        )
        self.btn_pdf.pack(side="right", padx=12)

        tabla = ctk.CTkFrame(self, fg_color=("#FFFFFF", "#1A1E26"), corner_radius=10)
        tabla.pack(fill="both", expand=True, padx=20, pady=8)
        columnas = (
            "numero", "titular", "cedula", "difunto",
            "total", "pagado", "saldo", "solvencia"
        )
        self.tree = ttk.Treeview(tabla, columns=columnas, show="headings", height=14)
        titulos = {
            "numero": "Contrato", "titular": "Titular", "cedula": "Cédula",
            "difunto": "Difunto / Beneficiario", "total": "Total",
            "pagado": "Pagado", "saldo": "Saldo", "solvencia": "Resultado",
        }
        anchos = {
            "numero": 150, "titular": 180, "cedula": 110, "difunto": 180,
            "total": 100, "pagado": 100, "saldo": 100, "solvencia": 120,
        }
        for columna in columnas:
            self.tree.heading(columna, text=titulos[columna])
            self.tree.column(columna, width=anchos[columna], anchor="center")
        barra = ttk.Scrollbar(tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        barra.pack(side="right", fill="y", padx=(0, 10), pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_seleccion)
        self.tree.bind("<Double-1>", self.on_doble_click)
        aplicar_estilo_treeview()

        self.detalle = ctk.CTkLabel(
            self, text="Seleccione un contrato para consultar su estado.",
            font=("Segoe UI", 12), anchor="w", justify="left", wraplength=1100
        )
        self.detalle.pack(fill="x", padx=25, pady=(4, 16))

    def buscar_contratos(self):
        for fila in self.tree.get_children():
            self.tree.delete(fila)
        self.contratos.clear()
        self.btn_pdf.configure(state="disabled")
        try:
            contratos = SolvenciaService.consultar(self.busqueda.get())
        except Exception as exc:
            mb.showerror("Error de consulta", f"No se pudieron consultar las solvencias:\n{exc}")
            return

        for contrato in contratos:
            item = self.tree.insert("", "end", values=(
                contrato["numero"], contrato["titular"], contrato["titular_cedula"],
                contrato["difunto"], f"${contrato['monto_total']:,.2f}",
                f"${contrato['pagado']:,.2f}", f"${contrato['saldo_pendiente']:,.2f}",
                contrato["estado_solvencia"],
            ))
            self.contratos[item] = contrato

        self.detalle.configure(
            text=f"Contratos encontrados: {len(contratos)}. "
                 "Los certificados solo se emiten para contratos solventes."
        )

    def on_seleccion(self, _event=None):
        seleccion = self.tree.selection()
        if not seleccion:
            self.btn_pdf.configure(state="disabled")
            return
        contrato = self.contratos[seleccion[0]]
        self.btn_pdf.configure(state="normal" if contrato["solvente"] else "disabled")
        periodos = contrato["periodos_con_pagos"]
        cuotas_pendientes = contrato["cuotas_pendientes"]
        cuotas_vencidas = contrato["cuotas_vencidas"]
        resumen_periodos = ", ".join(
            f"{periodo['periodo']} (${periodo['monto']:,.2f})"
            for periodo in periodos
        ) if periodos else "Sin períodos registrados"
        resumen_pendientes = ", ".join(cuotas_pendientes) if cuotas_pendientes else "Ninguna"
        resumen_vencidas = ", ".join(
            f"{cuota['etiqueta']} (${cuota['saldo']:,.2f})"
            for cuota in cuotas_vencidas
        ) if cuotas_vencidas else "Ninguna"
        self.detalle.configure(
            text=(
                f"Contrato {contrato['numero']} · {contrato['estado_solvencia']} · "
                f"Estado: {contrato['estado_contrato']} · "
                f"Fecha: {formatear_fecha_ddmmyyyy(contrato['fecha_contrato'])} · "
                f"Tipo: {contrato['tipo_contrato']} · "
                f"Total: ${contrato['monto_total']:,.2f} · "
                f"Pagado: ${contrato['pagado']:,.2f} · "
                f"Saldo por pagar: ${contrato['saldo_pendiente']:,.2f} · "
                f"Saldo vencido: ${contrato['monto_vencido']:,.2f}\n"
                f"Períodos con pagos registrados: {resumen_periodos}\n"
                f"Cuotas pendientes: {resumen_pendientes}\n"
                f"Cuotas vencidas: {resumen_vencidas}"
            )
        )

    def on_doble_click(self, _event=None):
        if self.tree.selection():
            contrato = self.contratos[self.tree.selection()[0]]
            if contrato["solvente"]:
                self.generar_pdf_seleccionado()

    def generar_pdf_seleccionado(self):
        seleccion = self.tree.selection()
        if not seleccion:
            mb.showwarning("Selección requerida", "Seleccione un contrato solvente.")
            return
        contrato = self.contratos[seleccion[0]]
        if not contrato["solvente"]:
            mb.showwarning(
                "Contrato no solvente",
                "No se genera el certificado porque el contrato está cancelado o mantiene saldo.",
            )
            return

        try:
            from services.pdf_service import generar_pdf_solvencia
            ruta = generar_pdf_solvencia(contrato["id"])
            if not ruta or not os.path.exists(ruta):
                raise OSError("No se encontró el PDF generado.")
        except Exception as exc:
            mb.showerror("Error al generar PDF", f"No se pudo generar la solvencia:\n{exc}")
            return

        mb.showinfo("Solvencia generada", f"PDF guardado en:\n{ruta}")
        try:
            os.startfile(ruta)
        except OSError:
            pass
