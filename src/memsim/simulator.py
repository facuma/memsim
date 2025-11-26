"""
Motor principal de la simulación y coordinación de componentes.

Este módulo orquesta la simulación de memoria coordinando la gestión de
memoria, la planificación de procesos y la visualización del estado.
"""

import csv
import logging
import os
from typing import List, Dict, Optional, Tuple
from .models import Process, State, throughput
from .memory import MemoryManager
from .scheduler import Scheduler
from .io import pretty_print_state


class MemorySimulator:
    """
    Motor principal de la simulación de administración de memoria.

    Esta clase coordina toda la simulación, gestionando la interacción entre la
    asignación de memoria, la planificación de procesos y los eventos del
    sistema.
    """
    
    def __init__(self, debug_mode: bool = False, log_level: str = "INFO"):
        """
        Inicializa el simulador con el administrador de memoria y el planificador.

        Args:
            debug_mode: Activa validaciones adicionales de invariantes.
            log_level: Nivel de bitácora ("INFO" o "DEBUG").
        """
        self.memory_manager = MemoryManager()
        self.scheduler = Scheduler()
        self.arrivals: List[Process] = []
        self.terminated: List[Process] = []
        self.current_time = 0
        self.max_multiprogramming = 5
        self.debug_mode = debug_mode
        self.simulation_log: List[str] = []
        self._simulation_complete = False
        self._summary_cache: Optional[Dict] = None
        
        # Configurar logger
        self.logger = logging.getLogger('memsim')
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Crear un handler de consola si aún no existe
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def initialize(self, processes: List[Process]):
        """Inicializa el estado interno para una nueva ejecución."""
        self.arrivals = sorted(processes, key=lambda p: (p.arrival, p.pid))
        self.terminated = []
        self.current_time = 0
        self.scheduler = Scheduler()
        self.memory_manager = MemoryManager()
        self.simulation_log = []
        self._simulation_complete = False
        self._summary_cache = None

    def run_simulation(self, processes: List[Process]) -> Dict:
        """
        Ejecuta la simulación completa de memoria.

        Args:
            processes: Lista de procesos a simular.

        Returns:
            dict: Resultados y métricas de la simulación.
        """
        self.initialize(processes)

        # Bucle principal de simulación
        while self.step() is not None:
            pass

        return self.finalize()

    def is_complete(self) -> bool:
        """Devuelve True cuando no quedan ticks por ejecutar."""
        if self._simulation_complete:
            return True
        return not self._has_pending_processes()

    def step(self) -> Optional[Dict[str, object]]:
        """Ejecuta un único tick de la simulación.

        Returns:
            Optional[Dict[str, object]]: Información del tick ejecutado o None
            si la simulación ya finalizó.
        """
        if self._simulation_complete:
            return None

        if not self._has_pending_processes():
            self._simulation_complete = True
            return None

        eventos_registrados = False

        # 1) Llegadas en el tiempo actual
        if self._handle_arrivals():
            eventos_registrados = True

        # 2) Planificación SRTF
        if self._schedule_srtf():
            eventos_registrados = True

        # 3) Ejecutar un tick
        if self._execute_tick():
            eventos_registrados = True

        # 4) Manejar terminaciones
        if self._handle_termination():
            eventos_registrados = True

        # 5) Manejar desuspensiones
        if self._handle_desuspension():
            eventos_registrados = True

        # 6) Validar invariantes (modo debug)
        self._validate_invariants()

        # 7) Capturar instantánea del estado para bitácora
        state_snapshot = self._collect_state_snapshot()
        self.simulation_log.append(state_snapshot)

        tick_info: Dict[str, object] = {
            'time': self.current_time,
            'snapshot': state_snapshot,
            'running_pid': self.scheduler.running.pid if self.scheduler.running else None,
            'ready_count': len(self.scheduler.ready_heap),
            'suspended_count': len(self.scheduler.ready_susp),
            'degree_of_multiprogramming': self.scheduler.count_in_memory(),
            'evento': eventos_registrados,
        }

        # 8) Incrementar tiempo
        self.current_time += 1

        return tick_info

    def step_hasta_evento(self) -> Optional[Dict[str, object]]:
        """Avanza la simulación hasta el siguiente tick con actividad relevante."""
        if self._simulation_complete:
            return None

        ticks_ejecutados = 0
        resultado_final: Optional[Dict[str, object]] = None

        while True:
            info_tick = self.step()
            if info_tick is None:
                return resultado_final

            ticks_ejecutados += 1
            resultado_final = info_tick

            if info_tick.get('evento', False):
                resultado_final = dict(info_tick)
                resultado_final['ticks_agregados'] = ticks_ejecutados
                return resultado_final

    def finalize(self) -> Dict:
        """Finaliza la simulación y devuelve las métricas de resumen."""
        if not self._simulation_complete and self._has_pending_processes():
            while self.step() is not None:
                pass

        if not self._simulation_complete and not self._has_pending_processes():
            self._simulation_complete = True

        if self._summary_cache is None:
            summary = self._calculate_metrics()
            summary['simulation_log'] = self.simulation_log
            self._export_csv_report(summary)
            self._summary_cache = summary

        return self._summary_cache
    
    def _has_pending_processes(self) -> bool:
        """Verifica si aún quedan procesos por atender en el sistema."""
        return (len(self.arrivals) > 0 or 
                len(self.scheduler.ready_heap) > 0 or 
                len(self.scheduler.ready_susp) > 0 or 
                self.scheduler.running is not None)
    
    def _handle_arrivals(self) -> bool:
        """Gestiona la llegada de procesos en el instante de tiempo actual."""
        eventos = False
        arriving_processes = []
        
        # Buscar procesos que llegan en el tiempo actual
        while self.arrivals and self.arrivals[0].arrival == self.current_time:
            arriving_processes.append(self.arrivals.pop(0))

        # Intentar admitir cada proceso entrante
        for process in arriving_processes:
            # Comprueba si el grado de multiprogramación no ha alcanzado el límite
            if self.scheduler.count_in_memory() < self.max_multiprogramming:
                partition = self.memory_manager.best_fit(process.size)
                if partition is not None:
                    # Admite el proceso si se encontró una partición
                    self.memory_manager.assign(partition, process.pid)
                    if process.remaining <= 0:
                        process.remaining = process.burst
                    process.state = State.READY
                    self.scheduler.push_ready(process)
                    eventos = True
                else:
                    # No hay partición, se suspende
                    process.state = State.READY_SUSP
                    self.scheduler.enqueue_suspended(process)
                    eventos = True
            else:
                # Límite de multiprogramación alcanzado, se suspende
                self.scheduler.enqueue_suspended(process)
                eventos = True
                self.logger.debug(f"Proceso {process.pid} suspendido - memoria llena (grado={self.scheduler.count_in_memory()})")

        return eventos

    def _schedule_srtf(self) -> bool:
        """Gestiona la planificación SRTF con desalojo."""
        hubo_cambio = False
        if self.scheduler.running is None:
            if self.scheduler.ready_heap:
                process = self.scheduler.pop_ready_min()
                self.scheduler.running = process
                if process.start_time is None:
                    process.start_time = self.current_time
                process.state = State.RUNNING
                hubo_cambio = True
        else:
            if self.scheduler.ready_heap:
                min_ready = self.scheduler.peek_ready_min()
                if min_ready.remaining < self.scheduler.running.remaining:
                    preempted = self.scheduler.running
                    self.scheduler.running = None
                    preempted.state = State.READY
                    self.scheduler.push_ready(preempted)
                    new_process = self.scheduler.pop_ready_min()
                    self.scheduler.running = new_process
                    if new_process.start_time is None:
                        new_process.start_time = self.current_time
                    new_process.state = State.RUNNING
                    hubo_cambio = True

        return hubo_cambio

    def _execute_tick(self) -> bool:
        """Ejecuta un intervalo de tiempo para el proceso en la CPU."""
        if self.scheduler.running is not None:
            self.scheduler.running.remaining = max(0, self.scheduler.running.remaining - 1)
            return True
        return False

    def _handle_termination(self) -> bool:
        """Gestiona la terminación de procesos."""
        if (self.scheduler.running is not None and
            self.scheduler.running.remaining <= 0):
            # Proceso finalizado
            finished_process = self.scheduler.running
            finished_process.finish_time = self.current_time + 1
            finished_process.state = State.TERMINATED

            # Liberar partición de memoria
            self.memory_manager.release(finished_process.pid)
            self.logger.debug(f"Proceso {finished_process.pid} terminado, partición liberada")

            # Mover a la lista de terminados
            self.terminated.append(finished_process)
            self.scheduler.running = None
            return True

        return False

    def _handle_desuspension(self) -> bool:
        """Gestiona la desuspensión de procesos suspendidos."""
        hubo_cambio = False
        while (self.scheduler.ready_susp and
               self.scheduler.count_in_memory() < self.max_multiprogramming):
            # Tomar el primero de la cola de suspendidos
            process = self.scheduler.dequeue_suspended()

            # Intentar asignar memoria con Best-Fit
            partition = self.memory_manager.best_fit(process.size)
            if partition is not None:
                self.memory_manager.assign(partition, process.pid)
                if process.remaining <= 0:
                    process.remaining = process.burst
                process.state = State.READY
                self.scheduler.push_ready(process)
                hubo_cambio = True
            else:
                self.scheduler.ready_susp.appendleft(process)
                break

        return hubo_cambio
    
    def _collect_state_snapshot(self) -> str:
        """Recopila una instantánea del estado actual para la bitácora."""
        # Tabla de memoria
        process_sizes = {p.pid: p.size for p in self.terminated}
        if self.scheduler.running:
            process_sizes[self.scheduler.running.pid] = self.scheduler.running.size

        # Agregar procesos listos
        for _, _, _, process in self.scheduler.ready_heap:
            process_sizes[process.pid] = process.size

        mem_table = self.memory_manager.table_snapshot(process_sizes)

        # Listado de procesos listos
        ready_processes = [process for _, _, _, process in self.scheduler.ready_heap]

        # Listado de procesos suspendidos
        suspended_processes = list(self.scheduler.ready_susp)
        
        return pretty_print_state(
            self.current_time,
            self.scheduler.running,
            mem_table,
            ready_processes,
            suspended_processes
        )
    
    def _calculate_metrics(self) -> Dict:
        """Calcula las métricas finales de la simulación."""
        if not self.terminated:
            return {
                'processes': [],
                'avg_turnaround': 0.0,
                'avg_wait': 0.0,
                'throughput': 0.0,
                'tiempo_total': self.current_time
            }
        
        # Calcular métricas por proceso
        process_metrics = []
        total_turnaround = 0
        total_wait = 0

        for process in self.terminated:
            # Cálculos precisos
            turnaround = process.finish_time - process.arrival
            wait = turnaround - process.burst
            
            process_metrics.append({
                'pid': process.pid,
                'turnaround': turnaround,
                'wait': wait,
                'arrival': process.arrival,
                'burst': process.burst,
                'start_time': process.start_time,
                'finish_time': process.finish_time,
                'size': process.size
            })
            
            total_turnaround += turnaround
            total_wait += wait
        
        # Calcular promedios
        num_processes = len(self.terminated)
        avg_turnaround = total_turnaround / num_processes if num_processes > 0 else 0.0
        avg_wait = total_wait / num_processes if num_processes > 0 else 0.0

        # Cálculo defensivo del throughput
        if self.current_time == 0:
            throughput_value = 0.0
        else:
            throughput_value = num_processes / self.current_time
        
        return {
            'processes': process_metrics,
            'avg_turnaround': avg_turnaround,
            'avg_wait': avg_wait,
            'throughput': throughput_value,
            'tiempo_total': self.current_time
        }
    
    def _validate_invariants(self):
        """
        Valida las invariantes de la simulación en modo debug.

        Raises:
            AssertionError: Si alguna invariante es violada.
        """
        if not self.debug_mode:
            return

        # Invariante 1: Grado de multiprogramación <= 5
        current_count = self.scheduler.count_in_memory()
        assert current_count <= 5, f"Se excedió el grado de multiprogramación: {current_count} > 5"

        # Invariante 2: No hay PIDs duplicados en particiones
        assigned_pids = set()
        for partition in self.memory_manager.partitions:
            if partition.pid_assigned is not None:
                assert partition.pid_assigned not in assigned_pids, f"PID duplicado {partition.pid_assigned} en particiones"
                assigned_pids.add(partition.pid_assigned)

        # Invariante 3: Cada proceso está en exactamente una estructura
        all_processes = set()

        # Revisar llegadas
        for process in self.arrivals:
            assert process.pid not in all_processes, f"Proceso {process.pid} encontrado en múltiples estructuras (llegadas)"
            all_processes.add(process.pid)

        # Revisar cola de listos
        for _, _, _, process in self.scheduler.ready_heap:
            assert process.pid not in all_processes, f"Proceso {process.pid} encontrado en múltiples estructuras (listos)"
            all_processes.add(process.pid)

        # Revisar cola de suspendidos
        for process in self.scheduler.ready_susp:
            assert process.pid not in all_processes, f"Proceso {process.pid} encontrado en múltiples estructuras (suspendidos)"
            all_processes.add(process.pid)

        # Revisar proceso en ejecución
        if self.scheduler.running is not None:
            assert self.scheduler.running.pid not in all_processes, f"Proceso {self.scheduler.running.pid} encontrado en múltiples estructuras (ejecución)"
            all_processes.add(self.scheduler.running.pid)

        # Revisar terminados
        for process in self.terminated:
            assert process.pid not in all_processes, f"Proceso {process.pid} encontrado en múltiples estructuras (terminados)"
            all_processes.add(process.pid)

    def _export_csv_report(self, summary: Dict):
        """
        Exporta las métricas de la simulación a un archivo CSV.

        Args:
            summary: Diccionario con los resultados de la simulación.
        """
        csv_path = os.path.join(os.getcwd(), "simulation_report.csv")

        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Escribir encabezado
                writer.writerow([
                    'pid', 'arrival', 'burst', 'start_time', 'finish_time',
                    'turnaround', 'wait', 'size'
                ])

                # Escribir datos de procesos
                for process_metrics in summary['processes']:
                    writer.writerow([
                        process_metrics['pid'],
                        process_metrics['arrival'],
                        process_metrics['burst'],
                        process_metrics['start_time'],
                        process_metrics['finish_time'],
                        process_metrics['turnaround'],
                        process_metrics['wait'],
                        process_metrics.get('size', 'N/A')
                    ])

                # Escribir resumen
                writer.writerow([])  # Fila vacía
                writer.writerow(['RESUMEN / SUMMARY', '', '', '', '', '', '', ''])
                writer.writerow(['avg_turnaround', summary['avg_turnaround'], 'promedio_turnaround'])
                writer.writerow(['avg_wait', summary['avg_wait'], 'promedio_espera'])
                writer.writerow(['throughput', summary['throughput'], 'procesos/unidad'])
                writer.writerow(['tiempo_total', summary['tiempo_total'], 'duración_simulación'])

        except Exception as e:
            # No fallar la simulación si la exportación falla
            print(f"Advertencia: Error al exportar el reporte CSV: {e}")
            import traceback
            traceback.print_exc()


def run_simulation(config, processes):
    """
    Ejecuta la simulación completa de memoria.

    Args:
        config: Objeto SimulationConfig con parámetros de simulación.
        processes: Lista de procesos a simular.

    Returns:
        dict: Resultados y métricas de la simulación.
    """
    simulator = MemorySimulator()
    return simulator.run_simulation(processes)
