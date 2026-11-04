# services/pdf_service.py - Generación de contratos PDF profesionales
import os
import datetime
from typing import Optional

from services.db_service import obtener_conexion, CONTRATOS_DIR, EMPRESA, PAQUETES
from services.contrato_service import ContratoService
from services.precio_service import lineas_desglose, r2


def generar_pdf_contrato(contrato_id: int) -> Optional[str]:
    """Genera un contrato profesional en PDF con soporte para Inmediato, Largo Plazo, PNF y desglose de costos"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib import colors as rc
    from reportlab.lib.units import inch

    contrato = ContratoService.obtener_contrato_completo(contrato_id)
    if not contrato:
        return None

    conn = obtener_conexion()
    cursor = conn.cursor()

    # Productos adicionales
    cursor.execute("""
        SELECT i.nombre, cp.cantidad, cp.precio_unitario
        FROM contrato_productos cp
        JOIN inventario i ON cp.producto_id = i.id
        WHERE cp.contrato_id = ?
    """, (contrato_id,))
    productos = cursor.fetchall()

    # Servicios adicionales
    cursor.execute("""
        SELECT servicio_nombre, cantidad, precio_unitario, subtotal
        FROM contratos_servicios
        WHERE contrato_id = ?
    """, (contrato_id,))
    servicios_adicionales = cursor.fetchall()

    # Cuotas
    cuotas = []
    if contrato['metodo_pago'] == "Financiado":
        cursor.execute("""
            SELECT numero, monto, fecha_vencimiento, estado
            FROM cuotas WHERE contrato_id = ? ORDER BY numero
        """, (contrato_id,))
        cuotas = cursor.fetchall()

    conn.close()

    os.makedirs(CONTRATOS_DIR, exist_ok=True)
    filename = os.path.join(CONTRATOS_DIR, f"Contrato_{contrato['numero']}.pdf")

    # Colores corporativos
    DORADO = rc.HexColor("#B8860B")
    DORADO_CLARO = rc.HexColor("#F5E6C0")
    GRIS_OSC = rc.HexColor("#2C2C2C")
    GRIS_MEDIO = rc.HexColor("#666666")
    GRIS_CLARO = rc.HexColor("#F4F4F4")

    doc = SimpleDocTemplate(
        filename, pagesize=letter,
        leftMargin=0.8 * inch, rightMargin=0.8 * inch,
        topMargin=0.6 * inch, bottomMargin=0.85 * inch
    )
    W = letter[0] - 1.6 * inch

    def estilo(nombre, **kw):
        base = dict(fontName="Helvetica", fontSize=9, leading=13,
                    textColor=GRIS_OSC, spaceAfter=0, spaceBefore=0)
        base.update(kw)
        return ParagraphStyle(nombre, **base)

    s_emp = estilo("emp", fontSize=15, fontName="Helvetica-Bold", textColor=rc.white, alignment=TA_CENTER)
    s_sub = estilo("sub", fontSize=8, textColor=DORADO_CLARO, alignment=TA_CENTER)
    s_tit = estilo("tit", fontSize=13, fontName="Helvetica-Bold", textColor=DORADO, alignment=TA_CENTER, spaceBefore=10, spaceAfter=4)
    s_fecha = estilo("fec", fontSize=9, textColor=GRIS_MEDIO, alignment=TA_CENTER, spaceAfter=6)
    s_sec = estilo("sec", fontSize=10, fontName="Helvetica-Bold", textColor=rc.white)
    s_n = estilo("nor", fontSize=9, leading=14)
    s_nb = estilo("nb", fontSize=9, fontName="Helvetica-Bold", leading=14)
    s_leg = estilo("leg", fontSize=7.5, textColor=GRIS_MEDIO, leading=11)
    s_fa = estilo("fa", fontSize=8, textColor=GRIS_MEDIO, alignment=TA_CENTER)
    s_fn = estilo("fn", fontSize=7.5, textColor=GRIS_MEDIO, alignment=TA_CENTER)
    s_cen = estilo("cen", fontSize=9, alignment=TA_CENTER)

    story = []

    # Cabecera corporativa
    hdr = Table([[Paragraph(EMPRESA["nombre"], s_emp)]], colWidths=[W])
    hdr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_OSC),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
    ]))
    story.append(hdr)

    sub_t = Table([[
        Paragraph(f"RIF: {EMPRESA['rif']}", s_sub),
        Paragraph(EMPRESA["direccion"], s_sub),
        Paragraph(f"Tel: {EMPRESA['telefono']} | {EMPRESA['correo']}", s_sub)
    ]], colWidths=[W / 3] * 3)
    sub_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DORADO),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
    ]))
    story.append(sub_t)
    story.append(Spacer(1, 10))

    tipo_txt = f"[{contrato['tipo_contrato'].upper()}]"
    story.append(Paragraph(f"CONTRATO DE SERVICIO FUNERARIO {tipo_txt}", s_tit))
    from utils.helpers import formatear_fecha_ddmmyyyy
    story.append(Paragraph(
        f"N° {contrato['numero']}  ·  Fecha: {formatear_fecha_ddmmyyyy(contrato['fecha_contrato'])}  ·  Estado: {contrato['estado']}",
        s_fecha
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DORADO, spaceAfter=10))

    def sec(txt):
        t = Table([[Paragraph(txt, s_sec)]], colWidths=[W])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GRIS_OSC),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8)
        ]))
        return t

    def fila(lbl, val):
        return [Paragraph(f"<b>{lbl}</b>", s_nb), Paragraph(str(val) if val else "—", s_n)]

    # 1. Datos del fallecido / afiliado
    if contrato['tipo_contrato'] == "Largo Plazo" and not contrato['difunto_id']:
        filas_dif = [
            fila("Modalidad:", "Plan a Largo Plazo / Previsión Funeraria"),
            fila("Beneficiario:", "Por designar al momento de la activación del plan"),
            fila("Titular del Plan:", contrato['responsable'])
        ]
    else:
        filas_dif = [
            fila("Nombre completo:", contrato['difunto']),
            fila("Cédula de identidad:", contrato['difunto_cedula']),
            fila("Fecha de defunción:", contrato['difunto_defuncion'] or "No especificada")
        ]

    story += [
        sec("1. DATOS DEL FALLECIDO / AFILIADO"),
        Spacer(1, 4),
        Table(filas_dif, colWidths=[2.1 * inch, W - 2.1 * inch]),
        Spacer(1, 8)
    ]

    # 2. Familiar Responsable
    filas_resp = [
        fila("Nombre completo:", contrato['responsable']),
        fila("Cédula de identidad:", contrato['responsable_cedula']),
    ]
    if contrato.get('titular_edad'):
        filas_resp.append(fila("Edad del titular:", f"{contrato['titular_edad']} años (Mayor de edad)"))
    filas_resp.extend([
        fila("Teléfono:", contrato['responsable_telefono'] or "—"),
        fila("Correo electrónico:", contrato['responsable_email'] or "—"),
        fila("Dirección:", contrato['responsable_direccion'] or "—")
    ])

    story += [
        sec("2. FAMILIAR RESPONSABLE / TITULAR"),
        Spacer(1, 4),
        Table(filas_resp, colWidths=[2.1 * inch, W - 2.1 * inch]),
        Spacer(1, 8)
    ]

    num_sec = 3

    # Beneficiarios del Plan PNF (si existen)
    if contrato.get('beneficiarios'):
        enc_b = [Paragraph(f"<b>{h}</b>", estilo(f"hb{i}", fontName="Helvetica-Bold", alignment=TA_CENTER))
                 for i, h in enumerate(["N°", "Nombre del Beneficiario", "Tipo Doc.", "Cédula / Folio - Acta", "Fecha Nac.", "Edad"])]
        filas_b = [enc_b]
        for idx, b in enumerate(contrato['beneficiarios'], 1):
            if b.get('tipo_documento') == "Cedula":
                doc_ident = f"C.I. {b.get('cedula', '')}"
            else:
                doc_ident = f"Folio: {b.get('folio', '')} | Acta: {b.get('acta', '')}"
            filas_b.append([
                Paragraph(str(idx), s_cen),
                Paragraph(b.get('nombre_completo', ''), s_n),
                Paragraph(b.get('tipo_documento', ''), s_cen),
                Paragraph(doc_ident, s_n),
                Paragraph(formatear_fecha_ddmmyyyy(str(b.get('fecha_nacimiento', ''))), s_cen),
                Paragraph(f"{b.get('edad', 0)} años", s_cen)
            ])
        tb = Table(filas_b, colWidths=[W * 0.06, W * 0.32, W * 0.14, W * 0.28, W * 0.12, W * 0.08])
        tb.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DORADO),
            ("TEXTCOLOR", (0, 0), (-1, 0), rc.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rc.white, GRIS_CLARO]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.3, rc.HexColor("#CCCCCC"))
        ]))
        story += [
            sec(f"{num_sec}. NÓMINA DE BENEFICIARIOS A SU CARGO (PNF - {len(contrato['beneficiarios'])} PERSONAS)"),
            Spacer(1, 4),
            tb,
            Spacer(1, 8)
        ]
        num_sec += 1


    # Cobertura PNF (si aplica)
    if contrato['pnf_asociado']:
        filas_pnf = [
            fila("Afiliación PNF:", "Sí (Plan Nacional Funerario asociado)"),
            fila("N° de Contrato / Póliza PNF:", contrato['pnf_numero'] or "No registrado"),
            fila("Cubre Cremación:", "Sí (sin costo adicional)" if contrato['pnf_cubre_cremacion'] else "No cubierta"),
            fila("Cubre Traslado:", f"Sí (cobertura {contrato['tipo_traslado']})" if contrato['pnf_cubre_traslado'] else "No cubierto"),
            fila("Descuento total PNF:", f"${contrato['descuento_pnf']:,.2f}")
        ]
        story += [
            sec(f"{num_sec}. AFILIACIÓN A PLAN NACIONAL FUNERARIO (PNF)"),
            Spacer(1, 4),
            Table(filas_pnf, colWidths=[2.1 * inch, W - 2.1 * inch]),
            Spacer(1, 8)
        ]
        num_sec += 1

    # 4. Detalle del servicio
    pq = PAQUETES.get(contrato['paquete'], {"precio": 0, "descripcion": "", "incluye": []})
    incluye = "  ✔  ".join(pq.get("incluye", ["Servicio básico incluido"]))

    filas_serv = [
        fila("Tipo de contrato:", contrato['tipo_contrato']),
        fila("Paquete:", f"{contrato['paquete']}  —  ${pq.get('precio', 0):,.2f}"),
        fila("Descripción:", pq.get("descripcion", "")),
        fila("Incluye:", incluye),
        fila("Tipo de velación:", contrato['tipo_velacion']),
        fila("Capilla asignada:", contrato['capilla']),
        fila("Cremación:", "Sí" if contrato['requiere_cremacion'] else "No"),
        fila("Tipo de traslado:", contrato['tipo_traslado'])
    ]

    if contrato['tipo_contrato'] == "Inmediato" or contrato['fecha_velacion']:
        filas_serv.append(fila("Fecha de velación:", formatear_fecha_ddmmyyyy(contrato['fecha_velacion'])))
        filas_serv.append(fila("Horario planificado:", f"{contrato['hora_inicio']} a {contrato['hora_fin']}"))
    else:
        filas_serv.append(fila("Fecha y horario:", "Se asignarán al momento de activar el plan"))

    story += [
        sec(f"{num_sec}. DETALLE DEL SERVICIO CONTRATADO"),
        Spacer(1, 4),
        Table(filas_serv, colWidths=[2.1 * inch, W - 2.1 * inch]),
        Spacer(1, 8)
    ]
    num_sec += 1

    # 5. Horarios reales (si existen)
    if contrato['hora_llegada_real'] or contrato['hora_salida_capilla']:
        llegada_txt = contrato['hora_llegada_real']
        if contrato['fecha_llegada_real']:
            llegada_txt = f"{contrato['fecha_llegada_real']} {llegada_txt}"
        story += [
            sec(f"{num_sec}. HORARIOS REALES DEL SERVICIO"),
            Spacer(1, 4),
            Table([
                fila("Hora real de llegada del cuerpo:", llegada_txt or "No registrada"),
                fila("Hora de salida de capilla:", contrato['hora_salida_capilla'] or "No registrada")
            ], colWidths=[2.1 * inch, W - 2.1 * inch]),
            Spacer(1, 8)
        ]
        num_sec += 1

    # 6. Productos adicionales
    if productos:
        enc = [Paragraph(f"<b>{h}</b>", estilo(f"h{i}", fontName="Helvetica-Bold", alignment=TA_CENTER))
               for i, h in enumerate(["Producto", "Cant.", "Precio Unit.", "Subtotal"])]
        filas_p = [enc]
        for p in productos:
            sub = p[1] * p[2]
            filas_p.append([
                Paragraph(p[0], s_n), Paragraph(str(p[1]), s_cen),
                Paragraph(f"${p[2]:,.2f}", s_cen), Paragraph(f"${sub:,.2f}", s_cen)
            ])
        tp = Table(filas_p, colWidths=[W * 0.5, W * 0.1, W * 0.2, W * 0.2])
        tp.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DORADO),
            ("TEXTCOLOR", (0, 0), (-1, 0), rc.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rc.white, GRIS_CLARO]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.3, rc.HexColor("#CCCCCC"))
        ]))
        story += [sec(f"{num_sec}. PRODUCTOS ADICIONALES"), Spacer(1, 4), tp, Spacer(1, 8)]
        num_sec += 1

    # 7. Servicios adicionales
    if servicios_adicionales:
        enc = [Paragraph(f"<b>{h}</b>", estilo(f"hs{i}", fontName="Helvetica-Bold", alignment=TA_CENTER))
               for i, h in enumerate(["Servicio", "Cant.", "Precio Unit.", "Subtotal"])]
        filas_s = [enc]
        for s in servicios_adicionales:
            filas_s.append([
                Paragraph(s[0], s_n), Paragraph(str(s[1]), s_cen),
                Paragraph(f"${s[2]:,.2f}", s_cen), Paragraph(f"${s[3]:,.2f}", s_cen)
            ])
        ts = Table(filas_s, colWidths=[W * 0.5, W * 0.1, W * 0.2, W * 0.2])
        ts.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DORADO),
            ("TEXTCOLOR", (0, 0), (-1, 0), rc.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rc.white, GRIS_CLARO]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.3, rc.HexColor("#CCCCCC"))
        ]))
        story += [sec(f"{num_sec}. SERVICIOS ADICIONALES"), Spacer(1, 4), ts, Spacer(1, 8)]
        num_sec += 1

    # 8. Desglose detallado de costos y resumen financiero
    desglose_items = []
    if contrato.get('costo_paquete') is not None:
        d_dict = {
            "costo_paquete": contrato['costo_paquete'],
            "costo_cremacion": contrato['costo_cremacion'],
            "costo_traslado": contrato['costo_traslado'],
            "costo_productos": contrato['costo_productos'],
            "costo_servicios": contrato['costo_servicios'],
            "descuento_pnf": contrato['descuento_pnf']
        }
        desglose_items = lineas_desglose(d_dict, contrato['paquete'], contrato['tipo_traslado'])

    filas_fin = []
    for concepto, monto in desglose_items:
        prefix = "- " if monto < 0 else ""
        filas_fin.append(fila(f"{concepto}:", f"{prefix}${abs(monto):,.2f}"))

    filas_fin.append(fila("TOTAL DEL CONTRATO:", f"${contrato['monto_total']:,.2f}"))
    filas_fin.append(fila("Modalidad de pago:", contrato['metodo_pago']))

    saldo = r2(contrato['monto_total'] - contrato['pagado'])
    if contrato['metodo_pago'] == "Financiado":
        filas_fin.append(fila("Frecuencia de pago:", contrato.get('frecuencia_pago', 'Mensual')))
        filas_fin.append(fila("Inicial pactada:", f"${contrato['inicial']:,.2f}"))
        filas_fin.append(fila("Número de cuotas:", str(len(cuotas) if cuotas else contrato['numero_cuotas'])))


    filas_fin.append(fila("Total pagado a la fecha:", f"${contrato['pagado']:,.2f}"))
    filas_fin.append(fila("Saldo pendiente:", f"${saldo:,.2f}"))

    tf = Table(filas_fin, colWidths=[2.4 * inch, W - 2.4 * inch])
    tf.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [rc.white, GRIS_CLARO]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (0, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.3, rc.HexColor("#DDDDDD")),
        ("BACKGROUND", (0, -1), (-1, -1), DORADO_CLARO),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")
    ]))
    story += [sec(f"{num_sec}. DESGLOSE Y RESUMEN FINANCIERO"), Spacer(1, 4), tf, Spacer(1, 8)]
    num_sec += 1

    # 9. Plan de pagos
    if cuotas and contrato['metodo_pago'] == "Financiado":
        enc2 = [Paragraph(f"<b>{h}</b>", estilo(f"cc{i}", fontName="Helvetica-Bold", alignment=TA_CENTER))
                for i, h in enumerate(["N° Cuota", "Monto", "Vencimiento", "Estado"])]
        fc = [enc2]
        for cu in cuotas:
            color_est = "#27AE60" if cu[3] == "Pagada" else "#E74C3C"
            fc.append([
                Paragraph(str(cu[0]), s_cen),
                Paragraph(f"${cu[1]:,.2f}", s_cen),
                Paragraph(formatear_fecha_ddmmyyyy(cu[2]), s_cen),
                Paragraph(f'<font color="{color_est}"><b>{cu[3]}</b></font>', s_cen)
            ])
        tc = Table(fc, colWidths=[W * 0.15, W * 0.2, W * 0.35, W * 0.3])
        tc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DORADO),
            ("TEXTCOLOR", (0, 0), (-1, 0), rc.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rc.white, GRIS_CLARO]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.3, rc.HexColor("#CCCCCC"))
        ]))
        story += [sec(f"{num_sec}. PLAN DE PAGOS"), Spacer(1, 4), tc, Spacer(1, 8)]
        num_sec += 1

    # Observaciones
    if contrato['observaciones'] and contrato['observaciones'].strip():
        story += [sec("OBSERVACIONES"), Spacer(1, 4), Paragraph(contrato['observaciones'], s_n), Spacer(1, 8)]

    # Cláusulas legales
    clausula = (
        "El presente contrato tiene carácter vinculante entre SERVICIOS MEMORIALES ALTAGRACIA C.A. "
        "y el Familiar Responsable identificado en la Sección 2. Los servicios serán prestados conforme "
        "a los términos acordados. En los contratos a Largo Plazo, la activación del servicio requerirá la "
        "notificación formal por parte del titular o sus familiares para la asignación inmediata de capilla. "
        "El incumplimiento en el pago de cuotas podrá dar lugar a la suspensión de los beneficios pactados. "
        "Cualquier controversia se resolverá ante los tribunales competentes de Calabozo, Estado Guárico, "
        "República Bolivariana de Venezuela."
    )
    story += [
        HRFlowable(width="100%", thickness=0.5, color=DORADO, spaceBefore=4, spaceAfter=6),
        Paragraph(clausula, s_leg),
        Spacer(1, 20)
    ]

    # Firmas
    med = W / 2 - 0.2 * inch
    t_firmas = Table([[
        Table([[HRFlowable(width=med, thickness=1, color=GRIS_OSC)],
               [Paragraph("Firma y sello autorizado", s_fa)],
               [Paragraph(EMPRESA["nombre"], s_fn)]], colWidths=[med]),
        Table([[HRFlowable(width=med, thickness=1, color=GRIS_OSC)],
               [Paragraph("Firma del Familiar Responsable", s_fa)],
               [Paragraph(f"{contrato['responsable']} | C.I.: {contrato['responsable_cedula']}", s_fn)]], colWidths=[med]),
    ]], colWidths=[W / 2, W / 2])
    t_firmas.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
    story.append(KeepTogether(t_firmas))

    def pie(cv, d):
        cv.saveState()
        cv.setFont("Helvetica", 7)
        cv.setFillColor(GRIS_MEDIO)
        cv.drawCentredString(
            letter[0] / 2, 0.45 * inch,
            f"{EMPRESA['nombre']} · {EMPRESA['telefono']} · {EMPRESA['correo']} · Pág. {d.page}"
        )
        cv.restoreState()

    doc.build(story, onFirstPage=pie, onLaterPages=pie)

    # Guardar la ruta en la base de datos
    try:
        conn = obtener_conexion()
        conn.execute("UPDATE contratos SET pdf_ruta = ? WHERE id = ?", (filename, contrato_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

    return filename


def generar_pdf_recibo_pago(pago_id: int) -> Optional[str]:
    """
    Genera un Recibo de Pago Oficial profesional en PDF (ideal para Plan Nacional Funerario - PNF o Contratos Generales)
    destacando el mes/período cancelado, datos del titular, carga familiar amparada, desglose del pago y saldo del plan.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib import colors as rc
    from reportlab.lib.units import inch
    from utils.helpers import formatear_fecha_ddmmyyyy

    conn = obtener_conexion()
    cursor = conn.cursor()

    # 1. Obtener pago
    cursor.execute("""
        SELECT p.id, p.fecha, p.monto, p.metodo, p.referencia, p.moneda, p.tasa_cambio,
               p.contrato_id, p.cuota_id, p.mes_periodo
        FROM pagos p
        WHERE p.id = ?
    """, (pago_id,))
    pago_row = cursor.fetchone()
    if not pago_row:
        conn.close()
        return None

    pid, p_fecha, p_monto, p_metodo, p_ref, p_moneda, p_tasa, cid, cuota_id, p_mes_periodo = pago_row

    # 2. Obtener contrato y titular
    cursor.execute("""
        SELECT c.id, c.numero, c.fecha_contrato, c.monto_total, c.pagado,
               COALESCE(c.tipo_contrato, 'Inmediato') as tipo_contrato,
               c.paquete, c.pnf_asociado, c.pnf_numero,
               COALESCE(d.nombre || ' ' || d.apellido, 'Por asignar (A futuro)') as difunto,
               COALESCE(d.cedula, 'N/E') as difunto_cedula,
               COALESCE(f.resp_nombre || ' ' || f.resp_apellido, 'Sin titular') as titular,
               COALESCE(f.resp_cedula, '—') as titular_cedula,
               COALESCE(f.resp_telefono, '—') as titular_telefono,
               COALESCE(f.resp_email, '—') as titular_email,
               COALESCE(f.resp_direccion, '—') as titular_direccion,
               COALESCE(cap.nombre, 'Sin Capilla Asignada') as capilla
        FROM contratos c
        LEFT JOIN difuntos d ON c.difunto_id = d.id
        LEFT JOIN familias f ON c.familia_id = f.familia_id
        LEFT JOIN capillas cap ON c.capilla_id = cap.id
        WHERE c.id = ?
    """, (cid,))
    c_row = cursor.fetchone()
    if not c_row:
        conn.close()
        return None

    (c_id, c_numero, c_fecha, c_total, c_pagado, c_tipo, c_paquete, c_pnf_asoc, c_pnf_num,
     dif_nombre, dif_ced, tit_nombre, tit_ced, tit_tel, tit_email, tit_dir, cap_nombre) = c_row

    # 3. Beneficiarios PNF
    cursor.execute("""
        SELECT nombre_completo, tipo_documento, cedula, folio, acta, fecha_nacimiento, edad, parentesco
        FROM contrato_beneficiarios
        WHERE contrato_id = ?
        ORDER BY id ASC
    """, (cid,))
    beneficiarios = cursor.fetchall()
    conn.close()

    # Preparar directorio y nombre de archivo
    os.makedirs(CONTRATOS_DIR, exist_ok=True)
    clean_num = str(c_numero).replace("/", "-").replace(" ", "_")
    filename = os.path.join(CONTRATOS_DIR, f"Recibo_Pago_{clean_num}_PAG_{pid:06d}.pdf")

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch
    )

    W = letter[0] - 1.0 * inch  # Ancho útil

    # Colores corporativos
    AZUL_OSCURO = rc.HexColor("#1A1A2E")
    DORADO = rc.HexColor("#D4AF37")
    GRIS_FONDO = rc.HexColor("#F8F9FA")
    GRIS_BORDE = rc.HexColor("#D0D5DD")
    VERDE = rc.HexColor("#27AE60")

    def est(nombre, **kw):
        return ParagraphStyle(nombre, **kw)

    s_tit_corp = est("r_tit_corp", fontName="Helvetica-Bold", fontSize=14, leading=17, alignment=TA_CENTER, textColor=AZUL_OSCURO)
    s_sub_corp = est("r_sub_corp", fontName="Helvetica", fontSize=8, leading=11, alignment=TA_CENTER, textColor=rc.HexColor("#555555"))
    s_badge = est("r_badge", fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=TA_CENTER, textColor=rc.white)
    s_sec = est("r_sec", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=AZUL_OSCURO)
    s_lbl = est("r_lbl", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=rc.HexColor("#333333"))
    s_val = est("r_val", fontName="Helvetica", fontSize=8, leading=10, textColor=rc.HexColor("#111111"))
    s_destacado = est("r_dest", fontName="Helvetica-Bold", fontSize=11, leading=14, alignment=TA_CENTER, textColor=AZUL_OSCURO)

    story = []

    # 1. ENCABEZADO
    story.append(Paragraph(f"<b>{EMPRESA['nombre']}</b>", s_tit_corp))
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        f"RIF: {EMPRESA['rif']}  ·  {EMPRESA['direccion']}<br/>"
        f"Teléfono: {EMPRESA['telefono']}  ·  Correo: {EMPRESA['correo']}",
        s_sub_corp
    ))
    story.append(Spacer(1, 6))

    # Título según tipo de contrato
    es_pnf = bool(c_pnf_asoc) or c_tipo == "Largo Plazo" or "PNF" in str(c_numero).upper()
    titulo_doc = "RECIBO DE PAGO — PLAN NACIONAL FUNERARIO (PNF)" if es_pnf else "RECIBO OFICIAL DE PAGO — COMPROBANTE DE CAJA"

    t_titulo = Table(
        [[Paragraph(f"<b>{titulo_doc}</b>", s_badge)]],
        colWidths=[W]
    )
    t_titulo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL_OSCURO),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(t_titulo)
    story.append(Spacer(1, 4))

    # Sub-barra con datos de emisión
    f_pago_fmt = formatear_fecha_ddmmyyyy(p_fecha)
    t_sub = Table([
        [
            Paragraph(f"<b>N° Comprobante:</b> REC-PAG-{pid:06d}", s_val),
            Paragraph(f"<b>Fecha de Pago:</b> {f_pago_fmt}", s_val),
            Paragraph(f"<b>Contrato N°:</b> {c_numero}", s_val)
        ]
    ], colWidths=[W * 0.35, W * 0.35, W * 0.30])
    t_sub.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_FONDO),
        ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_sub)
    story.append(Spacer(1, 6))

    # BANNER DESTACADO: MES / PERÍODO CANCELADO
    periodo_texto = p_mes_periodo or "Abono / Pago General a Saldo"
    t_periodo = Table([
        [Paragraph(f"🗓️ <b>MES / PERÍODO CANCELADO:</b> <font color='#B45309'>{periodo_texto.upper()}</font>", s_destacado)]
    ], colWidths=[W])
    t_periodo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), rc.HexColor("#FEF3C7")),
        ("BOX", (0, 0), (-1, -1), 1, DORADO),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(t_periodo)
    story.append(Spacer(1, 8))

    # SECCIÓN 1: DATOS DEL TITULAR / AFILIADO
    def fila_kv(l1, v1, l2, v2):
        return [
            Paragraph(f"<b>{l1}</b>", s_lbl), Paragraph(str(v1), s_val),
            Paragraph(f"<b>{l2}</b>", s_lbl), Paragraph(str(v2), s_val)
        ]

    datos_tit_filas = [
        fila_kv("Titular Afiliado:", tit_nombre, "Cédula de Identidad:", tit_ced),
        fila_kv("Teléfono de Contacto:", tit_tel, "Correo Electrónico:", tit_email),
        fila_kv("Dirección / Domicilio:", tit_dir, "Tipo de Plan / Servicio:", f"{c_tipo} ({c_paquete})"),
    ]
    if es_pnf and c_pnf_num:
        datos_tit_filas.append(fila_kv("N° Certificado PNF:", c_pnf_num, "Capilla / Sede:", cap_nombre))

    story.append(Paragraph("<b>1. DATOS DEL TITULAR / CONTRATANTE</b>", s_sec))
    story.append(Spacer(1, 3))
    t_tit = Table(datos_tit_filas, colWidths=[W * 0.20, W * 0.30, W * 0.20, W * 0.30])
    t_tit.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_FONDO),
        ("GRID", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_tit)
    story.append(Spacer(1, 8))

    # SECCIÓN 2: CARGA FAMILIAR AMPARADA (si es PNF y tiene beneficiarios)
    if beneficiarios:
        story.append(Paragraph(f"<b>2. CARGA FAMILIAR AMPARADA — PNF ({len(beneficiarios)} BENEFICIARIOS)</b>", s_sec))
        story.append(Spacer(1, 3))
        ben_rows = [[
            Paragraph("<b>N°</b>", s_lbl),
            Paragraph("<b>Nombre Completo</b>", s_lbl),
            Paragraph("<b>Documento (C.I. / Partida)</b>", s_lbl),
            Paragraph("<b>F. Nacimiento</b>", s_lbl),
            Paragraph("<b>Edad</b>", s_lbl),
            Paragraph("<b>Parentesco</b>", s_lbl)
        ]]
        for idx, b in enumerate(beneficiarios, 1):
            doc_str = f"C.I: {b[2]}" if b[1] == "Cedula" else f"Partida (F:{b[3] or '—'} A:{b[4] or '—'})"
            fnac_fmt = formatear_fecha_ddmmyyyy(b[5])
            ben_rows.append([
                Paragraph(str(idx), s_val),
                Paragraph(str(b[0]), s_val),
                Paragraph(doc_str, s_val),
                Paragraph(fnac_fmt, s_val),
                Paragraph(f"{b[6]} años", s_val),
                Paragraph(str(b[7] or "Familiar"), s_val)
            ])
        t_ben = Table(ben_rows, colWidths=[W * 0.05, W * 0.30, W * 0.25, W * 0.15, W * 0.10, W * 0.15])
        t_ben.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rc.HexColor("#E2E8F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rc.white, GRIS_FONDO]),
            ("GRID", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_ben)
        story.append(Spacer(1, 8))

    # SECCIÓN 3: DETALLE DEL PAGO
    num_sec_pago = "3" if beneficiarios else "2"
    story.append(Paragraph(f"<b>{num_sec_pago}. DETALLE DE LA TRANSACCIÓN Y FACTURACIÓN</b>", s_sec))
    story.append(Spacer(1, 3))

    bs_info = "—"
    if p_moneda == "BS" or p_tasa:
        tasa_val = p_tasa or 1.0
        monto_bs = p_monto * tasa_val if p_moneda == "USD" else p_monto
        bs_info = f"Bs {monto_bs:,.2f} (Tasa: 1 USD = {tasa_val:,.2f} BS)"

    detalle_pago_filas = [
        fila_kv("Concepto / Mes Cancelado:", periodo_texto, "Monto Pagado en Divisa:", f"${p_monto:,.2f} USD"),
        fila_kv("Forma de Pago:", p_metodo, "Equivalente en Bolívares:", bs_info),
        fila_kv("Moneda de Registro:", p_moneda or "USD", "Referencia / Comprobante:", p_ref or "N/A"),
    ]
    t_det_pago = Table(detalle_pago_filas, colWidths=[W * 0.22, W * 0.28, W * 0.22, W * 0.28])
    t_det_pago.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_FONDO),
        ("GRID", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_det_pago)
    story.append(Spacer(1, 8))

    # SECCIÓN 4: ESTADO DE CUENTA
    num_sec_cta = "4" if beneficiarios else "3"
    story.append(Paragraph(f"<b>{num_sec_cta}. ESTADO DE CUENTA DEL PLAN / CONTRATO</b>", s_sec))
    story.append(Spacer(1, 3))

    saldo_act = max(0.0, c_total - c_pagado)
    t_saldo = Table([
        [
            Paragraph("<b>Total del Contrato:</b>", s_lbl), Paragraph(f"${c_total:,.2f}", s_val),
            Paragraph("<b>Total Pagado Acumulado:</b>", s_lbl), Paragraph(f"${c_pagado:,.2f}", s_val),
            Paragraph("<b>Saldo Pendiente:</b>", s_lbl), Paragraph(f"<b>${saldo_act:,.2f}</b>", s_lbl)
        ]
    ], colWidths=[W * 0.18, W * 0.15, W * 0.22, W * 0.15, W * 0.15, W * 0.15])
    t_saldo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), rc.HexColor("#EFF6FF")),
        ("BOX", (0, 0), (-1, -1), 0.5, rc.HexColor("#93C5FD")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_saldo)
    story.append(Spacer(1, 10))

    # TEXTO DE VALIDEZ Y CLÁUSULA
    clausula_recibo = (
        "<b>CERTIFICACIÓN:</b> El presente recibo de pago constituye comprobante legal de abono y vigencia del período "
        "indicado para los servicios contratados y beneficiarios amparados en el Plan Nacional Funerario (PNF), "
        "sujeto a los términos del contrato suscrito con Servicios Memoriales Altagracia C.A."
    )
    story.append(Paragraph(clausula_recibo, est("r_cert", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=rc.HexColor("#444444"))))
    story.append(Spacer(1, 18))

    # FIRMAS
    t_firmas = Table([
        [
            Paragraph("___________________________________<br/><b>SERVICIOS MEMORIALES ALTAGRACIA</b><br/>Firma y Sello Autorizado", est("f1", fontName="Helvetica", fontSize=8, leading=10, alignment=TA_CENTER)),
            Paragraph(f"___________________________________<br/><b>{tit_nombre}</b><br/>C.I. {tit_ced} — Titular / Afiliado", est("f2", fontName="Helvetica", fontSize=8, leading=10, alignment=TA_CENTER))
        ]
    ], colWidths=[W * 0.5, W * 0.5])
    t_firmas.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(KeepTogether(t_firmas))

    # Pie de página
    def pie_recibo(cv, d):
        cv.saveState()
        cv.setFont("Helvetica", 7)
        cv.setFillColor(rc.HexColor("#777777"))
        cv.drawCentredString(
            letter[0] / 2, 0.3 * inch,
            f"{EMPRESA['nombre']} · Recibo generado el {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} · Pág. {d.page}"
        )
        cv.restoreState()

    doc.build(story, onFirstPage=pie_recibo, onLaterPages=pie_recibo)
    return filename


def generar_pdf_solvencia(contrato_id: int) -> Optional[str]:
    """Genera constancia PDF únicamente cuando el contrato cumple el criterio de solvencia."""
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from services.solvencia_service import SolvenciaService
    from utils.helpers import formatear_fecha_ddmmyyyy

    contrato = SolvenciaService.obtener_por_id(contrato_id)
    if not contrato:
        return None
    if not contrato["solvente"]:
        raise ValueError(
            "No se puede emitir la solvencia: el contrato está cancelado o mantiene un saldo superior a $0,01."
        )

    os.makedirs(CONTRATOS_DIR, exist_ok=True)
    numero_limpio = "".join(
        caracter if caracter.isalnum() or caracter in "-_" else "_"
        for caracter in str(contrato["numero"])
    )
    marca_tiempo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(
        CONTRATOS_DIR, f"Solvencia_{numero_limpio}_{marca_tiempo}.pdf"
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="SolvenciaEmpresa", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=15, leading=19, textColor=colors.HexColor("#2C2C2C"),
        alignment=TA_CENTER, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="SolvenciaTitulo", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=14, leading=18, textColor=colors.HexColor("#B8860B"),
        alignment=TA_CENTER, spaceBefore=16, spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        name="SolvenciaTexto", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=10, leading=15,
    ))
    styles.add(ParagraphStyle(
        name="SolvenciaAviso", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8, leading=11, textColor=colors.HexColor("#555555"),
    ))

    parrafo = lambda valor: Paragraph(escape(str(valor or "—")), styles["SolvenciaTexto"])
    filas = [
        [parrafo("N° de contrato"), parrafo(contrato["numero"])],
        [parrafo("Tipo de contrato"), parrafo(contrato["tipo_contrato"])],
        [parrafo("Fecha del contrato"), parrafo(formatear_fecha_ddmmyyyy(contrato["fecha_contrato"]))],
        [parrafo("Estado del contrato"), parrafo(contrato["estado_contrato"])],
        [parrafo("Titular / responsable"), parrafo(contrato["titular"])],
        [parrafo("Cédula del titular"), parrafo(contrato["titular_cedula"])],
        [parrafo("Difunto / beneficiario"), parrafo(contrato["difunto"])],
        [parrafo("Cédula del difunto"), parrafo(contrato["difunto_cedula"])],
        [parrafo("Monto total"), parrafo(f"${contrato['monto_total']:,.2f}")],
        [parrafo("Total pagado"), parrafo(f"${contrato['pagado']:,.2f}")],
        [parrafo("Saldo pendiente"), parrafo(f"${contrato['saldo_pendiente']:,.2f}")],
    ]
    story = [
        Paragraph(escape(EMPRESA["nombre"]), styles["SolvenciaEmpresa"]),
        Paragraph(
            f"RIF: {escape(EMPRESA['rif'])}<br/>"
            f"{escape(EMPRESA['direccion'])}<br/>"
            f"Tel: {escape(EMPRESA['telefono'])} · {escape(EMPRESA['correo'])}",
            styles["SolvenciaAviso"],
        ),
        Paragraph("CONSTANCIA DE SOLVENCIA DE CONTRATO FUNERARIO", styles["SolvenciaTitulo"]),
        Paragraph(
            f"Se hace constar que el contrato <b>{escape(str(contrato['numero']))}</b> "
            "se encuentra solvente a la fecha de emisión de este documento.",
            styles["SolvenciaTexto"],
        ),
        Spacer(1, 14),
    ]
    tabla = Table(filas, colWidths=[2.1 * inch, 4.7 * inch], hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F4F4F4")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([
        tabla,
        Spacer(1, 16),
        Paragraph(
            "Documento generado por el sistema. La condición de solvencia se verificó "
            "al momento de su emisión; saldo permitido por redondeo: hasta $0,01.",
            styles["SolvenciaAviso"],
        ),
        Spacer(1, 42),
        Paragraph(
            "________________________________________<br/>"
            "Firma y sello autorizado",
            ParagraphStyle(
                name="SolvenciaFirma", parent=styles["SolvenciaAviso"],
                alignment=TA_CENTER,
            ),
        ),
        Spacer(1, 12),
        Paragraph(
            f"Emitido: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ParagraphStyle(
                name="SolvenciaFecha", parent=styles["SolvenciaAviso"],
                alignment=TA_CENTER,
            ),
        ),
    ])
    SimpleDocTemplate(
        filename, pagesize=letter, leftMargin=0.85 * inch,
        rightMargin=0.85 * inch, topMargin=0.7 * inch, bottomMargin=0.7 * inch,
    ).build(story)
    return filename
