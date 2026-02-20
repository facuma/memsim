"""
Operaciones de Entrada/Salida para la simulación de memoria.

Este módulo gestiona la lectura de datos de procesos desde archivos (CSV),
la escritura de resultados de la simulación y la presentación de datos en un
formato legible.
"""

import csv
from typing import List, Optional
from .models import Process


def leer_procesos_csv(path: str) -> List[Process]:
    """
    Lee los datos de los procesos desde un archivo CSV.
    
    Formato esperado del CSV (con cabecera): pid,size,arrival,burst
    Establece `remaining` igual a `burst` al cargar.
    Devuelve una lista ordenada por tiempo de llegada y luego por PID.
    
    Args:
        path: Ruta al archivo CSV.
        
    Returns:
        Lista de objetos `Process` ordenada por llegada y luego por PID.
    """
    processes = []
    
    try:
        with open(path, 'r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Analiza la fila del CSV
                pid = int(row['pid'])
                size = int(row['size'])
                arrival = int(row['arrival'])
                burst = int(row['burst'])
                
                # Crea el objeto Proceso con remaining=burst
                process = Process(
                    pid=pid,
                    size=size,
                    arrival=arrival,
                    burst=burst,
                    remaining=burst
                )
                processes.append(process)
    
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {path}")
    except KeyError as e:
        raise ValueError(f"Columna requerida faltante en el CSV: {e}")
    except ValueError as e:
        raise ValueError(f"Datos inválidos en el archivo CSV: {e}")
    
    # Ordena por tiempo de llegada, y luego por PID como desempate.
    processes.sort(key=lambda p: (p.arrival, p.pid))
    
    return processes


def pretty_print_estado(
    t: int, 
    running: Optional[Process], 
    mem_table: List[dict], 
    ready: List[Process],
    ready_susp: List[Process],
    arrivals: List[Process] = [],
    structured: bool = False
) -> object:
    """
    Genera una representación del estado actual de la simulación.

    Args:
        t: Tiempo actual de la simulación.
        running: Proceso actualmente en ejecución (None si la CPU está inactiva).
        mem_table: Tabla de memoria con información de las particiones.
        ready: Lista de procesos en la cola de listos.
        ready_susp: Lista de procesos en la cola de listos/suspendidos.
        arrivals: Lista de procesos en la cola de nuevos (llegadas pendientes).
        
    Returns:
        - Si `structured` es False (por defecto), devuelve una cadena de texto formateada.
        - Si `structured` es True, devuelve un diccionario con los datos.
    """
    if structured:
        return {
            "mem_table": mem_table, 
            "ready": ready, 
            "ready_susp": ready_susp,
            "arrivals": arrivals
        }

    # El resto de la función es para la salida de texto (CLI)
    lines = []
    
    # Tiempo y estado de la CPU
    cpu_status = f"pid={running.pid}" if running else "IDLE"
    lines.append(f"t={t} | CPU: {cpu_status}")
    
    # Memory table
    lines.append("Memoria:")
    if mem_table:
        # Header
        lines.append("  id  inicio  tamaño  pid  frag  libre")
        lines.append("  --  ------  ------  ---  ----  -----")
        lines.append("  SO    000   100     ---  ----  -----")
        
        # Filas de datos
        for entry in mem_table:
            pid_str = str(entry['pid']) if entry.get('pid') is not None else "---"
            free_str = "Si" if entry.get('free', True) else "No"
            lines.append(f"  {entry['id']:2}  {entry['start']:5}  {entry['size']:4}  {pid_str:3}  {entry['frag_interna']:4}  {free_str:4}")
    else:
        lines.append("  (no memory partitions)")
    
    # Cola de Nuevos (Arrivals)
    lines.append("Cola Nuevos:")
    if arrivals:
        new_info = []
        for proc in arrivals:
            new_info.append(f"pid={proc.pid}(size={proc.size}, arr={proc.arrival})")
        lines.append(f"  {' '.join(new_info)}")
    else:
        lines.append("  (Vacio)")

    # Cola de listos
    lines.append("Cola Listo:")
    if ready:
        ready_info = []
        for proc in ready:
            ready_info.append(f"pid={proc.pid}(rem={proc.remaining})")
        lines.append(f"  {' '.join(ready_info)}")
    else:
        lines.append("  (Vacio)")
    
    # Cola de listos/suspendidos
    lines.append("Cola Listos/suspendido:")
    if ready_susp:
        susp_info = []
        for proc in ready_susp:
            susp_info.append(f"pid={proc.pid}(size={proc.size})")
        lines.append(f"  {' '.join(susp_info)}")
    else:
        lines.append("  (vacio)")
    
    return "\n".join(lines)
