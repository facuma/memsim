"""
Operaciones y algoritmos de gestión de memoria.

Este módulo implementa la estrategia de asignación de memoria Best-Fit sobre
un esquema de particionamiento fijo. También se encarga de la liberación de
memoria y del cálculo de la fragmentación interna para la visualización
del estado.
"""

from typing import Optional, Dict, List
from .models import Partition


class MemoryManager:
    """
    Gestiona la asignación y liberación de memoria usando particionamiento fijo.
    
    This class manages three partitions (excluding OS reserved space):
    - P1: start=100, size=250
    - P2: start=350, size=150  
    - P3: start=500, size=50
    
    Invariant: Each partition contains 0 or 1 process; OS 100K is reserved and outside these partitions.
    Invariante: Cada partición contiene 0 o 1 proceso. El S.O. ocupa 100K que están fuera de estas particiones.
    """
    
    def __init__(self):
        """Inicializa el gestor de memoria con tres particiones fijas."""
        self.partitions = [
            Partition(id="P1", start=100, size=250),
            Partition(id="P2", start=350, size=150),
            Partition(id="P3", start=500, size=50)
        ]
    
    def best_fit(self, size: int) -> Optional[Partition]:
        """
        Encuentra la partición libre más pequeña que pueda alojar el tamaño dado.
        
        Args:
            size: Tamaño de memoria requerido por el proceso.
            
        Returns:
            La partición más pequeña y adecuada. Devuelve None si ninguna partición
            libre es lo suficientemente grande.
        """
        free_partitions = [p for p in self.partitions if p.is_free]
        suitable_partitions = [p for p in free_partitions if p.size >= size]

        if suitable_partitions:
            # Devuelve la partición con el menor tamaño entre las adecuadas.
            return min(suitable_partitions, key=lambda p: p.size)

        if free_partitions and len(free_partitions) < len(self.partitions):
            # Todas las particiones libres son demasiado pequeñas, pero algo de memoria
            # está ocupada. Se podría devolver la más grande de las libres para que
            # el llamador decida (ej. suspender), pero para Best-Fit estricto,
            # si no cabe, no hay candidato.
            return max(free_partitions, key=lambda p: p.size)

        return None
    
    def assign(self, part: Partition, pid: int) -> None:
        """
        Asigna una partición a un proceso.
        
        Args:
            part: La partición a asignar.
            pid: ID del proceso a asignar a la partición.
        """
        part.pid_assigned = pid
    
    def release(self, pid: int) -> None:
        """
        Libera la partición asignada al ID de proceso dado.
        
        Args:
            pid: ID del proceso cuya partición debe ser liberada.
        """
        for partition in self.partitions:
            if partition.pid_assigned == pid:
                partition.pid_assigned = None
                break
    
    def table_snapshot(self, process_sizes: Dict[int, int]) -> List[Dict]:
        """
        Genera una instantánea de la tabla de memoria para su visualización.
        
        Args:
            process_sizes: Diccionario que mapea IDs de procesos a sus tamaños.
            
        Returns:
            Lista de diccionarios con información de cada partición, incluyendo
            las claves: {id, start, size, pid, frag_interna}.
        """
        snapshot = []
        
        for partition in self.partitions:
            pid = partition.pid_assigned
            frag_interna = 0
            
            if pid is not None and pid in process_sizes:
                # Calcula la fragmentación interna, asegurando que no sea negativa.
                frag_interna = partition.frag_interna(process_sizes[pid])
            elif pid is not None:
                # Si no se encuentra el tamaño del proceso, se asume sin fragmentación.
                frag_interna = 0
            
            snapshot.append({
                'id': partition.id,
                'start': partition.start,
                'size': partition.size,
                'pid': pid,
                'frag_interna': frag_interna,
                'free': partition.is_free
            })
        
        return snapshot
