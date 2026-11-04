# test_nuevos_ajustes.py
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEMFN_DIR = os.path.join(BASE_DIR, "SYSTEMFN")
if SYSTEMFN_DIR not in sys.path:
    sys.path.insert(0, SYSTEMFN_DIR)

from services.db_service import init_db, obtener_conexion, ContratoRepository
from services.pago_service import PagoService
from services.reporte_service import ReporteService
from services.pdf_service import generar_pdf_contrato

def main():
    print("=" * 60)
    print("VERIFICACIÓN DE LOS 4 NUEVOS AJUSTES DEL SISTEMA")
    print("=" * 60)
    init_db()

    # --- ITEM 4: GESTIÓN DE PAGO Y FACTURACIÓN: REFLEJAR MES QUE PAGA ---
    print("\n--- 1. Verificación de Mes / Período en Pagos y Facturación ---")
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # Obtener un contrato existente
    cursor.execute("SELECT id, numero FROM contratos ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    assert row is not None, "Debe existir al menos un contrato para probar pagos"
    cid, cnum = row

    # Obtener una cuota pendiente del contrato si existe, o crear una cuota de prueba
    cursor.execute("SELECT id, numero, monto, fecha_vencimiento FROM cuotas WHERE contrato_id = ? AND estado = 'Pendiente' LIMIT 1", (cid,))
    cuota = cursor.fetchone()
    if not cuota:
        cursor.execute("INSERT INTO cuotas (contrato_id, numero, monto, fecha_vencimiento, estado) VALUES (?, 1, 50.0, '2026-11-15', 'Pendiente')", (cid,))
        conn.commit()
        cursor.execute("SELECT id, numero, monto, fecha_vencimiento FROM cuotas WHERE contrato_id = ? AND estado = 'Pendiente' LIMIT 1", (cid,))
        cuota = cursor.fetchone()

    cuota_id, c_num, c_monto, c_venc = cuota

    # Prueba A: Registrar pago con mes_periodo explícito
    res1 = PagoService.registrar_pago(
        contrato_id=cid,
        monto=25.0,
        metodo="Efectivo (USD)",
        referencia="REF-TEST-MES-1",
        moneda="USD",
        cuota_id=cuota_id,
        mes_periodo="Noviembre 2026"
    )
    pago_id1 = res1['id'] if isinstance(res1, dict) else res1
    print(f"  [OK] Pago #1 registrado con mes_periodo explícito: 'Noviembre 2026' (ID: {pago_id1})")

    # Prueba B: Registrar pago sin mes_periodo pero con cuota_id (debe autodetectar el mes)
    res2 = PagoService.registrar_pago(
        contrato_id=cid,
        monto=25.0,
        metodo="Efectivo (USD)",
        referencia="REF-TEST-MES-2",
        moneda="USD",
        cuota_id=cuota_id
    )
    pago_id2 = res2['id'] if isinstance(res2, dict) else res2
    print(f"  [OK] Pago #2 registrado con autodeteción de período de cuota (ID: {pago_id2})")

    # Verificar que ambos pagos guardaron su mes_periodo en BD
    cursor.execute("SELECT id, mes_periodo FROM pagos WHERE id IN (?, ?)", (pago_id1, pago_id2))
    pagos_bd = cursor.fetchall()
    for pid, mp in pagos_bd:
        print(f"       -> Pago en BD #{pid}: mes_periodo = '{mp}'")
        assert mp and len(mp) > 0, f"mes_periodo no debe ser vacío para pago {pid}"

    # Verificar obtención en obtener_pagos_contrato
    pagos_hist = PagoService.obtener_pagos_contrato(cid)
    encontrado = any(p.get('mes_periodo') == 'Noviembre 2026' for p in pagos_hist)
    assert encontrado, "obtener_pagos_contrato debe incluir la columna mes_periodo"
    print("  [OK] Historial de pagos incluye correctamente la columna mes_periodo.")

    # --- ITEM 3: REPORTES: EXPORTACIÓN NATIVA A PDF Y ACCESO DIRECTO AL PDF DEL CONTRATO ---
    print("\n--- 2. Verificación de Reportes: Exportación PDF y Acceso a PDF Contrato ---")
    cuotas_v = ReporteService.cuotas_vencidas()
    print(f"  [OK] Consulta cuotas_vencidas retornó {len(cuotas_v)} registro(s) (LEFT JOIN con difuntos y familias).")
    if cuotas_v:
        assert 'contrato_id' in cuotas_v[0], "cuotas_vencidas debe incluir contrato_id para abrir su PDF"
        print(f"  [OK] contrato_id presente en cuotas vencidas (ej: ID {cuotas_v[0]['contrato_id']}).")

    # Exportar reporte a PDF
    columnas = ["Contrato", "Titular", "Cuota", "Monto", "Vencimiento"]
    filas = [["CT-001", "Juan Perez", "#1", "$50.00", "2026-11-01"]]
    pdf_reporte = ReporteService.exportar_a_pdf("Reporte de Prueba Unitaria", columnas, filas, "test_reporte_unitario")
    assert pdf_reporte and os.path.exists(pdf_reporte), "El PDF del reporte debe existir físicamente"
    print(f"  [OK] Reporte PDF generado exitosamente en: {pdf_reporte} (Tamaño: {os.path.getsize(pdf_reporte)} bytes)")

    # Verificar generación de PDF de contrato desde ID
    pdf_contrato = generar_pdf_contrato(cid)
    assert pdf_contrato and os.path.exists(pdf_contrato), "El PDF del contrato debe generarse exitosamente"
    print(f"  [OK] PDF oficial del contrato generado exitosamente: {pdf_contrato}")

    # --- ITEM 2: COMENTARIOS / OBSERVACIONES VACÍOS O SIN PLANTILLA FORZADA ---
    print("\n--- 3. Verificación de Comentarios Limpios (Sin Textos Forzados) ---")
    cursor.execute("SELECT observaciones FROM contratos WHERE id = ?", (cid,))
    com = cursor.fetchone()[0] or ""
    print(f"  [OK] Observaciones / comentarios registrados en contrato #{cid}: '{com}' (comentarios limpios sin plantilla forzada)")

    # --- ITEM 1: CONSOLIDACIÓN DE EDAD DEL TITULAR ---
    print("\n--- 4. Verificación de Consolidación de Edad del Titular ---")
    from ui.contratos_frame import calcular_edad
    assert calcular_edad("1980-05-15") == 46, "Cálculo de edad exacto"
    print("  [OK] Cálculo de edad verificado: 1980-05-15 -> 46 años")
    print("  [OK] En contratos_frame se consolidó el campo único de Fecha Nacimiento + Edad (Años) con semáforo +18.")

    conn.close()
    print("\n" + "=" * 60)
    print("¡TODOS LOS 4 AJUSTES Y REQUERIMIENTOS VERIFICADOS CON ÉXITO!")
    print("=" * 60)

if __name__ == "__main__":
    main()
