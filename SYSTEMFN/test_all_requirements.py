# test_all_requirements.py - Suite de verificación automatizada de los 7 cambios
import sys
import os
import datetime

# Asegurar path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.db_service import (
    obtener_conexion, init_db, CapillaRepository, FamiliaRepository,
    ContratoRepository, normalizar_cedula
)
from services.precio_service import (
    PrecioService, calcular_desglose, verificar_contrato, r2,
    COSTO_CREMACION, COSTOS_TRASLADO
)
from services.contrato_service import ContratoService
from services.cliente_service import ClienteService
from services.pdf_service import generar_pdf_contrato

def run_tests():
    print("==================================================")
    print("INICIANDO PRUEBAS DE INTEGRACIÓN DEL SISTEMA")
    print("==================================================")

    init_db()

    # ----------------------------------------------------
    # REQ 1: VERIFICAR TOTAL Y COSTO
    # ----------------------------------------------------
    print("\n--- REQ 1: Verificar Total y Costo ---")
    desglose = PrecioService.calcular_desglose(
        paquete="ORO",
        requiere_cremacion=True,
        tipo_traslado="Regional",
        productos=[{"cantidad": 2, "precio": 50.00}],
        servicios=[{"cantidad": 1, "precio": 120.00}],
        pnf_asociado=False
    )
    # ORO: 3800 + Cremación: 250 + Regional: 300 + Prods: 100 + Servs: 120 = 4570
    assert desglose["costo_paquete"] == 3800.00, f"Error costo paquete: {desglose['costo_paquete']}"
    assert desglose["costo_cremacion"] == 250.00
    assert desglose["costo_traslado"] == 300.00
    assert desglose["costo_productos"] == 100.00
    assert desglose["costo_servicios"] == 120.00
    assert desglose["total"] == 4570.00, f"Total esperado 4570.00, obtenido {desglose['total']}"
    print(f"  [OK] Desglose matematico exacto: Total = ${desglose['total']:.2f}")

    # Verificar cuotas exactas
    cuotas = PrecioService.calcular_cuotas_exactas(100.00, 3)
    assert sum(cuotas) == 100.00, f"Cuotas deben sumar 100.00, suman {sum(cuotas)}"
    print(f"  [OK] Distribucion exacta de cuotas: {cuotas} (suma: ${sum(cuotas):.2f})")

    # ----------------------------------------------------
    # REQ 2: OPCIÓN DE MODIFICAR CAPILLAS
    # ----------------------------------------------------
    print("\n--- REQ 2: Opcion de Modificar Capillas ---")
    cap_id = CapillaRepository.crear("Capilla Test Verificacion", 40, "Capilla para pruebas", "Disponible")
    assert cap_id is not None, "Error al crear capilla"
    print(f"  [OK] Capilla creada con ID: #{cap_id}")

    ok, msg = CapillaRepository.actualizar(cap_id, "Capilla Test Modificada", 55, "Descripcion editada", "Mantenimiento")
    assert ok, f"Error al actualizar capilla: {msg}"
    c_info = CapillaRepository.obtener_por_id(cap_id)
    assert c_info['nombre'] == "Capilla Test Modificada"
    assert c_info['capacidad'] == 55
    assert c_info['estado'] == "Mantenimiento"
    print(f"  [OK] Capilla #{cap_id} modificada exitosamente (Capacidad: 55, Estado: Mantenimiento)")

    ok, msg = CapillaRepository.cambiar_estado(cap_id, "Disponible")
    assert ok
    c_info = CapillaRepository.obtener_por_id(cap_id)
    assert c_info['estado'] == "Disponible"
    print(f"  [OK] Cambio rapido de estado a Disponible exitoso.")

    # ----------------------------------------------------
    # REQ 3: FUENTE MODIFICAR - COLOR
    # ----------------------------------------------------
    print("\n--- REQ 3: Fuente Modificar - Color ---")
    from utils.helpers import FONT_FAMILY, COLOR_GOLD, COLOR_BG_DARK, obtener_fuente
    assert FONT_FAMILY == "Segoe UI"
    assert COLOR_GOLD.upper() == "#D4AF37"
    f = obtener_fuente(14, "bold")
    assert f == ("Segoe UI", 14, "bold")
    print(f"  [OK] Estandar visual y tipografia verificada: {FONT_FAMILY}, Acento: {COLOR_GOLD}")

    # ----------------------------------------------------
    # REQ 4: ASOCIAR PNF AL SISTEMA
    # ----------------------------------------------------
    print("\n--- REQ 4: Asociar PNF al Sistema ---")
    # PNF cubriendo cremacion y traslado nacional
    desglose_pnf = PrecioService.calcular_desglose(
        paquete="PLATA",
        requiere_cremacion=True,
        tipo_traslado="Nacional",
        productos=[],
        servicios=[],
        pnf_asociado=True,
        pnf_cubre_traslado=True,
        pnf_cubre_cremacion=True
    )
    # PLATA: 1800 + Cremacion: 250 + Nacional: 800 = 2850
    # Descuento PNF: 250 + 800 = 1050
    # Total con PNF: 1800
    assert desglose_pnf["subtotal"] == 2850.00
    assert desglose_pnf["descuento_pnf"] == 1050.00
    assert desglose_pnf["total"] == 1800.00
    print(f"  [OK] PNF aplica descuento 100% a cremacion y traslado: Descuento PNF = -${desglose_pnf['descuento_pnf']:.2f}, Total Final = ${desglose_pnf['total']:.2f}")

    # ----------------------------------------------------
    # REQ 5: CONTRATOS INMEDIATOS vs LARGO PLAZO
    # ----------------------------------------------------
    print("\n--- REQ 5: Contratos Inmediatos vs Largo Plazo ---")
    # Obtener una familia existente o crear una
    familias = ClienteService.listar_todas_familias()
    if not familias:
        fid = ClienteService.registrar_familia({
            'cedula': 'V-99887766', 'nombre': 'Carlos', 'apellido': 'Previsor',
            'telefono': '0414-0000000', 'email': 'carlos@test.com', 'direccion': 'Calabozo'
        })
    else:
        fid = familias[0]['familia_id']

    conn = obtener_conexion()
    cur = conn.cursor()

    num_lp = ContratoService.generar_numero_contrato()
    cur.execute("""
        INSERT INTO contratos (
            numero, fecha_contrato, familia_id, difunto_id, paquete,
            capilla_id, fecha_velacion, hora_inicio, hora_fin,
            monto_total, metodo_pago, inicial, numero_cuotas, pagado, estado,
            tipo_contrato, pnf_asociado, pnf_numero, pnf_cubre_traslado, pnf_cubre_cremacion,
            descuento_pnf, costo_paquete, costo_cremacion, costo_traslado, costo_productos, costo_servicios
        ) VALUES (?, ?, ?, NULL, 'PLATA', NULL, 'Plan a Futuro', '10:00', '22:00', 1800.00, 'Contado', 0, 1, 0, 'Activo',
                  'Largo Plazo', 1, 'PNF-99881', 1, 0, 0, 1800.00, 0, 0, 0, 0)
    """, (num_lp, datetime.datetime.now().strftime("%Y-%m-%d"), fid))
    lp_id = cur.lastrowid
    conn.commit()
    conn.close()

    print(f"  [OK] Contrato a Largo Plazo #{lp_id} ({num_lp}) creado sin difunto ni capilla inicial.")

    # Verificar que aparece en la consulta LEFT JOIN sin romperse
    conn = obtener_conexion()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.numero, c.tipo_contrato, d.nombre, cap.nombre
        FROM contratos c
        LEFT JOIN difuntos d ON c.difunto_id = d.id
        LEFT JOIN capillas cap ON c.capilla_id = cap.id
        WHERE c.id = ?
    """, (lp_id,))
    row = cur.fetchone()
    conn.close()
    assert row[2] == "Largo Plazo"
    assert row[3] is None  # difunto es NULL
    assert row[4] is None  # capilla es NULL
    print(f"  [OK] Consulta LEFT JOIN recupera contrato a Largo Plazo con difunto y capilla NULL.")

    # ----------------------------------------------------
    # REQ 6: HORA DE LLEGADA DEL DIFUNTO A LA FUNERARIA
    # ----------------------------------------------------
    print("\n--- REQ 6: Hora de Llegada del Difunto para Gestion de Contratos ---")
    ok, msg = ContratoService.actualizar_horarios_llegada(
        contrato_id=lp_id,
        hora_llegada="13:45",
        hora_salida="17:30",
        estado_servicio="En Velación"
    )
    assert ok, f"Error al actualizar horarios: {msg}"

    conn = obtener_conexion()
    cur = conn.cursor()
    cur.execute("SELECT hora_llegada_real, hora_salida_capilla, estado_servicio FROM contratos WHERE id = ?", (lp_id,))
    h_row = cur.fetchone()
    conn.close()
    assert h_row[0] == "13:45"
    assert h_row[1] == "17:30"
    assert h_row[2] == "En Velación"
    print(f"  [OK] Horarios actualizados en DB: Llegada Real={h_row[0]}, Salida={h_row[1]}, Estado={h_row[2]}")

    # Reasignar capilla a este contrato
    ok, msg = ContratoService.reasignar_capilla(lp_id, cap_id)
    assert ok, f"Error al reasignar capilla: {msg}"
    conn = obtener_conexion()
    cur = conn.cursor()
    cur.execute("SELECT capilla_id FROM contratos WHERE id = ?", (lp_id,))
    assert cur.fetchone()[0] == cap_id
    conn.close()
    print(f"  [OK] Capilla #{cap_id} reasignada exitosamente al contrato #{lp_id}.")

    # ----------------------------------------------------
    # REQ 7: FAMILIAR RESPONSABLE AUTO-DETECCIÓN POR CÉDULA
    # ----------------------------------------------------
    print("\n--- REQ 7: Familiar Responsable Auto-deteccion por Cedula ---")
    if not ClienteService.buscar_familia_por_cedula("V-99887766"):
        ClienteService.registrar_familia({
            'cedula': 'V-99887766', 'nombre': 'Carlos', 'apellido': 'Previsor',
            'telefono': '0414-0000000', 'email': 'carlos@test.com', 'direccion': 'Calabozo'
        })

    # Busqueda con cedula formateada y normalizada
    resp_encontrado = ClienteService.buscar_familia_por_cedula("V-99887766")
    assert resp_encontrado is not None, "No se encontro el responsable por cedula"
    assert resp_encontrado['resp_nombre'] == "Carlos"
    assert resp_encontrado['resp_apellido'] == "Previsor"
    print(f"  [OK] Familiar responsable auto-detectado por cedula: {resp_encontrado['resp_nombre']} {resp_encontrado['resp_apellido']} (Familia ID: {resp_encontrado['familia_id']})")

    # Búsqueda con cédula sin formato
    resp_norm = ClienteService.buscar_familia_por_cedula("99887766")
    assert resp_norm is not None
    assert resp_norm['familia_id'] == resp_encontrado['familia_id']
    print(f"  [OK] Busqueda tolerante a formato (99887766 vs V-99887766) funciona perfectamente.")

    # ----------------------------------------------------
    # VERIFICACIÓN DEL GENERADOR DE PDF
    # ----------------------------------------------------
    print("\n--- Verificacion de Generacion de PDF ---")
    pdf_path = generar_pdf_contrato(lp_id)
    assert pdf_path and os.path.exists(pdf_path), f"El archivo PDF no se genero: {pdf_path}"
    print(f"  [OK] PDF generado con exito: {pdf_path}")

    # Limpiar capilla de prueba
    CapillaRepository.eliminar(cap_id)

    print("\n==================================================")
    print("TODAS LAS 7 PRUEBAS DE REQUERIMIENTOS PASARON EXITOSAMENTE (100% OK)")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
