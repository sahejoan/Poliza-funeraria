# models.py - Data classes y enums del sistema funerario
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum


class TipoContrato(Enum):
    INMEDIATO = "Inmediato"
    LARGO_PLAZO = "Largo Plazo"


class TipoTraslado(Enum):
    LOCAL = "Local"
    REGIONAL = "Regional"
    NACIONAL = "Nacional"
    EXTERNO = "Externo"


class EstadoServicio(Enum):
    PENDIENTE = "Pendiente"
    EN_CAPILLA = "En capilla"
    CREMACION = "Cremación"
    FINALIZADO = "Finalizado"
    CANCELADO = "Cancelado"


class EstadoCapilla(Enum):
    DISPONIBLE = "Disponible"
    OCUPADA = "Ocupada"
    MANTENIMIENTO = "Mantenimiento"


@dataclass
class FamiliaDTO:
    """Representa una familia (responsable + todos sus difuntos)"""
    familia_id: str
    resp_cedula: str
    resp_nombre: str
    resp_apellido: str
    resp_telefono: str
    resp_email: str
    resp_direccion: str
    difuntos: List[dict]
    fecha_creacion: str


@dataclass
class DifuntoDTO:
    """Representa un difunto individual"""
    id: Optional[int]
    familia_id: str
    cedula: str
    nombre: str
    apellido: str
    fecha_nacimiento: Optional[str]
    fecha_defuncion: Optional[str]
    causa_muerte: Optional[str]


@dataclass
class ContratoDTO:
    id: Optional[int]
    numero: str
    fecha_contrato: str
    familia_id: str
    difunto_id: Optional[int]
    paquete: str
    capilla_id: Optional[int]
    fecha_velacion: Optional[str]
    hora_inicio: Optional[str]
    hora_fin: Optional[str]
    monto_total: float
    metodo_pago: str
    inicial: float
    numero_cuotas: int
    pagado: float
    estado: str
    tipo_contrato: str
    requiere_cremacion: bool
    tipo_traslado: str
    pnf_asociado: bool
    pnf_numero: Optional[str]
    pnf_cubre_traslado: bool
    pnf_cubre_cremacion: bool
    hora_llegada_real: Optional[str]
    hora_salida_capilla: Optional[str]
    fecha_llegada_real: Optional[str]
    estado_servicio: str
    tipo_velacion: str
    observaciones: Optional[str]
    titular_edad: Optional[int] = None
    frecuencia_pago: Optional[str] = "Mensual"


@dataclass
class BeneficiarioDTO:
    id: Optional[int]
    contrato_id: Optional[int]
    nombre_completo: str
    tipo_documento: str  # 'Cedula' o 'Partida'
    cedula: Optional[str]
    folio: Optional[str]
    acta: Optional[str]
    fecha_nacimiento: str
    edad: int
    parentesco: Optional[str] = ""
