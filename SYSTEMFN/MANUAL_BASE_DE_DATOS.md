# Manual de la base de datos

**Sistema:** Memoriales Altagracia  
**Motor:** SQLite  
**Archivo:** `SYSTEMFN/memoriales_altagracia.db`  
**Código que administra la base:** `SYSTEMFN/services/db_service.py`

Este manual describe el esquema implementado en el código del sistema. Una base
antigua puede tener columnas adicionales o una estructura anterior; el programa
ejecuta migraciones al iniciar para acercarla al esquema vigente.

## 1. Resumen y configuración

SQLite guarda la base de datos en un archivo. No requiere instalar ni mantener
un servidor independiente. El sistema usa el módulo `sqlite3` incluido con
Python.

La ruta se construye en `services/db_service.py` a partir de la carpeta donde
está ese módulo:

```text
BASE_DIR = carpeta SYSTEMFN
DB_PATH  = BASE_DIR + memoriales_altagracia.db
```

Por tanto, el archivo de la instalación actual está en:

```text
C:\laragon\www\sistemvip\SYSTEMFN\memoriales_altagracia.db
```

La aplicación obtiene conexiones mediante `obtener_conexion()`. Cada conexión
activa `PRAGMA foreign_keys = ON`, de modo que SQLite aplique las relaciones y
acciones de borrado declaradas en las claves foráneas. Las consultas de la
aplicación usan parámetros `?` para pasar valores.

Al arrancar, `main.py` llama a `init_db()`. Esta función crea las tablas que no
existen, agrega datos iniciales si las tablas correspondientes están vacías y
ejecuta las migraciones de esquema y de datos antiguos.

### Datos iniciales

Cuando corresponda, la inicialización registra:

- Tres capillas iniciales: San José, La Paz y Santa Teresa.
- Productos iniciales de inventario.
- Una tasa de cambio inicial de `40.0` BS por USD, si aún no existe.
- Si no hay usuarios, la inicialización crea el administrador `admin` con
  contraseña inicial `admin123`.

**Seguridad:** aunque la contraseña inicial se almacena con PBKDF2-HMAC-SHA256
y una sal aleatoria, la clave `admin123` es pública y conocida. Cambie la clave
antes de guardar información real. Las contraseñas SHA-256 heredadas se
actualizan al iniciar sesión correctamente. Si el administrador `admin` aún
tiene un hash heredado, el sistema solicita configurarlo al arrancar.

## 2. Tipos y convenciones de datos

SQLite usa tipos como `TEXT`, `INTEGER` y `REAL` en el esquema:

- `TEXT`: nombres, identificadores, estados, fechas y horas.
- `INTEGER`: identificadores, cantidades y banderas (normalmente `0`/`1`).
- `REAL`: montos y tasas.

Las fechas se guardan principalmente como texto. Las cuotas usan fecha ISO
`AAAA-MM-DD`; algunos campos de fecha y hora pueden almacenar fecha-hora ISO o
texto según el flujo que los creó.

En pagos:

- `pagos.monto` representa el equivalente descontado del contrato en USD.
- `pagos.monto_original` conserva el importe entregado en su moneda original.
- `pagos.moneda` distingue USD de BS.
- `pagos.tasa_cambio` conserva la tasa aplicada al pago en bolívares.
- `pagos.mes_periodo` registra el período o concepto indicado para el pago.

Los importes se redondean a dos decimales en las reglas de negocio. La base no
declara restricciones SQL generales para todos los estados, importes o formatos;
las validaciones se implementan principalmente en los servicios Python.

## 3. Tablas

La estructura vigente define las siguientes tablas:

### `familias`

Responsable o titular de una familia.

- `id`: identificador interno autoincremental.
- `familia_id`: identificador de familia único.
- `resp_cedula`: cédula del responsable, única.
- `resp_nombre`, `resp_apellido`: nombre y apellido del responsable.
- `resp_telefono`, `resp_email`, `resp_direccion`: datos de contacto.
- `fecha_creacion`: fecha de registro.
- `activo`: indicador de actividad.

Una familia puede relacionarse con varios difuntos y contratos.

### `difuntos`

Personas fallecidas vinculadas a una familia.

- `id`: identificador interno.
- `familia_id`: referencia a `familias.familia_id`.
- `cedula`: cédula, única.
- `nombre`, `apellido`, `fecha_nacimiento`, `fecha_defuncion`,
  `causa_muerte`: datos de identidad y registro.

La relación con la familia tiene `ON DELETE CASCADE`: al borrar una familia
SQLite también elimina sus difuntos asociados.

### `contratos`

Registro principal de cada servicio o plan contratado.

- Identificación: `id`, `numero` (único), `fecha_contrato`, `familia_id`,
  `difunto_id`.
- Servicio: `paquete`, `capilla_id`, `fecha_velacion`, `hora_inicio`,
  `hora_fin`, `tipo_velacion`, `tipo_traslado`, `requiere_cremacion`,
  `estado_servicio`, `hora_llegada_real`, `hora_salida_capilla`,
  `fecha_llegada_real`.
- Pago: `monto_total`, `metodo_pago`, `inicial`, `numero_cuotas`, `pagado`,
  `estado`, `tipo_contrato`, `frecuencia_pago`.
- PNF: `pnf_asociado`, `pnf_numero`, `pnf_cubre_traslado`,
  `pnf_cubre_cremacion`, `descuento_pnf`.
- Desglose: `costo_paquete`, `costo_cremacion`, `costo_traslado`,
  `costo_productos`, `costo_servicios`.
- Otros: `observaciones`, `fecha_activacion`, `pdf_ruta`, `titular_edad`.

`familia_id` es obligatorio. `difunto_id`, `capilla_id` y los datos de
velación pueden quedar vacíos, por ejemplo, para un contrato de largo plazo.
El contrato se relaciona con `familias`, `difuntos` y `capillas`.

### `cuotas`

Calendario de cobros de un contrato financiado.

- `id`: identificador de cuota.
- `contrato_id`: contrato al que pertenece.
- `numero`: número secuencial de cuota.
- `monto`: importe de la cuota.
- `fecha_vencimiento`: fecha límite.
- `fecha_pago`: fecha de pago cuando se completa.
- `estado`: por ejemplo, `Pendiente`, `Vencida` o `Pagada`.

La cuota pertenece a un contrato. Su eliminación se propaga al borrar el
contrato (`ON DELETE CASCADE`).

### `pagos`

Movimientos de dinero registrados para un contrato.

- `id`, `contrato_id`, `cuota_id`: identificadores y vínculos.
- `fecha`, `monto`, `metodo`, `referencia`: fecha, equivalente USD, método y
  referencia de pago.
- `moneda`, `tasa_cambio`, `monto_original`: moneda entregada y conversión.
- `mes_periodo`: mes, cuota o concepto que cancela el pago.

El contrato es obligatorio y sus pagos se eliminan si se elimina el contrato.
La cuota asociada es opcional; al borrar esa cuota, `cuota_id` se establece en
`NULL` (`ON DELETE SET NULL`).

### `capillas`

- `id`, `nombre`, `capacidad`, `descripcion`, `estado`, `activo`.
- Estados generales definidos por la aplicación: Disponible, Ocupada y
  Mantenimiento.
- Los contratos pueden apuntar a una capilla; la referencia es opcional en
  contratos de largo plazo.

### `inventario`

Catálogo de productos: `id`, `nombre` (único), `stock`, `precio` y
`stock_minimo`.

### `contrato_productos`

Productos incorporados a un contrato: `id`, `contrato_id`, `producto_id`,
`cantidad` y `precio_unitario`. El registro se elimina al borrar el contrato.
La referencia a `inventario` identifica el producto.

### `contratos_servicios`

Servicios adicionales del contrato: `id`, `contrato_id`, `tipo_velacion`,
`servicio_key`, `servicio_nombre`, `cantidad`, `precio_unitario` y `subtotal`.
Se eliminan al borrar el contrato.

### `contrato_beneficiarios`

Personas beneficiarias asociadas a contratos PNF:
`id`, `contrato_id`, `nombre_completo`, `tipo_documento`, `cedula`, `folio`,
`acta`, `fecha_nacimiento`, `edad` y `parentesco`. Se eliminan al borrar el
contrato.

### `usuarios`

Acceso al sistema: `id`, `usuario` (único), `password` (hash guardado),
`nombre`, `rol`, `activo` y `fecha_creacion`.

### `bitacora`

Eventos del sistema: `id`, `usuario_id`, `accion`, `fecha` y `detalles`.
`usuario_id` puede ser nulo; si se informa, se relaciona con `usuarios`.

### `inventario_movimientos`

Historial de movimientos: `id`, `producto_id`, `producto_nombre`, `tipo`,
`cantidad`, `usuario_id`, `usuario_nombre`, `motivo` y `fecha`.
`producto_id` referencia el producto del inventario.

### `configuracion`

Valores de configuración en formato clave-valor:
`clave` (clave primaria), `valor` y `actualizado`. La tasa USD/BS se guarda con
la clave `tasa_cambio_usd_bs`.

## 4. Relaciones principales

```text
familias (1) ─── (N) difuntos
familias (1) ─── (N) contratos
difuntos (1) ─── (N) contratos       [opcional en el contrato]
capillas (1) ─── (N) contratos       [opcional en el contrato]
contratos (1) ─── (N) cuotas
contratos (1) ─── (N) pagos
cuotas (1) ─── (N) pagos             [opcional en cada pago]
contratos (1) ─── (N) contrato_productos
inventario (1) ─── (N) contrato_productos
contratos (1) ─── (N) contratos_servicios
contratos (1) ─── (N) contrato_beneficiarios
usuarios (1) ─── (N) bitacora
inventario (1) ─── (N) inventario_movimientos
```

`N` significa que un registro principal puede tener varios registros
relacionados. Por ejemplo, un contrato puede tener varias cuotas y pagos.

## 5. Cómo funciona el registro de un contrato y sus pagos

1. Se registra la familia/responsable y, cuando aplica, el difunto.
2. Se crea el contrato con su total, modalidad y demás datos del servicio.
3. En los contratos financiados, la aplicación genera registros en `cuotas`
   con monto y fecha de vencimiento.
4. Al registrar un pago, el sistema guarda un registro en `pagos`. Para pagos
   en BS, convierte el importe a USD con la tasa indicada, conservando también
   el importe y tasa originales.
5. El campo `contratos.pagado` se recalcula a partir de los pagos asociados.
6. Si el pago se vincula a una cuota, el sistema actualiza su estado cuando
   alcanza el importe de esa cuota. El período/concepto se conserva en
   `pagos.mes_periodo` y se muestra en el historial.
7. Las pantallas de reportes y solvencia consultan contratos, cuotas y pagos
   para presentar saldo, períodos registrados y cuotas vencidas.

La información del pago se conserva en el historial. No se debe cambiar
manualmente `contratos.pagado` como sustituto de registrar un pago: el proceso
de migración también calcula ese campo desde la suma de `pagos.monto`.

## 6. Inicialización y migraciones

`init_db()` realiza, en este orden general:

1. Crea las tablas actuales que falten.
2. Agrega datos iniciales cuando corresponde.
3. Ejecuta `migrar_esquema()` para incorporar cambios a bases existentes.
4. Ejecuta `migrar_datos_antiguos()` para importar registros de una tabla
   heredada `clientes`, si esa tabla existe.

Las migraciones actuales pueden agregar columnas faltantes a `contratos`,
agregar `capillas.activo`, incorporar `pagos.monto_original` y
`pagos.mes_periodo`, convertir ciertos pagos antiguos en BS y recalcular
`contratos.pagado`. También completan desglose de costos antiguo y crean la
tabla de beneficiarios si faltaba.

No se declara en el esquema una tabla central de versiones de migración. Por
eso, antes de actualizar la aplicación conviene respaldar la base y comprobar
que el sistema abre correctamente.

## 7. Inspección y mantenimiento

La base se puede inspeccionar con una herramienta compatible con SQLite, por
ejemplo DB Browser for SQLite, o desde Python. Para ver tablas y columnas en
SQLite:

```sql
SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name;

PRAGMA table_info(contratos);
PRAGMA foreign_key_list(pagos);
```

Para comprobar la integridad de la base:

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

Ejecute consultas de inspección antes de cualquier modificación. No elimine
registros ni cambie claves, estados o importes directamente sin entender su
relación con los servicios de la aplicación.

## 8. Copias de seguridad y recuperación

La base contiene información personal, contractual y financiera. Mantenga
copias periódicas, con fecha en el nombre, en una ubicación protegida distinta
de la carpeta de la aplicación. Limite el acceso a la base y a sus respaldos.

El código revisado no muestra un proceso automático de respaldo. Para hacer una
copia manual sencilla:

1. Cierre el sistema para evitar cambios simultáneos durante la copia.
2. Copie `memoriales_altagracia.db` a una ubicación segura.
3. Conserve varias copias históricas y verifique periódicamente que una copia
   pueda abrirse.

Para sistemas que deban respaldarse mientras siguen recibiendo cambios, use la
API de respaldo de SQLite en lugar de copiar únicamente el archivo principal;
SQLite puede utilizar archivos auxiliares de diario mientras está en uso.

Para restaurar, cierre el sistema y reemplace el archivo de la instalación con
una copia verificada. Antes, guarde aparte el archivo que va a reemplazar.

## 9. Límites y consideraciones

- Es una base local en un solo archivo. Si varias computadoras necesitan
  trabajar simultáneamente sobre los mismos datos, no se debe asumir que copiar
  el archivo entre ellas constituye una sincronización segura.
- El código activa claves foráneas en las conexiones creadas por la aplicación;
  otras herramientas pueden requerir que se habiliten explícitamente por
  conexión.
- No se observan índices de aplicación declarados aparte de las claves
  primarias y restricciones únicas del esquema; SQLite crea índices para
  estas últimas automáticamente.
- Las restricciones de negocio, como montos positivos y estados válidos,
  dependen en gran parte de los servicios del programa.
- No se configura cifrado SQLite en el código revisado. Proteja el equipo,
  permisos de archivos y respaldos, especialmente porque contienen datos
  personales.

## 10. Archivos relacionados

- Esquema, conexiones, inicialización, datos iniciales y migraciones:
  `services/db_service.py`.
- Inicio de la aplicación:
  `main.py`.
- Registro y consulta de pagos:
  `services/pago_service.py`.
- Generación de cuotas y cálculos monetarios:
  `services/precio_service.py`.
