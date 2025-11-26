"""
Modelos de datos para la simulación de memoria.

Este módulo define las estructuras de datos principales utilizadas en toda la
simulación, incluyendo `Process`, `Partition` y otras entidades esenciales.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class State(Enum):
    """Estados de un proceso en la simulación."""
    NEW = "NEW"
    READY = "READY"
    READY_SUSP = "READY_SUSP"
    RUNNING = "RUNNING"
    TERMINATED = "TERMINATED"


@dataclass
class Process:
    """
    Representa un proceso en la simulación de memoria.
    
    Attributes:
        pid: Identificador del proceso.
        size: Tamaño de memoria requerido por el proceso.
        arrival: Instante de tiempo en que llega el proceso.
        burst: Tiempo de ráfaga de CPU para el proceso.
        remaining: Tiempo de ráfaga restante (por defecto: 0).
        start_time: Tiempo en que el proceso comenzó su ejecución (por defecto: None).
        finish_time: Tiempo en que el proceso finalizó su ejecución (por defecto: None).
        state: Estado actual del proceso (por defecto: State.NEW).
    """
    pid: int
    size: int
    arrival: int
    burst: int
    remaining: int = 0
    start_time: Optional[int] = None
    finish_time: Optional[int] = None
    state: State = State.NEW
    
    def to_row(self) -> dict:
        """
        Convierte el proceso a un diccionario para fines de registro o visualización.
        
        Returns:
            dict: Representación del proceso en formato de diccionario.
        """
        return {
            'pid': self.pid,
            'size': self.size,
            'arrival': self.arrival,
            'burst': self.burst,
            'remaining': self.remaining,
            'start_time': self.start_time,
            'finish_time': self.finish_time,
            'state': self.state.value
        }


@dataclass
class Partition:
    """
    Representa una partición de memoria en el sistema.
    
    Attributes:
        id: Identificador único para la partición.
        start: Dirección de memoria inicial.
        size: Tamaño de la partición.
        pid_assigned: ID del proceso asignado a esta partición (por defecto: None).
    """
    id: str
    start: int
    size: int
    pid_assigned: Optional[int] = None
    
    @property
    def is_free(self) -> bool:
        """
        Comprueba si la partición está libre (no asignada a ningún proceso).
        
        Returns:
            bool: True si la partición está libre, False en caso contrario.
        """
        return self.pid_assigned is None
    
    def frag_interna(self, process_size: int) -> int:
        """
        Calcula la fragmentación interna para un tamaño de proceso dado.
        
        Args:
            process_size: Tamaño del proceso que sería asignado.
            
        Returns:
            int: Fragmentación interna (espacio desperdiciado) si esta partición
                 fuera asignada a un proceso del tamaño especificado.
        """
        if self.is_free:
            return 0
        return max(0, self.size - process_size)


def throughput(finished: int, total_time: int) -> float:
    """
    Calcula el rendimiento (throughput) como procesos completados por unidad de tiempo.
    
    Args:
        finished: Número de procesos que finalizaron su ejecución.
        total_time: Tiempo total de la simulación.
        
    Returns:
        float: Rendimiento (procesos por unidad de tiempo), o 0.0 si el tiempo total es 0.
    """
    if total_time == 0:
        return 0.0
    return finished / total_time
