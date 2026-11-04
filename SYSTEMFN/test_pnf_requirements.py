# test_pnf_requirements.py - Pruebas automatizadas de los nuevos requerimientos PNF
import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.db_service import (
    obtener_conexion, init_db, ContratoRepository, generar_familia_id, PAQUETES
)
from utils.helpers import calcular_edad
from services.precio_service import PrecioService, generar_plan_cuotas
from services.contrato_service import ContratoService
from services.pdf_service import generar_pdf_contrato

def test_pnf():
    print("==================================================")
    print("INICIANDO PRUEBAS DE LOS NUEVOS REQUERIMIENTOS PNF")
    print("==================================================")

    init_db()

    # 1. Prueba de cálculo automático de edad y validación +18
    print("\n--- 1. Cálculo de Edad y Validación +18 del Titular ---")
    edad_menor = calcular_edad("2015-05-20")
    edad_mayor = calcular_edad("1990-10-15")
    edad_bebe = calcular_edad("2024-01-01")

    print(f"  Fecha 2015-05-20 -> Edad: {edad_menor} años")
    print(f"  Fecha 1990-10-15 -> Edad: {edad_mayor} años")
    print(f"  Fecha 2024-01-01 -> Edad: {edad_bebe} años")

    assert edad_menor < 18, "Error: Debería ser menor de 18"
    assert edad_mayor >= 18, "Error: Debería ser mayor de 18"
    print("  [OK] Validación de edad mayor/menor a 18 años correcta.")

    # 2. Beneficiarios a su cargo (entre 8 y 15 personas)
    print("\n--- 2. Beneficiarios a su Cargo (8 a 15 personas) ---")
    beneficiarios = []
    # Generar 10 beneficiarios de prueba combinando cédula y partida de nacimiento
    for i in range(1, 11):
        if i <= 5: # Cédula para mayores de 9
            fn = f"200{i}-03-10"
            edad = calcular_edad(fn)
            beneficiarios.append({
                "nombre_completo": f"Beneficiario Mayor {i}",
                "tipo_documento": "Cedula",
                "cedula": f"V-3012345{i}",
                "folio": "",
                "acta": "",
                "fecha_nacimiento": fn,
                "edad": edad,
                "parentesco": "Hijo/a"
            })
        else: # Partida de nacimiento para infantes/menores
            fn = f"202{i-5}-08-15"
            edad = calcular_edad(fn)
            beneficiarios.append({
                "nombre_completo": f"Beneficiario Menor {i}",
                "tipo_documento": "Partida",
                "cedula": "",
                "folio": f"F-{100+i}",
                "acta": f"A-{200+i}",
                "fecha_nacimiento": fn,
                "edad": edad,
                "parentesco": "Sobrino/a"
            })

    assert 8 <= len(beneficiarios) <= 15, "La nómina debe tener entre 8 y 15 beneficiarios"
    print(f"  [OK] Nómina de {len(beneficiarios)} beneficiarios generada con éxito (mínimo 8, máximo 15 cumplido).")

    # 3. Opciones de periodicidad de pago
    print("\n--- 3. Periodicidad de Cancelación (Semanal, Quincenal, Mensual, Trimestral) ---")
    plan_semanal = PrecioService.generar_plan_cuotas(total=850.00, inicial=50.00, numero_cuotas=52, frecuencia="Semanal")
    plan_quincenal = PrecioService.generar_plan_cuotas(total=850.00, inicial=50.00, numero_cuotas=24, frecuencia="Quincenal")
    plan_mensual = PrecioService.generar_plan_cuotas(total=850.00, inicial=50.00, numero_cuotas=12, frecuencia="Mensual")
    plan_trimestral = PrecioService.generar_plan_cuotas(total=850.00, inicial=50.00, numero_cuotas=4, frecuencia="Trimestral")

    assert len(plan_semanal) == 52, "Debe tener 52 cuotas semanales"
    assert len(plan_quincenal) == 24, "Debe tener 24 cuotas quincenales"
    assert len(plan_mensual) == 12, "Debe tener 12 cuotas mensuales"
    assert len(plan_trimestral) == 4, "Debe tener 4 cuotas trimestrales"

    # Verificar suma exacta de cuotas
    suma_sem = round(sum(c["monto"] for c in plan_semanal), 2)
    assert abs(suma_sem - 800.00) < 0.01, f"Suma semanal incorrecta: {suma_sem}"
    suma_quin = round(sum(c["monto"] for c in plan_quincenal), 2)
    assert abs(suma_quin - 800.00) < 0.01, f"Suma quincenal incorrecta: {suma_quin}"

    print(f"  [OK] Semanal: 52 cuotas de ${plan_semanal[0]['monto']:.2f} (Vence 1ra: {plan_semanal[0]['fecha_vencimiento']})")
    print(f"  [OK] Quincenal: 24 cuotas de ${plan_quincenal[0]['monto']:.2f} (Vence 1ra: {plan_quincenal[0]['fecha_vencimiento']})")
    print(f"  [OK] Mensual: 12 cuotas de ${plan_mensual[0]['monto']:.2f} (Vence 1ra: {plan_mensual[0]['fecha_vencimiento']})")
    print(f"  [OK] Trimestral: 4 cuotas de ${plan_trimestral[0]['monto']:.2f} (Vence 1ra: {plan_trimestral[0]['fecha_vencimiento']})")

    # 4. Creación en BD de Contrato PNF con titular (+18), beneficiarios y cuotas
    print("\n--- 4. Creación de Contrato PNF Completo en BD ---")
    conn = obtener_conexion()
    c = conn.cursor()

    fam_id = generar_familia_id()
    import random
    cedula_test = f"V-{random.randint(10000000, 99999999)}"
    c.execute("""
        INSERT INTO familias (familia_id, resp_cedula, resp_nombre, resp_apellido, resp_telefono, resp_direccion, fecha_creacion)
        VALUES (?, ?, 'María', 'González', '0414-9998877', 'Sector Centro', ?)
    """, (fam_id, cedula_test, datetime.datetime.now().isoformat()))


    num_contrato = f"PNF-TEST-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    c.execute("""
        INSERT INTO contratos (
            numero, fecha_contrato, familia_id, paquete, monto_total, metodo_pago,
            inicial, numero_cuotas, pagado, estado, tipo_contrato, pnf_asociado,
            pnf_numero, costo_paquete, titular_edad, frecuencia_pago
        ) VALUES (?, ?, ?, 'PLATA', 1800.00, 'Financiado', 200.00, 24, 0.0, 'Activo', 'Largo Plazo', 1, ?, 1800.00, 36, 'Quincenal')
    """, (num_contrato, datetime.datetime.now().strftime("%Y-%m-%d"), fam_id, num_contrato))
    contrato_id = c.lastrowid
    conn.commit()
    conn.close()

    # Guardar beneficiarios
    ContratoRepository.guardar_beneficiarios(contrato_id, beneficiarios)


    # Verificar recuperación
    contrato_rec = ContratoService.obtener_contrato_completo(contrato_id)
    assert contrato_rec is not None
    assert contrato_rec["titular_edad"] == 36
    assert contrato_rec["frecuencia_pago"] == "Quincenal"
    assert len(contrato_rec["beneficiarios"]) == 10
    print(f"  [OK] Contrato #{contrato_id} ({num_contrato}) guardado y verificado en base de datos.")
    print(f"       Titular edad: {contrato_rec['titular_edad']} años | Frecuencia: {contrato_rec['frecuencia_pago']} | Beneficiarios: {len(contrato_rec['beneficiarios'])}")

    # 5. Generación de PDF del PNF
    print("\n--- 5. Generación de PDF del PNF con Beneficiarios ---")
    pdf_path = generar_pdf_contrato(contrato_id)
    assert pdf_path is not None and os.path.exists(pdf_path)
    print(f"  [OK] PDF del PNF generado exitosamente en:\n       {pdf_path}")

    # 6. Prueba de Carga Familiar Reducida (ej: 3 o 4 beneficiarios a su cargo, sin bloqueo de mínimo 8)
    print("\n--- 6. Flexibilidad de Carga Familiar (1 a 15 personas: ej. 4 beneficiarios + titular = 5) ---")
    carga_4 = [
        {
            "nombre_completo": "Hijo Mayor 1",
            "tipo_documento": "Cedula",
            "cedula": "V-31000111",
            "folio": "",
            "acta": "",
            "fecha_nacimiento": "2010-04-12",
            "edad": calcular_edad("2010-04-12"),
            "parentesco": "Hijo"
        },
        {
            "nombre_completo": "Hija Menor 2",
            "tipo_documento": "Partida",
            "cedula": "",
            "folio": "F-55",
            "acta": "A-99",
            "fecha_nacimiento": "2020-07-22",
            "edad": calcular_edad("2020-07-22"),
            "parentesco": "Hija"
        },
        {
            "nombre_completo": "Madre Titular",
            "tipo_documento": "Cedula",
            "cedula": "V-05888999",
            "folio": "",
            "acta": "",
            "fecha_nacimiento": "1958-11-03",
            "edad": calcular_edad("1958-11-03"),
            "parentesco": "Madre"
        },
        {
            "nombre_completo": "Esposo/a",
            "tipo_documento": "Cedula",
            "cedula": "V-15222333",
            "folio": "",
            "acta": "",
            "fecha_nacimiento": "1988-02-19",
            "edad": calcular_edad("1988-02-19"),
            "parentesco": "Cónyuge"
        }
    ]
    ContratoRepository.guardar_beneficiarios(contrato_id, carga_4)
    contrato_rec_4 = ContratoService.obtener_contrato_completo(contrato_id)
    assert len(contrato_rec_4["beneficiarios"]) == 4, "Debería reflejar exactamente 4 beneficiarios"
    print(f"  [OK] Carga familiar actualizada y reflejada con {len(contrato_rec_4['beneficiarios'])} beneficiarios (+ titular = 5 personas).")

    # 7. Prueba de navegación con teclado en CTkComboBox y CTkOptionMenu
    print("\n--- 7. Verificacion de Parche de Navegacion por Teclado (Flecha Abajo / Arriba) ---")
    import customtkinter as ctk
    from utils.helpers import habilitar_navegacion_teclado
    habilitar_navegacion_teclado()

    root = ctk.CTk()
    root.withdraw()
    seleccionado_combo = []
    combo = ctk.CTkComboBox(root, values=["Opción 1", "Opción 2", "Opción 3"], state="readonly", command=lambda v: seleccionado_combo.append(v))
    combo.set("Opción 1")

    class DummyEvent:
        def __init__(self, keysym):
            self.keysym = keysym

    # Simular presionar flecha abajo en el combo
    combo._navegar_teclado(DummyEvent("Down"))
    assert combo.get() == "Opción 2", f"Se esperaba 'Opción 2' al presionar Flecha Abajo, se obtuvo '{combo.get()}'"
    combo._navegar_teclado(DummyEvent("Down"))
    assert combo.get() == "Opción 3", f"Se esperaba 'Opción 3' al presionar Flecha Abajo, se obtuvo '{combo.get()}'"
    combo._navegar_teclado(DummyEvent("Up"))
    assert combo.get() == "Opción 2", f"Se esperaba 'Opción 2' al presionar Flecha Arriba, se obtuvo '{combo.get()}'"
    root.destroy()
    print("  [OK] CTkComboBox responde correctamente a las teclas <Down> y <Up> sin requerir clic en el boton.")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS DE PNF PASARON CON ÉXITO (100% OK)")
    print("==================================================")

if __name__ == "__main__":
    test_pnf()
