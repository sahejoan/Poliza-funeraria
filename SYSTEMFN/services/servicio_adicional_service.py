# services/servicio_adicional_service.py - Servicios adicionales para contratos
import sqlite3
from typing import List, Dict, Optional
from services.db_service import obtener_conexion

class ServicioAdicionalService:
    """Servicio para gestión de servicios adicionales en contratos"""
    
    # Servicios disponibles para velación en funeraria
    SERVICIOS_FUNERARIA = {
        "desayuno": {"nombre": "Desayuno (por persona)", "precio": 8.00},
        "almuerzo": {"nombre": "Almuerzo (por persona)", "precio": 15.00},
        "cena": {"nombre": "Cena (por persona)", "precio": 12.00},
        "hospedaje": {"nombre": "Hospedaje (2 familiares, 1 noche)", "precio": 80.00},
        "cafeteria": {"nombre": "Servicio de cafetería (24h)", "precio": 45.00}
    }
    
    # Servicios disponibles para velación a domicilio
    SERVICIOS_DOMICILIO = {
        "traslado_cuerpo": {"nombre": "Traslado del cuerpo (desde/hasta)", "precio": 150.00},
        "sillas": {"nombre": "Sillas plásticas (por unidad)", "precio": 2.50},
        "carpa": {"nombre": "Carpa (4x4 metros)", "precio": 120.00},
        "mesa_honor": {"nombre": "Mesa de honor con mantelería", "precio": 45.00},
        "sonido": {"nombre": "Equipo de sonido básico", "precio": 60.00},
        "generador": {"nombre": "Generador eléctrico", "precio": 90.00}
    }
    
    @staticmethod
    def crear_tabla_servicios():
        """Crea la tabla de servicios adicionales si no existe"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contratos_servicios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contrato_id INTEGER NOT NULL,
                tipo_velacion TEXT NOT NULL,
                servicio_key TEXT NOT NULL,
                servicio_nombre TEXT NOT NULL,
                cantidad INTEGER DEFAULT 1,
                precio_unitario REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY (contrato_id) REFERENCES contratos(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        conn.close()
    
    @staticmethod
    def agregar_servicio_funeraria(contrato_id: int, servicio_key: str, cantidad: int = 1) -> bool:
        """Agrega un servicio de velación en funeraria al contrato"""
        if servicio_key not in ServicioAdicionalService.SERVICIOS_FUNERARIA:
            return False
        
        servicio = ServicioAdicionalService.SERVICIOS_FUNERARIA[servicio_key]
        subtotal = servicio["precio"] * cantidad
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO contratos_servicios 
                (contrato_id, tipo_velacion, servicio_key, servicio_nombre, cantidad, precio_unitario, subtotal)
                VALUES (?, 'funeraria', ?, ?, ?, ?, ?)
            """, (contrato_id, servicio_key, servicio["nombre"], cantidad, servicio["precio"], subtotal))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error agregando servicio: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def agregar_servicio_domicilio(contrato_id: int, servicio_key: str, cantidad: int = 1) -> bool:
        """Agrega un servicio de velación a domicilio al contrato"""
        if servicio_key not in ServicioAdicionalService.SERVICIOS_DOMICILIO:
            return False
        
        servicio = ServicioAdicionalService.SERVICIOS_DOMICILIO[servicio_key]
        subtotal = servicio["precio"] * cantidad
        
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO contratos_servicios 
                (contrato_id, tipo_velacion, servicio_key, servicio_nombre, cantidad, precio_unitario, subtotal)
                VALUES (?, 'domicilio', ?, ?, ?, ?, ?)
            """, (contrato_id, servicio_key, servicio["nombre"], cantidad, servicio["precio"], subtotal))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error agregando servicio: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def obtener_servicios_contrato(contrato_id: int) -> List[Dict]:
        """Obtiene todos los servicios adicionales de un contrato"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tipo_velacion, servicio_key, servicio_nombre, cantidad, precio_unitario, subtotal
            FROM contratos_servicios
            WHERE contrato_id = ?
            ORDER BY tipo_velacion, servicio_nombre
        """, (contrato_id,))
        
        servicios = []
        for row in cursor.fetchall():
            servicios.append({
                'id': row[0],
                'tipo_velacion': row[1],
                'servicio_key': row[2],
                'servicio_nombre': row[3],
                'cantidad': row[4],
                'precio_unitario': row[5],
                'subtotal': row[6]
            })
        conn.close()
        return servicios
    
    @staticmethod
    def eliminar_servicio(servicio_id: int) -> bool:
        """Elimina un servicio adicional del contrato"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM contratos_servicios WHERE id = ?", (servicio_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error eliminando servicio: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def calcular_total_servicios(contrato_id: int) -> float:
        """Calcula el total de todos los servicios adicionales de un contrato"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(subtotal) FROM contratos_servicios WHERE contrato_id = ?", (contrato_id,))
        total = cursor.fetchone()[0] or 0.0
        conn.close()
        return total
    
    @staticmethod
    def obtener_tipos_velacion() -> List[str]:
        """Retorna los tipos de velación disponibles"""
        return ["Funeraria", "Domicilio"]