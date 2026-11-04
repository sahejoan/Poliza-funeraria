# services/db_service.py - Base de datos con estructura Familias + Difuntos + Servicios Adicionales
import os
import sqlite3
import datetime
import random
from typing import Optional, Tuple, List

DB_NAME = "memoriales_altagracia.db"

# Rutas absolutas (evita crear una BD vacía si el sistema se ejecuta desde otra carpeta)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, DB_NAME)
CONTRATOS_DIR = os.path.join(BASE_DIR, "contratos_generados")
REPORTES_DIR = os.path.join(BASE_DIR, "reportes")

# Datos iniciales
CAPILLAS = [
    {"nombre": "Capilla San José", "capacidad": 50, "descripcion": "Capilla principal con capacidad para 50 personas"},
    {"nombre": "Capilla La Paz", "capacidad": 30, "descripcion": "Capilla íntima para velorios privados"},
    {"nombre": "Capilla Santa Teresa", "capacidad": 40, "descripcion": "Capilla con decoración floral incluida"}
]

# Estados posibles de una capilla
ESTADOS_CAPILLA = ["Disponible", "Ocupada", "Mantenimiento"]

EMPRESA = {
    "nombre": "SERVICIOS MEMORIALES ALTAGRACIA C.A.",
    "rif": "J-41234567-8",
    "direccion": "Carrera 13 entre Calles 9 y 10, Calabozo, Estado Guárico, Venezuela",
    "telefono": "+58 246-1234567",
    "correo": "contacto@memorialesaltagracia.com"
}

# Paquetes (fuente única de precios y descripciones: la usan el formulario, el visor y el PDF)
PAQUETES = {
    "BRONCE": {
        "precio": 850.00,
        "descripcion": "Servicio básico: Capilla por 12 horas, preparación del cuerpo, traslado local, "
                       "acta de defunción, 1 corona floral",
        "incluye": ["Capilla 12h", "Preparación del cuerpo", "Traslado local", "Acta de defunción",
                    "1 corona floral"]
    },
    "PLATA": {
        "precio": 1800.00,
        "descripcion": "Servicio integral: Capilla por 24 horas, preparación premium, traslado regional, "
                       "cafetería, 3 coronas florales, registro de obituario",
        "incluye": ["Capilla 24h", "Preparación premium", "Traslado regional", "Cafetería",
                    "3 coronas florales", "Registro de obituario"]
    },
    "ORO": {
        "precio": 3800.00,
        "descripcion": "Servicio VIP: Capilla por 48 horas, preparación de lujo, traslado nacional, "
                       "catering completo, 6 coronas florales, video homenaje, registro en prensa",
        "incluye": ["Capilla 48h", "Preparación de lujo", "Traslado nacional", "Catering completo",
                    "6 coronas florales", "Video homenaje", "Registro en prensa"]
    }
}

INVENTARIO_INICIAL = [
    ("Ataúd Caoba Clásico", 5, 850.00),
    ("Ataúd Metal Plateado", 8, 450.00),
    ("Corona de Rosas", 12, 85.00),
    ("Libro de Condolencias", 15, 35.00)
]

# Esquema de la tabla contratos.
# difunto_id, capilla_id, fecha_velacion y horas aceptan vacío porque un contrato a
# LARGO PLAZO (previsión) se firma antes de que exista un difunto o una capilla asignada.
SQL_TABLA_CONTRATOS = """CREATE TABLE IF NOT EXISTS {nombre} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    fecha_contrato TEXT NOT NULL,
    familia_id TEXT NOT NULL,
    difunto_id INTEGER,
    paquete TEXT NOT NULL,
    capilla_id INTEGER,
    fecha_velacion TEXT,
    hora_inicio TEXT,
    hora_fin TEXT,
    monto_total REAL NOT NULL,
    metodo_pago TEXT NOT NULL,
    inicial REAL DEFAULT 0,
    numero_cuotas INTEGER DEFAULT 1,
    pagado REAL DEFAULT 0,
    estado TEXT DEFAULT 'Activo',
    observaciones TEXT,
    requiere_cremacion INTEGER DEFAULT 0,
    tipo_traslado TEXT DEFAULT 'Local',
    hora_llegada_real TEXT,
    hora_salida_capilla TEXT,
    estado_servicio TEXT DEFAULT 'Pendiente',
    tipo_velacion TEXT DEFAULT 'Funeraria',
    tipo_contrato TEXT DEFAULT 'Inmediato',
    fecha_llegada_real TEXT,
    pnf_asociado INTEGER DEFAULT 0,
    pnf_numero TEXT,
    pnf_cubre_traslado INTEGER DEFAULT 0,
    pnf_cubre_cremacion INTEGER DEFAULT 0,
    costo_paquete REAL,
    costo_cremacion REAL,
    costo_traslado REAL,
    costo_productos REAL,
    costo_servicios REAL,
    descuento_pnf REAL DEFAULT 0,
    fecha_activacion TEXT,
    pdf_ruta TEXT,
    titular_edad INTEGER,
    frecuencia_pago TEXT DEFAULT 'Mensual',
    FOREIGN KEY (familia_id) REFERENCES familias(familia_id),
    FOREIGN KEY (difunto_id) REFERENCES difuntos(id),
    FOREIGN KEY (capilla_id) REFERENCES capillas(id)
)"""


def obtener_conexion():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def generar_familia_id() -> str:
    fecha = datetime.datetime.now().strftime("%Y%m%d")
    random_num = random.randint(1, 999)
    return f"FAM-{fecha}-{random_num:03d}"


def normalizar_cedula(cedula: str) -> str:
    """Quita espacios, puntos, guiones y el prefijo V para comparar cédulas (V-12.345.678 -> 12345678)"""
    if cedula is None:
        return ""
    limpia = str(cedula).strip().upper().replace(".", "").replace(" ", "").replace("-", "")
    if limpia.startswith("V") and limpia[1:].isdigit():
        limpia = limpia[1:]
    return limpia


def _columnas(cursor, tabla: str) -> dict:
    """Devuelve {columna: notnull} de una tabla"""
    return {row[1]: row[3] for row in cursor.execute(f"PRAGMA table_info({tabla})").fetchall()}


def init_db():
    conn = obtener_conexion()
    cursor = conn.cursor()

    # ========== TABLA: FAMILIAS ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS familias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        familia_id TEXT UNIQUE NOT NULL,
        resp_cedula TEXT UNIQUE NOT NULL,
        resp_nombre TEXT NOT NULL,
        resp_apellido TEXT NOT NULL,
        resp_telefono TEXT,
        resp_email TEXT,
        resp_direccion TEXT,
        fecha_creacion TEXT NOT NULL,
        activo INTEGER DEFAULT 1
    )""")

    # ========== TABLA: DIFUNTOS ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS difuntos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        familia_id TEXT NOT NULL,
        cedula TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        fecha_nacimiento TEXT,
        fecha_defuncion TEXT,
        causa_muerte TEXT,
        FOREIGN KEY (familia_id) REFERENCES familias(familia_id) ON DELETE CASCADE
    )""")

    # ========== TABLA: USUARIOS ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nombre TEXT NOT NULL,
        rol TEXT DEFAULT 'usuario',
        activo INTEGER DEFAULT 1,
        fecha_creacion TEXT NOT NULL
    )""")

    # ========== TABLA: CONTRATOS ==========
    cursor.execute(SQL_TABLA_CONTRATOS.format(nombre="contratos"))

    # ========== TABLA: CAPILLAS ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS capillas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        capacidad INTEGER NOT NULL,
        descripcion TEXT,
        estado TEXT DEFAULT 'Disponible',
        activo INTEGER DEFAULT 1
    )""")

    # ========== TABLA: CUOTAS ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS cuotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contrato_id INTEGER NOT NULL,
        numero INTEGER NOT NULL,
        monto REAL NOT NULL,
        fecha_vencimiento TEXT NOT NULL,
        fecha_pago TEXT,
        estado TEXT DEFAULT 'Pendiente',
        FOREIGN KEY (contrato_id) REFERENCES contratos(id) ON DELETE CASCADE
    )""")

    # ========== TABLA: PAGOS ==========
    # monto          -> SIEMPRE en USD (es lo que se descuenta del contrato)
    # monto_original -> monto en la moneda en que se pagó (USD o BS)
    cursor.execute("""CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contrato_id INTEGER NOT NULL,
        cuota_id INTEGER,
        fecha TEXT NOT NULL,
        monto REAL NOT NULL,
        metodo TEXT NOT NULL,
        referencia TEXT,
        moneda TEXT DEFAULT 'USD',
        tasa_cambio REAL,
        monto_original REAL,
        mes_periodo TEXT,
        FOREIGN KEY (contrato_id) REFERENCES contratos(id) ON DELETE CASCADE,
        FOREIGN KEY (cuota_id) REFERENCES cuotas(id) ON DELETE SET NULL
    )""")

    # ========== TABLA: INVENTARIO ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        stock INTEGER NOT NULL DEFAULT 0,
        precio REAL NOT NULL,
        stock_minimo INTEGER DEFAULT 5
    )""")

    # ========== TABLA: CONTRATO_PRODUCTOS ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS contrato_productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contrato_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        precio_unitario REAL NOT NULL,
        FOREIGN KEY (contrato_id) REFERENCES contratos(id) ON DELETE CASCADE,
        FOREIGN KEY (producto_id) REFERENCES inventario(id)
    )""")

    # ========== TABLA: SERVICIOS ADICIONALES ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS contratos_servicios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contrato_id INTEGER NOT NULL,
        tipo_velacion TEXT NOT NULL,
        servicio_key TEXT NOT NULL,
        servicio_nombre TEXT NOT NULL,
        cantidad INTEGER DEFAULT 1,
        precio_unitario REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (contrato_id) REFERENCES contratos(id) ON DELETE CASCADE
    )""")

    # ========== TABLA: BENEFICIARIOS DE CONTRATOS (PNF) ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS contrato_beneficiarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contrato_id INTEGER NOT NULL,
        nombre_completo TEXT NOT NULL,
        tipo_documento TEXT NOT NULL,
        cedula TEXT,
        folio TEXT,
        acta TEXT,
        fecha_nacimiento TEXT NOT NULL,
        edad INTEGER NOT NULL,
        parentesco TEXT,
        FOREIGN KEY (contrato_id) REFERENCES contratos(id) ON DELETE CASCADE
    )""")

    # ========== TABLA: BITACORA ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS bitacora (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        accion TEXT NOT NULL,
        fecha TEXT NOT NULL,
        detalles TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )""")

    # ========== TABLA: MOVIMIENTOS INVENTARIO ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS inventario_movimientos (
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
    )""")

    # ========== TABLA: CONFIGURACION ==========
    cursor.execute("""CREATE TABLE IF NOT EXISTS configuracion (
        clave TEXT PRIMARY KEY,
        valor TEXT,
        actualizado TEXT
    )""")

    conn.commit()

    # Insertar capillas
    cursor.execute("SELECT COUNT(*) FROM capillas")
    if cursor.fetchone()[0] == 0:
        for cap in CAPILLAS:
            cursor.execute("INSERT INTO capillas (nombre, capacidad, descripcion) VALUES (?, ?, ?)",
                           (cap["nombre"], cap["capacidad"], cap["descripcion"]))

    # Insertar inventario inicial
    cursor.execute("SELECT COUNT(*) FROM inventario")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO inventario (nombre, stock, precio) VALUES (?, ?, ?)", INVENTARIO_INICIAL)

    # Insertar tasa de cambio por defecto
    cursor.execute("SELECT COUNT(*) FROM configuracion WHERE clave = 'tasa_cambio_usd_bs'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO configuracion (clave, valor, actualizado)
            VALUES ('tasa_cambio_usd_bs', '40.0', ?)
        """, (datetime.datetime.now().isoformat(),))

    conn.commit()
    conn.close()

    # Actualizar estructura de bases de datos creadas con versiones anteriores
    migrar_esquema()

    # Migrar datos antiguos si existen
    migrar_datos_antiguos()
    print("[OK] Base de datos inicializada correctamente")


def migrar_esquema():
    """Actualiza la estructura de una BD existente sin perder datos."""
    conn = sqlite3.connect(DB_PATH, isolation_level=None)  # control manual de transacciones
    cursor = conn.cursor()
    try:
        # ---- 1. contratos: reconstruir si difunto/capilla siguen siendo obligatorios ----
        cols = _columnas(cursor, "contratos")
        necesita_reconstruir = cols.get("difunto_id") == 1 or cols.get("capilla_id") == 1 \
            or cols.get("fecha_velacion") == 1
        if necesita_reconstruir:
            cursor.execute("PRAGMA foreign_keys = OFF")
            cursor.execute("BEGIN")
            cursor.execute("DROP TABLE IF EXISTS contratos_nueva")
            cursor.execute(SQL_TABLA_CONTRATOS.format(nombre="contratos_nueva"))
            nuevas = _columnas(cursor, "contratos_nueva")
            comunes = [c for c in cols if c in nuevas]
            lista = ", ".join(comunes)
            cursor.execute(f"INSERT INTO contratos_nueva ({lista}) SELECT {lista} FROM contratos")
            cursor.execute("DROP TABLE contratos")
            cursor.execute("ALTER TABLE contratos_nueva RENAME TO contratos")
            cursor.execute("COMMIT")
            cursor.execute("PRAGMA foreign_keys = ON")
        else:
            # Agregar columnas nuevas que falten
            cursor.execute("DROP TABLE IF EXISTS contratos_tmp_esquema")
            cursor.execute(SQL_TABLA_CONTRATOS.format(nombre="contratos_tmp_esquema"))
            esperadas = cursor.execute("PRAGMA table_info(contratos_tmp_esquema)").fetchall()
            cursor.execute("DROP TABLE contratos_tmp_esquema")
            for col in esperadas:
                nombre, tipo, default = col[1], col[2], col[4]
                if nombre not in cols:
                    sql = f"ALTER TABLE contratos ADD COLUMN {nombre} {tipo}"
                    if default is not None:
                        sql += f" DEFAULT {default}"
                    cursor.execute(sql)

        # ---- 2. capillas: columna activo ----
        if "activo" not in _columnas(cursor, "capillas"):
            cursor.execute("ALTER TABLE capillas ADD COLUMN activo INTEGER DEFAULT 1")
            cursor.execute("UPDATE capillas SET activo = 1 WHERE activo IS NULL")

        # ---- 3. pagos: monto_original y mes_periodo ----
        cols_pagos = _columnas(cursor, "pagos")
        if "monto_original" not in cols_pagos:
            cursor.execute("ALTER TABLE pagos ADD COLUMN monto_original REAL")
        if "mes_periodo" not in cols_pagos:
            cursor.execute("ALTER TABLE pagos ADD COLUMN mes_periodo TEXT")
        cursor.execute("BEGIN")
        # Pagos en BS registrados con la versión anterior guardaban los bolívares en 'monto'
        # (se sumaban como si fueran dólares). Se corrigen convirtiéndolos a USD.
        cursor.execute("""
            UPDATE pagos
            SET monto_original = monto, monto = ROUND(monto / tasa_cambio, 2)
            WHERE monto_original IS NULL AND moneda = 'BS' AND tasa_cambio IS NOT NULL AND tasa_cambio > 0
        """)
        cursor.execute("UPDATE pagos SET monto_original = monto WHERE monto_original IS NULL")
        # Recalcular lo pagado en cada contrato
        cursor.execute("""
            UPDATE contratos
            SET pagado = COALESCE((SELECT ROUND(SUM(p.monto), 2) FROM pagos p WHERE p.contrato_id = contratos.id), 0)
        """)
        cursor.execute("COMMIT")

        # ---- 4. Completar el desglose de costos de contratos anteriores ----
        _completar_desglose_contratos(cursor)

        # ---- 5. Tabla de beneficiarios para contratos PNF ----
        cursor.execute("""CREATE TABLE IF NOT EXISTS contrato_beneficiarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contrato_id INTEGER NOT NULL,
            nombre_completo TEXT NOT NULL,
            tipo_documento TEXT NOT NULL,
            cedula TEXT,
            folio TEXT,
            acta TEXT,
            fecha_nacimiento TEXT NOT NULL,
            edad INTEGER NOT NULL,
            parentesco TEXT,
            FOREIGN KEY (contrato_id) REFERENCES contratos(id) ON DELETE CASCADE
        )""")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass
        conn.close()


def _completar_desglose_contratos(cursor):
    """Calcula costo_paquete, costo_cremacion, etc. para contratos creados antes de guardar el desglose."""
    from services.precio_service import COSTO_CREMACION, COSTOS_TRASLADO
    filas = cursor.execute("""
        SELECT id, paquete, requiere_cremacion, tipo_traslado FROM contratos WHERE costo_paquete IS NULL
    """).fetchall()
    if not filas:
        return
    cursor.execute("BEGIN")
    for cid, paquete, cremacion, traslado in filas:
        costo_paquete = PAQUETES.get(paquete, {}).get("precio", 0.0)
        costo_cremacion = COSTO_CREMACION if cremacion else 0.0
        costo_traslado = COSTOS_TRASLADO.get(traslado or "Local", 0.0)
        costo_productos = cursor.execute(
            "SELECT COALESCE(SUM(cantidad * precio_unitario), 0) FROM contrato_productos WHERE contrato_id = ?",
            (cid,)).fetchone()[0]
        costo_servicios = cursor.execute(
            "SELECT COALESCE(SUM(subtotal), 0) FROM contratos_servicios WHERE contrato_id = ?",
            (cid,)).fetchone()[0]
        cursor.execute("""
            UPDATE contratos SET costo_paquete = ?, costo_cremacion = ?, costo_traslado = ?,
                   costo_productos = ?, costo_servicios = ?, descuento_pnf = COALESCE(descuento_pnf, 0),
                   tipo_contrato = COALESCE(tipo_contrato, 'Inmediato')
            WHERE id = ?
        """, (costo_paquete, costo_cremacion, costo_traslado, costo_productos, costo_servicios, cid))
    cursor.execute("COMMIT")


def migrar_datos_antiguos():
    conn = obtener_conexion()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clientes'")
    if cursor.fetchone():
        cursor.execute("""
            SELECT id, cedula, nombre, apellido, telefono, direccion, email, familiar_responsable_id
            FROM clientes WHERE tipo = 'responsable'
        """)
        responsables = cursor.fetchall()

        for resp in responsables:
            resp_id, cedula, nombre, apellido, telefono, direccion, email, _ = resp

            cursor.execute("SELECT familia_id FROM familias WHERE resp_cedula = ?", (cedula,))
            if not cursor.fetchone():
                familia_id = generar_familia_id()
                cursor.execute("""
                    INSERT INTO familias (familia_id, resp_cedula, resp_nombre, resp_apellido,
                                         resp_telefono, resp_email, resp_direccion, fecha_creacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (familia_id, cedula, nombre, apellido, telefono or "", email or "", direccion or "",
                      datetime.datetime.now().isoformat()))

                cursor.execute("""
                    SELECT cedula, nombre, apellido, fecha_nacimiento, fecha_defuncion, causa_muerte
                    FROM clientes
                    WHERE tipo = 'difunto' AND familiar_responsable_id = ?
                """, (resp_id,))
                difuntos = cursor.fetchall()

                for dif in difuntos:
                    cursor.execute("""
                        INSERT INTO difuntos (familia_id, cedula, nombre, apellido,
                                             fecha_nacimiento, fecha_defuncion, causa_muerte)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (familia_id, dif[0], dif[1], dif[2], dif[3], dif[4], dif[5]))

        conn.commit()
    conn.close()


class FamiliaRepository:
    @staticmethod
    def buscar_por_cedula(cedula: str) -> Optional[dict]:
        """Busca un responsable por cédula (acepta formatos como V-12.345.678)"""
        cedula_raw = (cedula or "").strip()
        cedula_norm = normalizar_cedula(cedula_raw)
        if not cedula_norm:
            return None
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT familia_id, resp_cedula, resp_nombre, resp_apellido,
                   resp_telefono, resp_email, resp_direccion, fecha_creacion
            FROM familias
            WHERE (resp_cedula = ? OR resp_cedula = ?) AND activo = 1
        """, (cedula_norm, cedula_raw))
        familia = cursor.fetchone()

        if not familia:
            conn.close()
            return None

        cursor.execute("""
            SELECT id, cedula, nombre, apellido, fecha_nacimiento, fecha_defuncion, causa_muerte
            FROM difuntos
            WHERE familia_id = ?
            ORDER BY fecha_defuncion DESC
        """, (familia[0],))
        difuntos = cursor.fetchall()

        conn.close()

        return {
            'familia_id': familia[0],
            'resp_cedula': familia[1],
            'resp_nombre': familia[2],
            'resp_apellido': familia[3],
            'resp_telefono': familia[4] or "",
            'resp_email': familia[5] or "",
            'resp_direccion': familia[6] or "",
            'fecha_creacion': familia[7],
            'difuntos': [{
                'id': d[0],
                'cedula': d[1],
                'nombre': d[2],
                'apellido': d[3],
                'fecha_nacimiento': d[4],
                'fecha_defuncion': d[5],
                'causa_muerte': d[6]
            } for d in difuntos]
        }

    @staticmethod
    def buscar_difunto_por_cedula(cedula: str) -> Optional[dict]:
        """Devuelve el difunto con esa cédula (y su familia) o None"""
        cedula_raw = (cedula or "").strip()
        cedula_norm = normalizar_cedula(cedula_raw)
        if not cedula_norm:
            return None
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.id, d.cedula, d.nombre, d.apellido, d.familia_id,
                   f.resp_nombre || ' ' || f.resp_apellido
            FROM difuntos d
            JOIN familias f ON d.familia_id = f.familia_id
            WHERE d.cedula = ? OR d.cedula = ?
        """, (cedula_norm, cedula_raw))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {'id': row[0], 'cedula': row[1], 'nombre': row[2], 'apellido': row[3],
                'familia_id': row[4], 'responsable': row[5]}

    @staticmethod
    def registrar_familia(resp_data: dict) -> str:
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            familia_id = generar_familia_id()
            # Evitar choques del ID aleatorio
            while cursor.execute("SELECT 1 FROM familias WHERE familia_id = ?", (familia_id,)).fetchone():
                familia_id = generar_familia_id()
            cursor.execute("""
                INSERT INTO familias (familia_id, resp_cedula, resp_nombre, resp_apellido,
                                     resp_telefono, resp_email, resp_direccion, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                familia_id,
                normalizar_cedula(resp_data['cedula']),
                resp_data['nombre'].strip(),
                resp_data['apellido'].strip(),
                resp_data.get('telefono', ''),
                resp_data.get('email', ''),
                resp_data.get('direccion', ''),
                datetime.datetime.now().isoformat()
            ))
            conn.commit()
            return familia_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def actualizar_responsable(familia_id: str, resp_data: dict) -> bool:
        """Actualiza los datos de contacto del familiar responsable"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE familias
                SET resp_nombre = ?, resp_apellido = ?, resp_telefono = ?, resp_email = ?, resp_direccion = ?
                WHERE familia_id = ?
            """, (
                resp_data['nombre'].strip(),
                resp_data['apellido'].strip(),
                resp_data.get('telefono', ''),
                resp_data.get('email', ''),
                resp_data.get('direccion', ''),
                familia_id
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def agregar_difunto(familia_id: str, difunto_data: dict) -> int:
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO difuntos (familia_id, cedula, nombre, apellido,
                                     fecha_nacimiento, fecha_defuncion, causa_muerte)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                familia_id,
                normalizar_cedula(difunto_data['cedula']),
                difunto_data['nombre'].strip(),
                difunto_data['apellido'].strip(),
                difunto_data.get('fecha_nacimiento'),
                difunto_data.get('fecha_defuncion'),
                difunto_data.get('causa_muerte')
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def listar_todas_familias(limite: int = 500) -> List[dict]:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.familia_id, f.resp_cedula, f.resp_nombre, f.resp_apellido,
                   f.resp_telefono, COUNT(d.id) as num_difuntos
            FROM familias f
            LEFT JOIN difuntos d ON f.familia_id = d.familia_id
            WHERE f.activo = 1
            GROUP BY f.familia_id
            ORDER BY f.fecha_creacion DESC
            LIMIT ?
        """, (limite,))

        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'familia_id': row[0],
                'resp_cedula': row[1],
                'resp_nombre_completo': f"{row[2]} {row[3]}",
                'resp_telefono': row[4] or "",
                'num_difuntos': row[5]
            })
        conn.close()
        return resultados

    @staticmethod
    def buscar_por_texto(texto: str) -> List[dict]:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT f.familia_id, f.resp_cedula, f.resp_nombre, f.resp_apellido, f.resp_telefono
            FROM familias f
            LEFT JOIN difuntos d ON f.familia_id = d.familia_id
            WHERE f.resp_cedula LIKE ?
               OR f.resp_nombre LIKE ?
               OR f.resp_apellido LIKE ?
               OR d.cedula LIKE ?
               OR d.nombre LIKE ?
               OR d.apellido LIKE ?
            LIMIT 20
        """, (f"%{texto}%", f"%{texto}%", f"%{texto}%", f"%{texto}%", f"%{texto}%", f"%{texto}%"))

        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'familia_id': row[0],
                'resp_cedula': row[1],
                'resp_nombre_completo': f"{row[2]} {row[3]}",
                'resp_telefono': row[4] or ""
            })
        conn.close()
        return resultados


class ContratoRepository:
    @staticmethod
    def actualizar_horario(contrato_id: int, hora_llegada: str, hora_salida: str,
                           fecha_llegada: str = None) -> bool:
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE contratos
                SET hora_llegada_real = ?, hora_salida_capilla = ?,
                    fecha_llegada_real = COALESCE(?, fecha_llegada_real)
                WHERE id = ?
            """, (hora_llegada, hora_salida, fecha_llegada, contrato_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error actualizando horario: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def obtener_contrato(contrato_id: int) -> Optional[Tuple]:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contratos WHERE id = ?", (contrato_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    @staticmethod
    def listar_contratos_activos() -> List[Tuple]:
        """(id, numero, nombre a mostrar, saldo pendiente). En planes a largo plazo sin difunto
        se muestra el titular."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.numero,
                   CASE WHEN d.id IS NOT NULL
                        THEN COALESCE(d.nombre, '') || ' ' || COALESCE(d.apellido, '')
                        ELSE 'Plan: ' || COALESCE(f.resp_nombre, '') || ' ' || COALESCE(f.resp_apellido, '')
                   END as nombre_mostrar,
                   ROUND(c.monto_total - c.pagado, 2) as pendiente
            FROM contratos c
            LEFT JOIN difuntos d ON c.difunto_id = d.id
            LEFT JOIN familias f ON c.familia_id = f.familia_id
            WHERE c.estado = 'Activo'
            ORDER BY c.id DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return rows

    @staticmethod
    def registrar_bitacora(usuario_id: int, accion: str, detalles: str = ""):
        if usuario_id is None:
            usuario_id = 1
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bitacora (usuario_id, accion, fecha, detalles)
            VALUES (?, ?, ?, ?)
        """, (usuario_id, accion, datetime.datetime.now().isoformat(), detalles))
        conn.commit()
        conn.close()

    @staticmethod
    def guardar_beneficiarios(contrato_id: int, beneficiarios: List[dict]):
        """Guarda la lista de beneficiarios asociados al contrato PNF"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM contrato_beneficiarios WHERE contrato_id = ?", (contrato_id,))
            for b in beneficiarios:
                cursor.execute("""
                    INSERT INTO contrato_beneficiarios 
                    (contrato_id, nombre_completo, tipo_documento, cedula, folio, acta, fecha_nacimiento, edad, parentesco)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    contrato_id,
                    b.get("nombre_completo", "").strip(),
                    b.get("tipo_documento", "Cedula"),
                    b.get("cedula", "").strip() if b.get("tipo_documento") == "Cedula" else None,
                    b.get("folio", "").strip() if b.get("tipo_documento") == "Partida" else None,
                    b.get("acta", "").strip() if b.get("tipo_documento") == "Partida" else None,
                    b.get("fecha_nacimiento", ""),
                    int(b.get("edad", 0)),
                    b.get("parentesco", "")
                ))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def obtener_beneficiarios(contrato_id: int) -> List[dict]:
        """Obtiene la lista de beneficiarios asociados a un contrato"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre_completo, tipo_documento, cedula, folio, acta, fecha_nacimiento, edad, parentesco
            FROM contrato_beneficiarios
            WHERE contrato_id = ?
            ORDER BY id
        """, (contrato_id,))
        filas = cursor.fetchall()
        conn.close()
        return [{
            "id": r[0],
            "nombre_completo": r[1],
            "tipo_documento": r[2],
            "cedula": r[3] or "",
            "folio": r[4] or "",
            "acta": r[5] or "",
            "fecha_nacimiento": r[6],
            "edad": r[7],
            "parentesco": r[8] or ""
        } for r in filas]



class CapillaRepository:
    """Gestión y modificación de capillas"""

    @staticmethod
    def listar_todas(solo_activas: bool = True) -> List[dict]:
        conn = obtener_conexion()
        cursor = conn.cursor()
        query = "SELECT id, nombre, capacidad, descripcion, estado, activo FROM capillas"
        if solo_activas:
            query += " WHERE activo = 1"
        query += " ORDER BY id"
        cursor.execute(query)
        filas = cursor.fetchall()
        conn.close()
        return [{
            "id": r[0],
            "nombre": r[1],
            "capacidad": r[2],
            "descripcion": r[3] or "",
            "estado": r[4],
            "activo": bool(r[5])
        } for r in filas]

    @staticmethod
    def listar_disponibles() -> List[dict]:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, capacidad, descripcion, estado
            FROM capillas WHERE activo = 1 AND estado = 'Disponible'
            ORDER BY nombre
        """)
        filas = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "nombre": r[1], "capacidad": r[2], "descripcion": r[3] or "", "estado": r[4]}
                for r in filas]

    @staticmethod
    def obtener_por_id(capilla_id: int) -> Optional[dict]:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, capacidad, descripcion, estado, activo FROM capillas WHERE id = ?", (capilla_id,))
        r = cursor.fetchone()
        conn.close()
        if not r:
            return None
        return {"id": r[0], "nombre": r[1], "capacidad": r[2], "descripcion": r[3] or "", "estado": r[4], "activo": bool(r[5])}

    @staticmethod
    def crear_capilla(nombre: str, capacidad: int, descripcion: str = "", estado: str = "Disponible") -> int:
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO capillas (nombre, capacidad, descripcion, estado, activo)
                VALUES (?, ?, ?, ?, 1)
            """, (nombre.strip(), int(capacidad), descripcion.strip(), estado))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def actualizar_capilla(capilla_id: int, nombre: str, capacidad: int, descripcion: str, estado: str) -> bool:
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE capillas
                SET nombre = ?, capacidad = ?, descripcion = ?, estado = ?
                WHERE id = ?
            """, (nombre.strip(), int(capacidad), descripcion.strip(), estado, capilla_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def cambiar_estado(capilla_id: int, nuevo_estado: str) -> Tuple[bool, str]:
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE capillas SET estado = ? WHERE id = ?", (nuevo_estado, capilla_id))
            conn.commit()
            if cursor.rowcount > 0:
                return (True, "OK")
            return (False, "Capilla no encontrada")
        except Exception as e:
            return (False, str(e))
        finally:
            conn.close()

    @staticmethod
    def desactivar_capilla(capilla_id: int) -> bool:
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE capillas SET activo = 0 WHERE id = ?", (capilla_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    # Alias convenientes
    @classmethod
    def obtener_todas(cls, solo_activas: bool = True) -> List[dict]:
        return cls.listar_todas(solo_activas)

    @classmethod
    def obtener_disponibles(cls) -> List[dict]:
        return cls.listar_disponibles()

    @classmethod
    def crear(cls, nombre: str, capacidad: int, descripcion: str = "", estado: str = "Disponible") -> int:
        return cls.crear_capilla(nombre, capacidad, descripcion, estado)

    @classmethod
    def actualizar(cls, capilla_id: int, nombre: str, capacidad: int, descripcion: str = "", estado: str = "Disponible") -> Tuple[bool, str]:
        ok = cls.actualizar_capilla(capilla_id, nombre, capacidad, descripcion, estado)
        return (True, "OK") if ok else (False, "Capilla no encontrada o sin cambios")

    @classmethod
    def eliminar(cls, capilla_id: int) -> bool:
        return cls.desactivar_capilla(capilla_id)


def obtener_config(clave: str, por_defecto: str = None) -> Optional[str]:
    """Lee un valor de la tabla configuracion"""
    try:
        conn = obtener_conexion()
        row = conn.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,)).fetchone()
        conn.close()
        return row[0] if row else por_defecto
    except sqlite3.Error:
        return por_defecto


def guardar_config(clave: str, valor: str):
    """Guarda un valor en la tabla configuracion"""
    conn = obtener_conexion()
    conn.execute("""
        INSERT OR REPLACE INTO configuracion (clave, valor, actualizado) VALUES (?, ?, ?)
    """, (clave, str(valor), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()