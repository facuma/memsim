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
        self.ready_heap: List[Tuple[int, int, int, Process]] = []  # (remaining, tiebreak, pid, Process)
        self.ready_susp: deque = deque()  # FIFO queue for suspended processes
        self.running: Optional[Process] = None
        self.tiebreak_counter: int = 0
    
    def push_ready(self, proc: Process) -> None:
        """
        Inserta un proceso en la cola de listos con prioridad por tiempo restante.
        
        Args:
            proc: Proceso a insertar en la cola de listos.
        """
        # El contador de desempate (tiebreak) asegura un orden FIFO para
        # procesos con el mismo tiempo restante.
        heapq.heappush(self.ready_heap, (proc.remaining, self.tiebreak_counter, proc.pid, proc))
        self.tiebreak_counter += 1
    
    def pop_ready_min(self) -> Optional[Process]:
        """
        Extrae y devuelve el proceso con el menor tiempo restante de la cola de listos.
        
        Returns:
            Proceso con el menor tiempo restante, o None si la cola está vacía.
        """
        if not self.ready_heap:
            return None
        
        _, _, _, process = heapq.heappop(self.ready_heap)
        return process
    
    def peek_ready_min(self) -> Optional[Process]:
        """
        Devuelve el proceso con el menor tiempo restante sin extraerlo de la cola.
        
        Returns:
            Proceso con el menor tiempo restante, o None si la cola está vacía.
        """
        if not self.ready_heap:
            return None
        
        _, _, _, process = self.ready_heap[0]
        return process
    
    def enqueue_suspended(self, proc: Process) -> None:
        """
        Añade un proceso a la cola de listos/suspendidos (FIFO).
        
        Args:
            proc: Proceso a añadir a la cola de suspendidos.
        """
        self.ready_susp.append(proc)
    
    def dequeue_suspended(self) -> Optional[Process]:
        """
        Extrae y devuelve el primer proceso de la cola de suspendidos (FIFO).
        
        Returns:
            El primer proceso en la cola de suspendidos, o None si está vacía.
        """
        if not self.ready_susp:
            return None
        
        return self.ready_susp.popleft()
    
    def preempt_if_needed(self, incoming_min_remaining: int) -> bool:
        """
        Comprueba si el proceso en ejecución actual debe ser desalojado (preempted).
        
        Args:
            incoming_min_remaining: Tiempo restante mínimo de los procesos entrantes.
            
        Returns:
            True si el proceso en ejecución debe ser desalojado, False en caso contrario.
        """
        if self.running is None:
            return False
        
        # Se desaloja si un proceso entrante tiene menor tiempo restante.
        return incoming_min_remaining < self.running.remaining
    
    def count_in_memory(self) -> int:
        """
        Calcula el grado de multiprogramación del sistema.

        Esto incluye procesos en estado Listo (en memoria), Ejecución (en CPU)
        y Listo/Suspendido (en disco, esperando por memoria).
        
        Returns:
            int: Grado de multiprogramación.
        """
        return len(self.ready_heap) + len(self.ready_susp) + (1 if self.running is not None else 0)
