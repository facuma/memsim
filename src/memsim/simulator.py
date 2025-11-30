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
from .io import pretty_print_estado


class MemorySimulator:
    """
    Motor principal de la simulación de administración de memoria.

    Esta clase coordina toda la simulación, gestionando la interacción entre la
    asignación de memoria, la planificación de procesos y los eventos del
    sistema.
    """
    
    def __init__(self, modo_depuracion: bool = False, nivel_log: str = "INFO"):
        """
        Inicializa el simulador con el administrador de memoria y el planificador.

        Args:
            modo_depuracion: Activa validaciones adicionales de invariantes.
            nivel_log: Nivel de bitácora ("INFO" o "DEBUG").
        """
        self.memory_manager = MemoryManager()
        self.scheduler = Scheduler()
        self.arrivals: List[Process] = []
        self.terminated: List[Process] = []
        self.current_time = 0
        self.max_multiprogramming = 5
        self.modo_depuracion = modo_depuracion
        self.simulation_log: List[str] = []
        self._simulation_complete = False
        self._summary_cache: Optional[Dict] = None
        
        # Configurar logger
        self.logger = logging.getLogger('memsim')
        self.logger.setLevel(getattr(logging, nivel_log.upper()))

        # Crear un handler de consola si aún no existe
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def inicializar(self, processes: List[Process]):
        """Inicializa el estado interno para una nueva ejecución."""
        self.arrivals = sorted(processes, key=lambda p: (p.arrival, p.pid))
        self.terminated = []
        self.current_time = 0
        self.scheduler = Scheduler()
        self.memory_manager = MemoryManager()
        self.simulation_log = []
        self._simulation_complete = False
        self._summary_cache = None

    def ejecutar_simulacion(self, processes: List[Process]) -> Dict:
        """
        Ejecuta la simulación completa de memoria.

        Args:
            processes: Lista de procesos a simular.

        Returns:
            dict: Resultados y métricas de la simulación.
        """
        self.inicializar(processes)

        # Bucle principal de simulación
        while self.paso() is not None:
            pass

        return self.finalizar()

    def esta_completa(self) -> bool:
        """Devuelve True cuando no quedan ticks por ejecutar."""
        if self._simulation_complete:
            return True
        return not self._tiene_procesos_pendientes()

    def paso(self) -> Optional[Dict[str, object]]:
        """Ejecuta un único tick de la simulación.

        Returns:
            Optional[Dict[str, object]]: Información del tick ejecutado o None
            si la simulación ya finalizó.
        """
        if self._simulation_complete:
            return None

        if not self._tiene_procesos_pendientes():
            self._simulation_complete = True
            return None

        eventos_registrados = False
        evento_clave = False  # Bandera para eventos de la consigna (llegada/terminación)

        # 1) Llegadas en el tiempo actual
        if self._manejar_llegadas():
            eventos_registrados = True
            evento_clave = True

        # 2) Planificación SRTF
        if self._planificar_srtf():
            eventos_registrados = True

        # 3) Ejecutar un tick
        if self._ejecutar_tick():
            eventos_registrados = True

        # 4) Manejar terminaciones
        if self._manejar_terminacion():
            eventos_registrados = True
            evento_clave = True

        # 5) Manejar desuspensiones
        if self._manejar_desuspension():
            eventos_registrados = True

        # 6) Validar invariantes (modo debug)
        self._validar_invariantes()

        # 7) Capturar instantánea del estado para bitácora
        state_snapshot_text = self._recolectar_snapshot_estado(structured=False)
        state_snapshot_data = self._recolectar_snapshot_estado(structured=True)
        self.simulation_log.append(state_snapshot_data)

        tick_info: Dict[str, object] = {
            'time': self.current_time,
            'snapshot': state_snapshot_text, # Para CLI
            'snapshot_data': state_snapshot_data, # Para GUI
            'running_pid': self.scheduler.running.pid if self.scheduler.running else None,
            'ready_count': len(self.scheduler.cola_listos),
            'suspended_count': len(self.scheduler.cola_suspendidos),
            'degree_of_multiprogramming': self.scheduler.contar_en_memoria(),
            'evento': eventos_registrados,
            'evento_clave': evento_clave, # Añadimos la nueva bandera al resultado del tick
        }

        # 8) Incrementar tiempo
        self.current_time += 1

        return tick_info

    def paso_hasta_evento(self) -> Optional[Dict[str, object]]:
        """Avanza la simulación hasta el siguiente tick con actividad relevante."""
        if self._simulation_complete:
            return None

        ticks_ejecutados = 0
        resultado_final: Optional[Dict[str, object]] = None

        while True:
            info_tick = self.paso()
            if info_tick is None:
                return resultado_final

            ticks_ejecutados += 1
            resultado_final = info_tick

            if info_tick.get('evento_clave', False):
                resultado_final = dict(info_tick)
                resultado_final['ticks_agregados'] = ticks_ejecutados
                return resultado_final

    def finalizar(self) -> Dict:
        """Finaliza la simulación y devuelve las métricas de resumen."""
        if not self._simulation_complete and self._tiene_procesos_pendientes():
            while self.paso() is not None:
                pass

        if not self._simulation_complete and not self._tiene_procesos_pendientes():
            self._simulation_complete = True

        if self._summary_cache is None:
            summary = self._calcular_metricas()
            summary['simulation_log'] = self.simulation_log
            # Llamada a la función de exportación deshabilitada por solicitud.
            # self._exportar_reporte_csv(summary)
            self._summary_cache = summary

        return self._summary_cache
    
    def _tiene_procesos_pendientes(self) -> bool:
        """Verifica si aún quedan procesos por atender en el sistema."""
        # Si hay procesos en llegadas, listos o en ejecución, la simulación no ha terminado.
        if (len(self.arrivals) > 0 or
            len(self.scheduler.cola_listos) > 0 or
            self.scheduler.running is not None):
            return True

        # Caso especial: solo quedan procesos en la cola de suspendidos.
        # Si ninguno de ellos puede ser admitido en memoria, la simulación ha terminado
        # de facto, para evitar un bucle infinito.
        if len(self.scheduler.cola_suspendidos) > 0:
            # Buscar si al menos un proceso suspendido podría caber en alguna partición libre.
            for proc in self.scheduler.cola_suspendidos:
                # Usamos una llamada hipotética a mejor_ajuste. Si devuelve una partición,
                # significa que hay esperanza y la simulación debe continuar.
                if self.memory_manager.mejor_ajuste(proc.size) is not None:
                    return True  # Hay al menos un proceso que podría entrar.
            
            # Si el bucle termina, significa que ningún proceso suspendido cabe. Es un deadlock.
            return False

        return False # No hay procesos en ninguna cola.
    
    def _manejar_llegadas(self) -> bool:
        """Gestiona la llegada de procesos en el instante de tiempo actual."""
        eventos = False
        arriving_processes = []
        
        # Buscar procesos que llegan en el tiempo actual
        while self.arrivals and self.arrivals[0].arrival == self.current_time:
            arriving_processes.append(self.arrivals.pop(0))

        # Intentar admitir cada proceso entrante
        for process in arriving_processes:
            # Comprueba si el grado de multiprogramación no ha alcanzado el límite
            if self.scheduler.contar_en_memoria() < self.max_multiprogramming:
                partition = self.memory_manager.mejor_ajuste(process.size)
                if partition is not None:
                    # Admite el proceso si se encontró una partición
                    self.memory_manager.asignar(partition, process.pid)
                    if process.remaining <= 0:
                        process.remaining = process.burst
                    process.state = State.READY
                    self.scheduler.insertar_en_listos(process)
                    eventos = True
                else:
                    # No hay partición, se suspende
                    process.state = State.READY_SUSP
                    self.scheduler.encolar_en_suspendidos(process)
                    eventos = True
            else:
                # Límite de multiprogramación alcanzado, se suspende
                self.scheduler.encolar_en_suspendidos(process)
                eventos = True
                self.logger.debug(f"Proceso {process.pid} suspendido - memoria llena (grado={self.scheduler.contar_en_memoria()})")

        return eventos

    def _planificar_srtf(self) -> bool:
        """Gestiona la planificación SRTF con desalojo."""
        hubo_cambio = False
        if self.scheduler.running is None:
            if self.scheduler.cola_listos:
                process = self.scheduler.extraer_min_de_listos()
                self.scheduler.running = process
                if process.start_time is None:
                    process.start_time = self.current_time
                process.state = State.RUNNING
                hubo_cambio = True
        else:
            if self.scheduler.cola_listos:
                min_ready = self.scheduler.ver_min_de_listos()
                if min_ready.remaining < self.scheduler.running.remaining:
                    preempted = self.scheduler.running
                    self.scheduler.running = None
                    preempted.state = State.READY
                    self.scheduler.insertar_en_listos(preempted)
                    new_process = self.scheduler.extraer_min_de_listos()
                    self.scheduler.running = new_process
                    if new_process.start_time is None:
                        new_process.start_time = self.current_time
                    new_process.state = State.RUNNING
                    hubo_cambio = True

        return hubo_cambio

    def _ejecutar_tick(self) -> bool:
        """Ejecuta un intervalo de tiempo para el proceso en la CPU."""
        if self.scheduler.running is not None:
            self.scheduler.running.remaining = max(0, self.scheduler.running.remaining - 1)
            return True
        return False

    def _manejar_terminacion(self) -> bool:
        """Gestiona la terminación de procesos."""
        if (self.scheduler.running is not None and
            self.scheduler.running.remaining <= 0):
            # Proceso finalizado
            finished_process = self.scheduler.running
            finished_process.finish_time = self.current_time + 1
            finished_process.state = State.TERMINATED

            # Liberar partición de memoria
            self.memory_manager.liberar(finished_process.pid)
            self.logger.debug(f"Proceso {finished_process.pid} terminado, partición liberada")

            # Mover a la lista de terminados
            self.terminated.append(finished_process)
            self.scheduler.running = None
            return True

        return False

    def _manejar_desuspension(self) -> bool:
        """Gestiona la desuspensión de procesos suspendidos."""
        hubo_cambio = False
        
        # Se itera sobre una copia de la cola para evitar bucles infinitos.
        # Se evalúan todos los procesos suspendidos en cada tick.
        procesos_a_revisar = len(self.scheduler.cola_suspendidos)
        for _ in range(procesos_a_revisar):
            if not (self.scheduler.cola_suspendidos and self.scheduler.contar_en_memoria() < self.max_multiprogramming):
                break # No hay más que hacer

            # Tomar el primero de la cola para evaluarlo
            process = self.scheduler.desencolar_de_suspendidos()

            # Intentar asignar memoria con Best-Fit
            partition = self.memory_manager.mejor_ajuste(process.size)
            if partition is not None:
                # ¡Éxito! El proceso entra a memoria.
                self.memory_manager.asignar(partition, process.pid)
                if process.remaining <= 0:
                    process.remaining = process.burst
                process.state = State.READY
                self.scheduler.insertar_en_listos(process)
                hubo_cambio = True
            else:
                # No cabe. Se devuelve al final de la cola para intentarlo en un futuro tick.
                self.scheduler.encolar_en_suspendidos(process)

        return hubo_cambio
    
    def obtener_snapshot_actual(self, structured: bool = False) -> object:
        """
        Devuelve una instantánea del estado actual de la simulación.

        Este es un método público seguro para ser consumido por la GUI u otros
        componentes externos.

        Args:
            structured: Si es True, devuelve un diccionario; de lo contrario, una cadena.

        Returns:
            La representación del estado actual.
        """
        return self._recolectar_snapshot_estado(structured=structured)

    def _recolectar_snapshot_estado(self, structured: bool = False) -> object:
        """Recopila una instantánea del estado actual para la bitácora."""
        # Tabla de memoria
        process_sizes = {p.pid: p.size for p in self.terminated}
        if self.scheduler.running:
            process_sizes[self.scheduler.running.pid] = self.scheduler.running.size

        # Agregar procesos listos
        for _, _, _, process in self.scheduler.cola_listos:
            process_sizes[process.pid] = process.size

        mem_table = self.memory_manager.snapshot_tabla(process_sizes)

        # Listado de procesos listos
        ready_processes = [process for _, _, _, process in self.scheduler.cola_listos]

        # Listado de procesos suspendidos
        suspended_processes = list(self.scheduler.cola_suspendidos)
        
        return pretty_print_estado(
            self.current_time,
            self.scheduler.running,
            mem_table,
            ready_processes,
            suspended_processes,
            structured=structured
        )
    
    def _calcular_metricas(self) -> Dict:
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
    
    def _validar_invariantes(self):
        """
        Valida las invariantes de la simulación en modo debug.

        Raises:
            AssertionError: Si alguna invariante es violada.
        """
        if not self.modo_depuracion:
            return

        # Invariante 1: Grado de multiprogramación <= 5
        current_count = self.scheduler.contar_en_memoria()
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
        for _, _, _, process in self.scheduler.cola_listos:
            assert process.pid not in all_processes, f"Proceso {process.pid} encontrado en múltiples estructuras (listos)"
            all_processes.add(process.pid)

        # Revisar cola de suspendidos
        for process in self.scheduler.cola_suspendidos:
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

    def _exportar_reporte_csv(self, summary: Dict):
        """
        Exporta las métricas de la simulación a un archivo CSV.

        Args:
            summary: Diccionario con los resultados de la simulación.
        """
        # --- FUNCIONALIDAD DESHABILITADA POR SOLICITUD ---
        # # Determinar el directorio de salida de forma segura.
        # # Esto es crucial para que funcione correctamente cuando se compila en un .exe.
        # # sys.executable apunta al .exe, y sys._MEIPASS a la carpeta temporal de PyInstaller.
        # import sys
        # if getattr(sys, 'frozen', False):
        #     # Estamos en un entorno compilado (.exe)
        #     output_dir = os.path.dirname(sys.executable)
        # else:
        #     # Estamos en un entorno de desarrollo normal
        #     output_dir = os.getcwd()

        # csv_path = os.path.join(output_dir, "simulation_report.csv")

        # try:
        #     with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        #         writer = csv.writer(csvfile)

        #         self.logger.info(f"Exportando reporte a: {csv_path}")

        #         # Escribir encabezado
        #         writer.writerow([
        #             'pid', 'arrival', 'burst', 'start_time', 'finish_time',
        #             'turnaround', 'wait', 'size'
        #         ])

        #         # Escribir datos de procesos
        #         for process_metrics in summary['processes']:
        #             writer.writerow([
        #                 process_metrics['pid'],
        #                 process_metrics['arrival'],
        #                 process_metrics['burst'],
        #                 process_metrics['start_time'],
        #                 process_metrics['finish_time'],
        #                 process_metrics['turnaround'],
        #                 process_metrics['wait'],
        #                 process_metrics.get('size', 'N/A')
        #             ])

        #         # Escribir resumen
        #         writer.writerow([])  # Fila vacía
        #         writer.writerow(['RESUMEN / SUMMARY', '', '', '', '', '', '', ''])
        #         writer.writerow(['avg_turnaround', summary['avg_turnaround'], 'promedio_turnaround'])
        #         writer.writerow(['avg_wait', summary['avg_wait'], 'promedio_espera'])
        #         writer.writerow(['throughput', summary['throughput'], 'procesos/unidad'])
        #         writer.writerow(['tiempo_total', summary['tiempo_total'], 'duración_simulación'])

        # except Exception as e:
        #     # No fallar la simulación si la exportación falla
        #     self.logger.error(f"Error al exportar el reporte CSV a '{csv_path}': {e}", exc_info=True)
        pass


def ejecutar_simulacion_completa(config, processes):
    """
    Ejecuta la simulación completa de memoria.

    Args:
        config: Objeto SimulationConfig con parámetros de simulación.
        processes: Lista de procesos a simular.

    Returns:
        dict: Resultados y métricas de la simulación.
    """
    simulator = MemorySimulator()
    return simulator.ejecutar_simulacion(processes)
