import datetime
import hashlib
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from openpyxl import load_workbook

from services import auth_service, db_service, pdf_service
from services.pago_service import PagoService
from services.pdf_service import generar_pdf_recibo_pago, generar_pdf_solvencia
from services.reporte_service import ReporteService
from services.solvencia_service import SolvenciaService
from ui.pagos_frame import PagosFrame
from ui.reportes_frame import ReportesFrame
from utils.helpers import (
    formatear_fecha_ddmmyyyy,
    normalizar_fecha_iso,
    parsear_decimal_monetario,
)


class SolvenciaYAjustesTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "pruebas.db")
        self.patch_db = patch.object(db_service, "DB_PATH", self.db_path)
        self.patch_pdf = patch.object(
            pdf_service, "CONTRATOS_DIR", os.path.join(self.temp_dir.name, "pdf")
        )
        self.patch_db.start()
        self.patch_pdf.start()
        db_service.init_db()
        self.familia_id = "FAM-TEST-SOLVENCIA"
        conn = db_service.obtener_conexion()
        try:
            conn.execute("""
                INSERT INTO usuarios (usuario, password, nombre, rol, fecha_creacion)
                VALUES ('test-admin', 'hash-pruebas', 'Usuario de prueba', 'admin', '2026-11-03')
            """)
            conn.execute("""
                INSERT INTO familias (
                    familia_id, resp_cedula, resp_nombre, resp_apellido,
                    resp_telefono, resp_email, resp_direccion, fecha_creacion
                ) VALUES (?, ?, ?, ?, '', '', '', '2026-11-03')
            """, (self.familia_id, "V-12.345.678", "Ana", "Pérez"))
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        self.patch_pdf.stop()
        self.patch_db.stop()
        self.temp_dir.cleanup()

    def test_inicializacion_crea_administrador_admin123_con_hash_seguro(self):
        conn = db_service.obtener_conexion()
        try:
            conn.execute("DELETE FROM usuarios")
            conn.commit()
        finally:
            conn.close()

        db_service.init_db()

        autenticado = auth_service.autenticar("admin", "admin123")
        self.assertIsNotNone(autenticado)
        self.assertEqual(autenticado[1:], ("admin", "Administrador", "admin"))
        conn = db_service.obtener_conexion()
        try:
            almacenada = conn.execute(
                "SELECT password FROM usuarios WHERE usuario = 'admin'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertTrue(almacenada.startswith("pbkdf2_sha256$"))

    def test_autenticacion_migra_hash_sha256_heredado(self):
        password = "Clave antigua de usuario"
        conn = db_service.obtener_conexion()
        try:
            conn.execute("""
                INSERT INTO usuarios (usuario, password, nombre, rol, fecha_creacion)
                VALUES ('operador', ?, 'Operador', 'usuario', '2026-11-04')
            """, (hashlib.sha256(password.encode()).hexdigest(),))
            conn.commit()
        finally:
            conn.close()

        autenticado = auth_service.autenticar("operador", password)
        self.assertIsNotNone(autenticado)
        self.assertEqual(autenticado[1:], ("operador", "Operador", "usuario"))
        conn = db_service.obtener_conexion()
        try:
            almacenada = conn.execute(
                "SELECT password FROM usuarios WHERE usuario = 'operador'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertTrue(almacenada.startswith("pbkdf2_sha256$"))

    def crear_contrato(self, numero, total, pagado, estado="Activo", pnf=False):
        conn = db_service.obtener_conexion()
        try:
            cursor = conn.execute("""
                INSERT INTO contratos (
                    numero, fecha_contrato, familia_id, paquete, monto_total,
                    metodo_pago, pagado, estado, tipo_contrato, pnf_asociado
                ) VALUES (?, '2026-11-03', ?, 'PLATA', ?, 'Financiado', ?, ?, 'Largo Plazo', ?)
            """, (numero, self.familia_id, total, pagado, estado, int(pnf)))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def test_busqueda_y_regla_de_solvencia(self):
        id_ok = self.crear_contrato("CT-SOLVENTE-01", 100, 99.99)
        id_saldo = self.crear_contrato("CT-PENDIENTE-01", 100, 99.98)
        id_cancelado = self.crear_contrato("CT-CANCELADO-01", 100, 100, "Cancelado")

        por_cedula = SolvenciaService.consultar("12345678")
        self.assertIn(id_ok, [c["id"] for c in por_cedula])
        self.assertIn(id_ok, [c["id"] for c in SolvenciaService.consultar("Pérez Ana")])
        self.assertIn(id_ok, [c["id"] for c in SolvenciaService.consultar("Pérez")])
        self.assertIn(id_ok, [c["id"] for c in SolvenciaService.consultar("Perez Ana")])
        resultados = {c["id"]: c for c in SolvenciaService.consultar("CT-")}
        self.assertTrue(resultados[id_ok]["solvente"])
        self.assertEqual(resultados[id_ok]["saldo_pendiente"], 0)
        self.assertFalse(resultados[id_saldo]["solvente"])
        self.assertEqual(resultados[id_saldo]["saldo_pendiente"], 0.02)
        self.assertFalse(resultados[id_cancelado]["solvente"])

    def test_estado_de_cuenta_muestra_periodos_y_mora_por_cuota_vencida(self):
        contrato_id = self.crear_contrato("CT-MORA-01", 100, 0)
        hoy = datetime.date.today()
        vencida = (hoy - datetime.timedelta(days=1)).isoformat()
        futura = (hoy + datetime.timedelta(days=30)).isoformat()
        conn = db_service.obtener_conexion()
        try:
            cuota_vencida = conn.execute("""
                INSERT INTO cuotas (contrato_id, numero, monto, fecha_vencimiento)
                VALUES (?, 1, 50, ?)
            """, (contrato_id, vencida)).lastrowid
            conn.execute("""
                INSERT INTO cuotas (contrato_id, numero, monto, fecha_vencimiento)
                VALUES (?, 2, 50, ?)
            """, (contrato_id, futura))
            conn.commit()
        finally:
            conn.close()

        PagoService.registrar_pago(
            contrato_id, 25, "Efectivo (USD)", cuota_id=cuota_vencida,
            mes_periodo="Cuota #1 - Noviembre 2026",
        )
        cuenta = SolvenciaService.obtener_por_id(contrato_id)
        self.assertEqual(cuenta["estado_solvencia"], "MOROSO")
        self.assertEqual(cuenta["monto_vencido"], 25)
        self.assertEqual(cuenta["saldo_pendiente"], 75)
        self.assertEqual(cuenta["periodos_con_pagos"], [{
            "periodo": "Cuota #1 - Noviembre 2026", "monto": 25,
        }])

        PagoService.registrar_pago(
            contrato_id, 25, "Efectivo (USD)", cuota_id=cuota_vencida,
            mes_periodo="Cuota #1 - Noviembre 2026",
        )
        cuenta = SolvenciaService.obtener_por_id(contrato_id)
        self.assertEqual(cuenta["estado_solvencia"], "PENDIENTE")
        self.assertEqual(cuenta["monto_vencido"], 0)
        self.assertEqual(cuenta["saldo_pendiente"], 50)
        self.assertEqual(len(cuenta["cuotas_pendientes"]), 1)

    def test_pdf_solo_para_contrato_solvente(self):
        id_ok = self.crear_contrato("CT-PDF-01", 50, 50)
        id_pendiente = self.crear_contrato("CT-PDF-02", 50, 49)

        ruta = generar_pdf_solvencia(id_ok)
        self.assertTrue(os.path.isfile(ruta))
        self.assertGreater(os.path.getsize(ruta), 500)
        with self.assertRaises(ValueError):
            generar_pdf_solvencia(id_pendiente)

    def test_periodo_pnf_se_guarda_y_se_emite_en_recibo(self):
        contrato_id = self.crear_contrato("CT-PNF-01", 100, 0, pnf=True)
        pago = PagoService.registrar_pago(
            contrato_id=contrato_id,
            monto=25.50,
            metodo="Efectivo (USD)",
            mes_periodo="Mes: Noviembre 2026",
        )
        historial = PagoService.obtener_pagos_contrato(contrato_id)
        self.assertEqual(historial[0]["mes_periodo"], "Mes: Noviembre 2026")
        cuenta = SolvenciaService.obtener_por_id(contrato_id)
        self.assertEqual(
            cuenta["periodos_con_pagos"], [{
                "periodo": "Mes: Noviembre 2026", "monto": 25.5,
            }]
        )
        self.assertEqual(cuenta["estado_solvencia"], "PENDIENTE")

        ruta = generar_pdf_recibo_pago(pago["id"])
        self.assertTrue(os.path.isfile(ruta))
        self.assertGreater(os.path.getsize(ruta), 500)

    def test_saldo_de_cuota_refleja_abonos_parciales_y_rechaza_exceso(self):
        contrato_id = self.crear_contrato("CT-CUOTA-PARCIAL-01", 100, 0)
        conn = db_service.obtener_conexion()
        try:
            cuota_id = conn.execute("""
                INSERT INTO cuotas (contrato_id, numero, monto, fecha_vencimiento)
                VALUES (?, 1, 60, '2026-12-01')
            """, (contrato_id,)).lastrowid
            conn.commit()
        finally:
            conn.close()

        PagoService.registrar_pago(
            contrato_id, 20, "Efectivo (USD)", cuota_id=cuota_id
        )
        cuota = PagoService.obtener_cuotas_con_saldos(contrato_id)[0]
        self.assertEqual(cuota["monto"], 60)
        self.assertEqual(cuota["pagado"], 20)
        self.assertEqual(cuota["saldo"], 40)
        self.assertEqual(cuota["estado"], "Pendiente")

        with self.assertRaisesRegex(ValueError, "excede el saldo de la cuota"):
            PagoService.registrar_pago(
                contrato_id, 41, "Efectivo (USD)", cuota_id=cuota_id
            )

        PagoService.registrar_pago(
            contrato_id, 40, "Efectivo (USD)", cuota_id=cuota_id
        )
        cuota = PagoService.obtener_cuotas_con_saldos(contrato_id)[0]
        self.assertEqual(cuota["pagado"], 60)
        self.assertEqual(cuota["saldo"], 0)
        self.assertEqual(cuota["estado"], "Pagada")

    def test_pago_desde_boton_de_cuota_ofrece_recibo_pdf(self):
        class Dialog:
            def __init__(self, **_kwargs):
                pass

            def get_input(self):
                return "15.00"

        frame = SimpleNamespace(
            contrato_om=SimpleNamespace(get=lambda: "CT-UI-01"),
            contrato_dict={"CT-UI-01": 1},
            cargar_detalle=Mock(),
            cargar_contratos=Mock(),
            generar_recibo_pago_pdf=Mock(),
        )
        with patch("ui.pagos_frame.ctk.CTkInputDialog", Dialog), \
                patch.object(PagoService, "registrar_pago", return_value={"id": 32}) as registrar, \
                patch("ui.pagos_frame.mb.askyesno", return_value=True) as preguntar, \
                patch("ui.pagos_frame.mb.showerror") as mostrar_error:
            PagosFrame.pagar_cuota(frame, 7, 40, 1)

        registrar.assert_called_once_with(
            contrato_id=1,
            monto=15,
            metodo="Efectivo (USD)",
            referencia="",
            moneda="USD",
            cuota_id=7,
        )
        preguntar.assert_called_once()
        frame.generar_recibo_pago_pdf.assert_called_once_with(32)
        frame.cargar_detalle.assert_called_once_with("CT-UI-01")
        frame.cargar_contratos.assert_called_once()
        mostrar_error.assert_not_called()

    def test_importes_decimales_y_fechas(self):
        self.assertEqual(parsear_decimal_monetario("25.50"), 25.50)
        self.assertEqual(parsear_decimal_monetario("25,50"), 25.50)
        self.assertEqual(parsear_decimal_monetario("$1,234.50"), 1234.50)
        self.assertEqual(parsear_decimal_monetario("1.234,50"), 1234.50)
        self.assertEqual(normalizar_fecha_iso("03/11/2026"), "2026-11-03")
        self.assertEqual(formatear_fecha_ddmmyyyy("2026-11-03"), "03/11/2026")

    def test_reporte_pdf_se_genera_con_titulo_largo_y_celdas_multilinea(self):
        directorio_original = os.getcwd()
        try:
            os.chdir(self.temp_dir.name)
            ruta = ReporteService.exportar_a_pdf(
                "Reporte de prueba con un título largo para validar el espacio del encabezado",
                ["Contrato", "Titular", "Detalle"],
                [["CT-001", "Juan Pérez", "Descripción con <caracteres> especiales y texto largo"]],
                "prueba_encabezado",
            )
            self.assertTrue(ruta)
            self.assertTrue(os.path.isfile(ruta))
            self.assertGreater(os.path.getsize(ruta), 1000)
        finally:
            os.chdir(directorio_original)

    def test_pdf_reporte_se_abre_despues_de_aceptar_aviso(self):
        llamadas = []
        directorio_original = os.getcwd()
        try:
            os.chdir(self.temp_dir.name)
            ruta_absoluta = os.path.abspath(os.path.join("reportes", "reporte.pdf"))
            with patch("ui.reportes_frame.mb.showinfo", side_effect=lambda *args: llamadas.append("aviso")), \
                    patch("ui.reportes_frame.os.startfile", side_effect=lambda ruta: llamadas.append(("abrir", ruta))):
                ReportesFrame._mostrar_pdf_generado(
                    "reportes/reporte.pdf",
                    "PDF Generado",
                    "Reporte PDF guardado en:",
                )
        finally:
            os.chdir(directorio_original)

        self.assertEqual(llamadas, ["aviso", ("abrir", ruta_absoluta)])

    def test_error_al_abrir_pdf_reporte_se_informa(self):
        with patch("ui.reportes_frame.mb.showinfo"), \
                patch("ui.reportes_frame.os.startfile", side_effect=OSError("visor no disponible")), \
                patch("ui.reportes_frame.mb.showerror") as mostrar_error:
            ReportesFrame._mostrar_pdf_generado(
                "reportes/reporte.pdf",
                "PDF Generado",
                "Reporte PDF guardado en:",
            )

        mostrar_error.assert_called_once()
        self.assertIn("visor no disponible", mostrar_error.call_args.args[1])

    def test_reporte_excel_incluye_encabezado_corporativo_y_repite_al_imprimir(self):
        directorio_original = os.getcwd()
        try:
            os.chdir(self.temp_dir.name)
            ruta = ReporteService.exportar_a_excel(
                [{"Contrato": "CT-001", "Titular": "Juan Pérez"}],
                "prueba_encabezado_excel",
            )
            self.assertTrue(ruta)
            workbook = load_workbook(ruta)
            worksheet = workbook.active
            self.assertEqual(worksheet["A1"].value, db_service.EMPRESA["nombre"])
            self.assertEqual(worksheet["A2"].value, f"RIF: {db_service.EMPRESA['rif']}")
            self.assertEqual(worksheet["A3"].value, db_service.EMPRESA["direccion"])
            self.assertEqual(
                worksheet["A4"].value,
                f"Tel: {db_service.EMPRESA['telefono']} · {db_service.EMPRESA['correo']}",
            )
            self.assertEqual([worksheet.cell(6, col).value for col in range(1, 3)],
                             ["Contrato", "Titular"])
            self.assertEqual([worksheet.cell(7, col).value for col in range(1, 3)],
                             ["CT-001", "Juan Pérez"])
            self.assertEqual(worksheet.print_title_rows, "$1:$6")
        finally:
            os.chdir(directorio_original)

    def test_metodo_efectivo_selecciona_y_fija_moneda_correcta(self):
        class Widget:
            def __init__(self, value=""):
                self.value = value
                self.options = {}

            def configure(self, **kwargs):
                self.options.update(kwargs)

            def set(self, value):
                self.value = value

            def delete(self, *_args):
                self.value = ""

            def get(self):
                return self.value

        for metodo, moneda in (("Efectivo (USD)", "USD"), ("Efectivo (BS)", "BS")):
            frame = SimpleNamespace(
                metodo_combo=Widget(metodo),
                moneda_label=Widget(),
                moneda_combo=Widget(),
                ref_label=Widget(),
                ref_entry=Widget(),
                on_moneda_cambiado=Mock(),
            )
            PagosFrame.on_metodo_cambiado(frame, None)
            self.assertEqual(frame.moneda_combo.get(), moneda)
            self.assertEqual(frame.moneda_combo.options["state"], "disabled")

    def test_pago_en_bolivares_valida_equivalente_usd(self):
        class Entry:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

            def delete(self, *_args):
                self.value = ""

        class Combo(Entry):
            def set(self, value):
                self.value = value

        frame = SimpleNamespace(
            monto_entry=Entry("1.000,00"),
            metodo_combo=Combo("Efectivo (BS)"),
            moneda_combo=Combo("USD"),
            ref_entry=Entry(""),
            mes_combo=Combo("Mes: Noviembre 2026"),
            meses_dict={"Mes: Noviembre 2026": {
                "cuota_id": None, "concepto": "Mes: Noviembre 2026",
            }},
            contrato_om=Combo("Contrato de prueba"),
            contrato_dict={},
            cargar_contratos=Mock(),
            generar_recibo_pago_pdf=Mock(),
        )

        with patch.object(PagoService, "obtener_tasa_cambio_dia", return_value=40), \
                patch.object(PagoService, "registrar_pago", return_value={"id": 9}) as registrar, \
                patch("ui.pagos_frame.mb.showinfo"), \
                patch("ui.pagos_frame.mb.showerror") as mostrar_error, \
                patch("ui.pagos_frame.mb.askyesno", return_value=False):
            PagosFrame.registrar_pago(frame, 1, 30)

        registrar.assert_called_once()
        self.assertEqual(registrar.call_args.kwargs["monto"], 1000)
        self.assertEqual(registrar.call_args.kwargs["moneda"], "BS")
        self.assertEqual(registrar.call_args.kwargs["tasa_cambio"], 40)
        mostrar_error.assert_not_called()

        frame.monto_entry = Entry("2.000,00")
        with patch.object(PagoService, "obtener_tasa_cambio_dia", return_value=40), \
                patch.object(PagoService, "registrar_pago") as registrar, \
                patch("ui.pagos_frame.mb.showerror") as mostrar_error:
            PagosFrame.registrar_pago(frame, 1, 30)
        registrar.assert_not_called()
        mostrar_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
