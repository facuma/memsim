"""
Algoritmos y gestión de la planificación de procesos.

Este módulo implementa la lógica del planificador de CPU, incluyendo la gestión
de las colas de procesos (listos, suspendidos) y la selección del siguiente
proceso a ejecutar bajo un esquema SRTF (Shortest Remaining Time First).
"""

import heapq
from collections import deque
from typing import Optional, List, Tuple
from .models import Process


class Scheduler:
    """
    Gestiona la planificación de procesos usando colas de prioridad y colas FIFO.
    
    Utiliza `heapq` para la cola de listos (prioridad por tiempo restante) y
    `collections.deque` para la cola de suspendidos (FIFO). Implementa la
    planificación apropiativa basada en el tiempo de ráfaga restante.
    """
    
    def __init__(self):
        """Inicializa el planificador con las colas vacías."""
        self.cola_listos: List[Tuple[int, int, int, Process]] = []
        self.cola_suspendidos: deque = deque()  # Cola FIFO para procesos suspendidos
        self.running: Optional[Process] = None
        self.tiebreak_counter: int = 0
    
    def insertar_en_listos(self, proc: Process) -> None:
        """
        Inserta un proceso en la cola de listos con prioridad por tiempo restante.
        
        Args:
            proc: Proceso a insertar en la cola de listos.
        """
        # El contador de desempate (tiebreak) asegura un orden FIFO para
        # procesos con el mismo tiempo restante.
        heapq.heappush(self.cola_listos, (proc.remaining, self.tiebreak_counter, proc.pid, proc))
        self.tiebreak_counter += 1
    
    def extraer_min_de_listos(self) -> Optional[Process]:
        """
        Extrae y devuelve el proceso con el menor tiempo restante de la cola de listos.
        
        Returns:
            Proceso con el menor tiempo restante, o None si la cola está vacía.
        """
        if not self.cola_listos:
            return None
        
        _, _, _, process = heapq.heappop(self.cola_listos)
        return process
    
    def ver_min_de_listos(self) -> Optional[Process]:
        """
        Devuelve el proceso con el menor tiempo restante sin extraerlo de la cola.
        
        Returns:
            Proceso con el menor tiempo restante, o None si la cola está vacía.
        """
        if not self.cola_listos:
            return None
        
        _, _, _, process = self.cola_listos[0]
        return process
    
    def encolar_en_suspendidos(self, proc: Process) -> None:
        """
        Añade un proceso a la cola de listos/suspendidos (FIFO).
        
        Args:
            proc: Proceso a añadir a la cola de suspendidos.
        """
        self.cola_suspendidos.append(proc)
    
    def desencolar_de_suspendidos(self) -> Optional[Process]:
        """
        Extrae y devuelve el primer proceso de la cola de suspendidos (FIFO).
        
        Returns:
            El primer proceso en la cola de suspendidos, o None si está vacía.
        """
        if not self.cola_suspendidos:
            return None
        
        return self.cola_suspendidos.popleft()
    
    def contar_en_memoria(self) -> int:
        """
        Calcula el grado de multiprogramación del sistema.

        Esto incluye procesos en estado Listo (en memoria), Ejecución (en CPU)
        y Listo/Suspendido (en disco, pero contando para el límite del sistema).
        
        Returns:
            int: Grado de multiprogramación.
        """
        en_memoria_y_cpu = len(self.cola_listos) + (1 if self.running is not None else 0)
        en_disco = len(self.cola_suspendidos)
        return en_memoria_y_cpu + en_disco
