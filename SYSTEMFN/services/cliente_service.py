# services/cliente_service.py - Lógica de negocio para familias y difuntos
from services.db_service import FamiliaRepository, obtener_conexion, generar_familia_id
from typing import Optional, List

class ClienteService:
    """Servicio para gestión de familias (responsable + difuntos)"""
    
    @staticmethod
    def buscar_familia_por_cedula(cedula: str) -> Optional[dict]:
        """Busca una familia por cédula del responsable"""
        return FamiliaRepository.buscar_por_cedula(cedula)
    
    @staticmethod
    def registrar_familia(resp_data: dict) -> str:
        """Registra una nueva familia (solo responsable)"""
        return FamiliaRepository.registrar_familia(resp_data)
    
    @staticmethod
    def agregar_difunto_a_familia(familia_id: str, difunto_data: dict) -> int:
        """Agrega un difunto a una familia existente"""
        return FamiliaRepository.agregar_difunto(familia_id, difunto_data)
    
    @staticmethod
    def registrar_familia_con_difunto(resp_data: dict, difunto_data: dict) -> tuple:
        """Registra una nueva familia con su primer difunto"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            familia_id = generar_familia_id()
            
            # Insertar familia
            cursor.execute("""
                INSERT INTO familias (familia_id, resp_cedula, resp_nombre, resp_apellido, 
                                     resp_telefono, resp_email, resp_direccion, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                familia_id,
                resp_data['cedula'],
                resp_data['nombre'],
                resp_data['apellido'],
                resp_data.get('telefono', ''),
                resp_data.get('email', ''),
                resp_data.get('direccion', ''),
                __import__('datetime').datetime.now().isoformat()
            ))
            
            # Insertar difunto
            cursor.execute("""
                INSERT INTO difuntos (familia_id, cedula, nombre, apellido, 
                                     fecha_nacimiento, fecha_defuncion, causa_muerte)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                familia_id,
                difunto_data['cedula'],
                difunto_data['nombre'],
                difunto_data['apellido'],
                difunto_data.get('fecha_nacimiento'),
                difunto_data.get('fecha_defuncion'),
                difunto_data.get('causa_muerte')
            ))
            difunto_id = cursor.lastrowid
            
            conn.commit()
            return (familia_id, difunto_id)
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def listar_todas_familias() -> List[dict]:
        """Lista todas las familias registradas"""
        return FamiliaRepository.listar_todas_familias()
    
    @staticmethod
    def buscar_por_texto(texto: str) -> List[dict]:
        """Búsqueda flexible por cédula o nombre"""
        return FamiliaRepository.buscar_por_texto(texto)
    
    @staticmethod
    def obtener_difuntos_por_familia(familia_id: str) -> List[dict]:
        """Obtiene todos los difuntos de una familia"""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, cedula, nombre, apellido, fecha_nacimiento, fecha_defuncion, causa_muerte
            FROM difuntos 
            WHERE familia_id = ?
            ORDER BY fecha_defuncion DESC
        """, (familia_id,))
        
        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'id': row[0],
                'cedula': row[1],
                'nombre_completo': f"{row[2]} {row[3]}",
                'fecha_defuncion': row[5],
                'causa_muerte': row[6]
            })
        conn.close()
        return resultados