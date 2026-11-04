# services/__init__.py - Inicializador del módulo services
# Este archivo permite importar los servicios desde la carpeta services

from services.db_service import obtener_conexion, init_db, ContratoRepository
from services.cliente_service import ClienteService
from services.contrato_service import ContratoService