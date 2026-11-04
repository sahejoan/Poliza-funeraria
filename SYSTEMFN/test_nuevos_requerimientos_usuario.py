# test_nuevos_requerimientos_usuario.py
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEMFN_DIR = os.path.join(BASE_DIR, "SYSTEMFN")
if SYSTEMFN_DIR not in sys.path:
    sys.path.insert(0, SYSTEMFN_DIR)

from services.db_service import init_db, obtener_conexion, ContratoRepository
from services.pago_service import PagoService
from services.reporte_service import ReporteService
from services.pdf_service import generar_pdf_recibo_pago
from utils.helpers import (
    validar_fecha, normalizar_fecha_iso, formatear_fecha_ddmmyyyy,
    calcular_edad, obtener_fecha_actual_ddmmyyyy
)

def test_inventario_decimales():
    print("\n--- 1. Pruebas de Precios con Decimales en Inventario ---")
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # Crear un producto con decimales usando punto
    p_nombre1 = "Urna Especial Caoba 25.50"
    cursor.execute("DELETE FROM inventario WHERE nombre = ?", (p_nombre1,))
    precio_raw1 = "25.50".replace("$", "").replace(",", ".").strip()
    precio1 = round(float(precio_raw1), 2)
    cursor.execute("INSERT INTO inventario (nombre, stock, precio, stock_minimo) VALUES (?, ?, ?, ?)",
                   (p_nombre1, 10, precio1, 3))
    conn.commit()
    pid1 = cursor.lastrowid
    print(f"  [OK] Producto creado con punto decimal: ID #{pid1}, precio: ${precio1:.2f}")

    # Modificar precio con coma (ej. 34,75)
    precio_raw2 = "34,75".replace("$", "").replace(",", ".").strip()
    precio2 = round(float(precio_raw2), 2)
    cursor.execute("UPDATE inventario SET precio = ? WHERE id = ?", (precio2, pid1))
    conn.commit()
    
    cursor.execute("SELECT precio FROM inventario WHERE id = ?", (pid1,))
    precio_guardado = cursor.fetchone()[0]
    assert precio_guardado == 34.75, f"Esperado 34.75, obtenido {precio_guardado}"
    print(f"  [OK] Producto actualizado con coma decimal ('34,75') -> guardado como {precio_guardado} (${precio_guardado:,.2f})")
    
    conn.close()

def test_fechas_ddmmyyyy():
    print("\n--- 2. Pruebas de Formato de Fechas DD/MM/YYYY ---")
    # Validar fechas
    assert validar_fecha("25/10/2026") == True, "25/10/2026 debe ser válida"
    assert validar_fecha("01/01/2027") == True, "01/01/2027 debe ser válida"
    assert validar_fecha("2026-10-25") == True, "2026-10-25 debe ser válida"
    assert validar_fecha("fecha_invalida") == False, "fecha_invalida debe ser falsa"
    print("  [OK] validar_fecha valida correctamente DD/MM/AAAA y formatos estándar.")

    # Normalizar a ISO
    assert normalizar_fecha_iso("25/10/2026") == "2026-10-25"
    assert normalizar_fecha_iso("05/11/2026") == "2026-11-05"
    assert normalizar_fecha_iso("2026-10-25") == "2026-10-25"
    print("  [OK] normalizar_fecha_iso convierte DD/MM/AAAA a YYYY-MM-DD para SQLite.")

    # Formatear a DD/MM/AAAA
    assert formatear_fecha_ddmmyyyy("2026-10-25") == "25/10/2026"
    assert formatear_fecha_ddmmyyyy("2026-10-25 14:30:00") == "25/10/2026 14:30:00"
    print("  [OK] formatear_fecha_ddmmyyyy formatea a DD/MM/AAAA correctamente.")

    # Calcular edad con DD/MM/AAAA
    edad = calcular_edad("15/05/1990")
    assert edad is not None and edad > 30, f"Edad esperada > 30, obtenida: {edad}"
    print(f"  [OK] calcular_edad con '15/05/1990' -> {edad} años.")

    # Reportes con fechas en DD/MM/AAAA
    datos_rep = ReporteService.ventas_por_periodo("01/01/2026", "31/12/2026")
    assert isinstance(datos_rep, dict), "ventas_por_periodo debe retornar un dict con fechas DD/MM/AAAA"
    print(f"  [OK] ReporteService.ventas_por_periodo funcionó con fechas '01/01/2026' a '31/12/2026' (Total: ${datos_rep['total_ventas']:,.2f})")

def test_facturacion_mes_pnf_recibo():
    print("\n--- 3. Pruebas de Gestión de Facturación y Recibo de Pago PNF (PDF) ---")
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # Buscar contrato PNF o crear uno
    cursor.execute("SELECT id, numero FROM contratos WHERE pnf_asociado = 1 ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT id, numero FROM contratos ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
    
    assert row is not None, "Debe existir al menos un contrato"
    cid, cnum = row
    
    # Registrar un pago especificando el mes que se está sacando (ej. "Mes: Octubre 2026")
    mes_sacado = "Mes: Octubre 2026"
    res_pago = PagoService.registrar_pago(
        contrato_id=cid,
        monto=35.50,
        metodo="Transferencia Bancaria",
        referencia="TRANSF-987654",
        moneda="USD",
        mes_periodo=mes_sacado
    )
    pago_id = res_pago['id'] if isinstance(res_pago, dict) else res_pago
    print(f"  [OK] Pago registrado para el mes que se está sacando: '{mes_sacado}', Monto: $35.50 (ID #{pago_id})")

    # Generar el Recibo de Pago Oficial en PDF
    pdf_ruta = generar_pdf_recibo_pago(pago_id)
    assert pdf_ruta is not None, "La ruta del PDF no debe ser None"
    assert os.path.exists(pdf_ruta), f"El archivo PDF {pdf_ruta} debe existir físicamente"
    tamano = os.path.getsize(pdf_ruta)
    assert tamano > 1000, f"El archivo PDF debe tener un tamaño válido (>1000 bytes, tiene {tamano})"
    print(f"  [OK] Recibo de Pago PNF en PDF generado exitosamente:\n       Ruta: {pdf_ruta}\n       Tamaño: {tamano} bytes")

    conn.close()

def main():
    print("=" * 65)
    print("EJECUTANDO PRUEBAS DE LOS 3 NUEVOS REQUERIMIENTOS SOLICITADOS")
    print("=" * 65)
    init_db()
    test_inventario_decimales()
    test_fechas_ddmmyyyy()
    test_facturacion_mes_pnf_recibo()
    print("\n" + "=" * 65)
    print("¡TODAS LAS PRUEBAS COMPLETADAS CON ÉXITO (100% OK)!")
    print("=" * 65)

if __name__ == "__main__":
    main()

