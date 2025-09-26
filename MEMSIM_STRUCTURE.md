# Memsim - Documentación Técnica de la Arquitectura

Este documento describe en detalle la organización interna del paquete `memsim`,
explicando el rol de cada módulo, las librerías que emplea, las estructuras y
algoritmos que implementa, además de ejemplos de uso y notas de evolución.

---

## `src/memsim/__init__.py`

### Descripción general del módulo
Expone la cadena de versión del paquete y sirve como punto de documentación
breve cuando el paquete es importado. No define lógica adicional, pero permite
que otras capas inspeccionen la versión distribuida.

### Librerías utilizadas
- Ninguna más allá de la propia sintaxis de Python. El archivo solo declara la
  constante `__version__`.

### Estructuras de datos principales
- Constante `__version__`: cadena que identifica la versión pública del paquete.

### Algoritmos implementados
- No aplica; es un módulo de metadatos.

### Ejemplos de uso
```python
import memsim

print(memsim.__version__)
```

### Notas y extensiones futuras
- En caso de exponer configuración global (por ejemplo, parámetros por defecto
de simulación), este sería el lugar natural para importarlos bajo un API
controlada.

---

## `src/memsim/__main__.py`

### Descripción general del módulo
Define el punto de entrada cuando el paquete se ejecuta con `python -m memsim`.
Encamina la ejecución hacia la interfaz de línea de comandos (`cli.main`).

### Librerías utilizadas
- Importación relativa de `memsim.cli`. No utiliza librerías externas.

### Estructuras de datos principales
- No define estructuras; únicamente importa y ejecuta una función.

### Algoritmos implementados
- No aplica. El comportamiento se limita a invocar `main()` de la CLI.

### Ejemplos de uso
```bash
python -m memsim --csv examples/processes_example.csv
```

### Notas y extensiones futuras
- Si en el futuro se requieren argumentos especiales solo disponibles al correr
como módulo, este archivo puede convertirse en un pequeño wrapper para
procesarlos antes de llamar a la CLI.

---

## `src/memsim/cli.py`

### Descripción general del módulo
Implementa la interfaz de línea de comandos. Se encarga de:
- Construir y validar argumentos con `argparse`.
- Cargar procesos desde CSV mediante `io.read_processes_csv`.
- Ejecutar la simulación a través de `MemorySimulator`.
- Mostrar bitácoras por tick o por evento, estadísticas por proceso y resúmenes.
- Manejar errores de entrada/salida y excepciones generales.

### Librerías utilizadas
- `argparse`: definición del CLI.
- `sys`: salida de mensajes de error y códigos de retorno.
- Módulos internos: `memsim.simulator.MemorySimulator` y `memsim.io.read_processes_csv`.

### Estructuras de datos principales
- No define nuevas clases; trabaja con listas de diccionarios producidos por el
  simulador y con objetos `Process` obtenidos desde `io.py`.
- Utiliza strings para bitácoras y banderas booleanas para controlar cabeceras.

### Algoritmos implementados
- Lógica de decisión para registrar ticks (`should_log_tick`). Determina si se
  imprime un estado con base en el modo solicitado (`none`, `events`, `ticks`).
- Bucles interactivos para avanzar la simulación tick a tick o hasta el
  siguiente evento, reutilizando la API del simulador. No implementa algoritmos
  de planificación, sino que coordina entradas y salidas.

### Ejemplos de uso
```python
from memsim.cli import create_parser

parser = create_parser()
args = parser.parse_args(["--csv", "procesos.csv", "--tick-log", "events"])
```

Para ejecutar desde código y reutilizar la salida de consola:
```python
from memsim.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
```

### Notas y extensiones futuras
- Podrían agregarse subcomandos (`run`, `report`, `gui`) o integración con
  archivos de configuración.
- Las funciones de formateo (`print_process_table`, `print_summary`) podrían
  moverse a un módulo común si se desea compartir con la GUI.

---

## `src/memsim/gui.py`

### Descripción general del módulo
Implementa la interfaz gráfica con Tkinter. Proporciona menús, barra de
herramientas y paneles para visualizar el estado de la simulación, los logs y
las métricas finales. Facilita interacciones como cargar CSV, avanzar por ticks
(o hasta un evento) y finalizar la simulación mostrando métricas agregadas.

### Librerías utilizadas
- `tkinter`, `tkinter.ttk`, `tkinter.filedialog`, `tkinter.messagebox`: widgets,
  diálogos y componentes visuales.
- `typing`: anotaciones `Dict`, `List`, `Optional`.
- Módulos internos: `memsim.io.read_processes_csv`, `memsim.models.Process`,
  `memsim.simulator.MemorySimulator`.

### Estructuras de datos principales
- Clase `MemSimGUI(tk.Tk)`: encapsula toda la aplicación gráfica y mantiene
  referencias a `MemorySimulator`, lista de procesos, rutas y estados de la
  simulación.
- Variables de control `tk.StringVar` para mostrar métricas y estados.
- `Treeview` para visualizar métricas por proceso.

### Algoritmos implementados
- Control de flujo de la simulación en modo interactivo: llama a `step()` o
  `step_hasta_evento()` y actualiza widgets según la información retornada.
- Gestión de habilitación/deshabilitación de acciones basadas en banderas (`csv`
  cargado, simulación iniciada o finalizada).
- Uso de `read_processes_csv` para cargar datos validados y recargar la vista.

### Ejemplos de uso
```python
from memsim.gui import MemSimGUI

if __name__ == "__main__":
    app = MemSimGUI()
    app.mainloop()
```

### Notas y extensiones futuras
- Existen llamadas a métodos protegidos del simulador (`_collect_state_snapshot`)
  para obtener el estado. Idealmente se podría exponer una API pública.
- Podría añadirse soporte para pausar/reanudar simulaciones largas o para
  exportar directamente desde la GUI los resultados a CSV.

---

## `src/memsim/io.py`

### Descripción general del módulo
Centraliza la entrada/salida de datos de procesos y el formateo textual del
estado de la simulación. Actualmente implementa la carga desde CSV y la
representación de snapshots; cuenta con stubs para exportar resultados y
validar datos.

### Librerías utilizadas
- `csv`: lectura de archivos con encabezados.
- `typing.List`, `typing.Optional`: anotaciones de tipos.
- Módulos internos: `memsim.models.Process`.

### Estructuras de datos principales
- Listas de `Process` para representar procesos cargados.
- Estructuras tipo diccionario (para snapshots de memoria) que contienen campos
  como `id`, `start`, `size`, `pid`, `frag_interna` y `free`.

### Algoritmos implementados
- Lectura ordenada de CSV (`read_processes_csv`): convierte filas a `Process`,
  inicializa `remaining` con el `burst` y ordena por llegada y PID para asegurar
  un flujo determinista.
- Formateo textual (`pretty_print_state`): genera una representación legible del
  estado del simulador, incluyendo tabla de memoria, cola de listos y cola de
  listos suspendidos.

### Ejemplos de uso
```python
from memsim.io import read_processes_csv, pretty_print_state

procesos = read_processes_csv("procesos.csv")
print(pretty_print_state(
    t=0,
    running=None,
    mem_table=[],
    ready=[],
    ready_susp=[]
))
```

### Notas y extensiones futuras
- Las funciones `load_processes_from_csv`, `save_results_to_file`,
  `export_memory_map` y `validate_process_data` están definidas como stubs y
  pueden implementarse para soportar más formatos y validaciones.
- Se podría agregar detección automática de encabezados o validación de tipos
  antes de crear `Process`.

---

## `src/memsim/memory.py`

### Descripción general del módulo
Gestiona la asignación y liberación de memoria en particiones fijas utilizando
estrategias de asignación (actualmente Best-Fit). Mantiene un conjunto de tres
particiones configuradas y calcula fragmentación interna para visualización.
Incluye stubs para compactación y funciones genéricas de asignación futura.

### Librerías utilizadas
- `typing.Optional`, `typing.Dict`, `typing.List`: anotaciones de tipos.
- Módulos internos: `memsim.models.Partition`.

### Estructuras de datos principales
- Clase `MemoryManager`: contiene la lista de `Partition` (P1, P2, P3) y
  proporciona operaciones de asignación/liberación.
- Lista de diccionarios generada por `table_snapshot` para integrarse con la
  visualización.
- Clase `MemoryCompactor` (stub) para futuras estrategias.

### Algoritmos implementados
- Best-Fit sobre particiones estáticas: filtra particiones libres (`is_free`),
  selecciona la más pequeña que satisfaga el tamaño solicitado y, si ninguna
  es suficiente pero existen particiones libres ocupadas por procesos, retorna
  la mayor libre para permitir la toma de decisiones (por ejemplo suspender).
- Cálculo de fragmentación interna mediante `Partition.frag_interna` y
  consolidación de snapshots con `table_snapshot` para reportes.

### Ejemplos de uso
```python
from memsim.memory import MemoryManager

mm = MemoryManager()
part = mm.best_fit(size=120)
if part is not None:
    mm.assign(part, pid=1)
# ... después
mm.release(pid=1)
```

### Notas y extensiones futuras
- `MemoryCompactor`, `allocate_memory` y `deallocate_memory` están sin
  implementar. Se prevé que soporten estrategias como First Fit, Worst Fit o
  compactación global.
- Podría integrarse un registro de particiones históricas para análisis.

---

## `src/memsim/models.py`

### Descripción general del módulo
Define las estructuras fundamentales de datos: estados de procesos, objetos
`Process` y particiones de memoria. También provee utilidades para obtener filas
serializables y calcular throughput global.

### Librerías utilizadas
- `dataclasses.dataclass`: para generar clases inmutables con atributos.
- `enum.Enum`: enumeración de estados (`State`).
- `typing.Optional`: atributos que pueden ser nulos (`start_time`, `finish_time`).

### Estructuras de datos principales
- `State`: enum con los estados `NEW`, `READY`, `READY_SUSP`, `RUNNING`,
  `TERMINATED`.
- `Process`: dataclass que almacena información de planificación y memoria.
- `Partition`: dataclass que representa una partición fija, con propiedades para
  saber si está libre y calcular fragmentación interna.

### Algoritmos implementados
- `Process.to_row`: transforma atributos en un diccionario listo para logs.
- `Partition.frag_interna`: calcula el espacio interno desperdiciado en función
  del tamaño del proceso asignado.
- `throughput`: métrica de productividad defensiva (evita división por cero).

### Ejemplos de uso
```python
from memsim.models import Process, Partition, State, throughput

proc = Process(pid=1, size=120, arrival=0, burst=5, remaining=5)
part = Partition(id="P1", start=100, size=250)
part.pid_assigned = proc.pid
print(part.frag_interna(proc.size))  # 130
print(throughput(finished=3, total_time=10))  # 0.3
```

### Notas y extensiones futuras
- Se puede extender `State` para cubrir estados intermedios (por ejemplo,
  `BLOCKED`).
- `Process` puede enriquecerse con campos de prioridad, deadline o métricas de
  E/S si se agregan nuevos algoritmos.

---

## `src/memsim/scheduler.py`

### Descripción general del módulo
Implementa el planificador SRTF (Shortest Remaining Time First) con soporte para
colas de listos y listos suspendidos. Gestiona la inserción, extracción y
preempción de procesos, además de mantener el proceso en ejecución. Incluye
stubs para clases genéricas y métricas adicionales.

### Librerías utilizadas
- `heapq`: para la cola de listos con prioridad por tiempo restante.
- `collections.deque`: cola FIFO de procesos listos suspendidos.
- `typing.Optional`, `typing.List`, `typing.Tuple`: anotaciones de tipos.
- Módulos internos: `memsim.models.Process`.

### Estructuras de datos principales
- Clase `Scheduler`: contiene `ready_heap` (min-heap con tuplas
  `(remaining, tiebreak, pid, process)`), `ready_susp` (cola FIFO), referencia al
  proceso en ejecución (`running`) y un contador para desempates (`tiebreak_counter`).
- Stubs `ProcessScheduler`, `ReadyQueue` para futuras abstracciones.

### Algoritmos implementados
- Inserción y extracción en heap para cumplir SRTF.
- Función `preempt_if_needed` utilizada por el simulador para decidir si se
  desaloja el proceso actual cuando llega uno con menor tiempo restante.
- Conteo de procesos en memoria (`count_in_memory`) para respetar el grado de
  multiprogramación.

### Ejemplos de uso
```python
from memsim.scheduler import Scheduler
from memsim.models import Process

sched = Scheduler()
proc_a = Process(pid=1, size=120, arrival=0, burst=6, remaining=6)
proc_b = Process(pid=2, size=80, arrival=1, burst=3, remaining=3)

sched.push_ready(proc_a)
sched.push_ready(proc_b)
current = sched.pop_ready_min()  # obtendrá proc_b por menor remaining
```

### Notas y extensiones futuras
- Las clases `ProcessScheduler` y `ReadyQueue`, así como las funciones
  `schedule_processes` y `calculate_metrics`, están pendientes de implementación
  y pueden generalizar el manejo de algoritmos adicionales (FCFS, RR, prioridades).
- Podría agregarse soporte para cuantum configurable o planificación híbrida.

---

## `src/memsim/simulator.py`

### Descripción general del módulo
Actúa como el motor principal de la simulación. Coordina la llegada de
procesos, la asignación de memoria, la planificación SRTF y el registro de
estadísticas. Expone métodos para ejecutar la simulación completa o avanzar por
pasos, así como un modo de depuración con validación de invariantes.

### Librerías utilizadas
- `csv`, `os`: generación de reportes (`simulation_report.csv`).
- `logging`: configuración de bitácoras con niveles `INFO`/`DEBUG`.
- `typing.List`, `typing.Dict`, `typing.Optional`, `typing.Tuple`: anotaciones de
  tipos.
- Módulos internos: `memsim.models.Process`, `memsim.models.State`,
  `memsim.models.throughput`, `memsim.memory.MemoryManager`,
  `memsim.scheduler.Scheduler`, `memsim.io.pretty_print_state`.

### Estructuras de datos principales
- Clase `MemorySimulator`: encapsula el estado global (listas de llegadas,
  terminados, tiempo actual, log de simulación, caché de resumen, grado máximo
  de multiprogramación, etc.).
- Listas de procesos (`arrivals`, `terminated`), heap de listos y deque de
  suspendidos manejados indirectamente via `Scheduler`.
- Diccionarios producidos por `_calculate_metrics` y `_collect_state_snapshot`.

### Algoritmos implementados
- Ciclo de simulación por tick (`step`): orquesta la secuencia de llegada,
  planificación, ejecución, terminación y desuspensión. Cada subpaso indica si
  se registraron eventos para controlar bitácoras.
- Llegadas con control de multiprogramación (`_handle_arrivals`): intenta
  asignar memoria con Best-Fit; suspende procesos cuando no hay particiones o
  se excede el grado máximo.
- Planificación SRTF (`_schedule_srtf`): utiliza el heap del planificador para
  seleccionar el proceso de menor `remaining` e implementa preempción.
- Ejecución de CPU (`_execute_tick`): decrementa el tiempo restante del proceso
  en ejecución.
- Terminación y liberación de memoria (`_handle_termination`): registra tiempos
  de finalización, libera particiones y mueve procesos a la lista de terminados.
- Desuspensión (`_handle_desuspension`): reintenta asignar memoria a procesos en
  cola suspendida cuando hay particiones libres.
- Validación de invariantes (`_validate_invariants`): en modo debug verifica
  unicidad de PIDs por estructura y grado máximo de multiprogramación.
- Exportación de reportes (`_export_csv_report`): genera un CSV con métricas por
  proceso y promedios globales.

### Ejemplos de uso
```python
from memsim.simulator import MemorySimulator
from memsim.io import read_processes_csv

sim = MemorySimulator(log_level="DEBUG")
procesos = read_processes_csv("procesos.csv")
resumen = sim.run_simulation(procesos)
print(resumen["avg_turnaround"])
```

Ejecutar en modo paso a paso:
```python
sim.initialize(procesos)
while not sim.is_complete():
    tick_info = sim.step()
    if tick_info:
        print(tick_info["snapshot"])
summary = sim.finalize()
```

### Notas y extensiones futuras
- Existen stubs (`SimulationConfig`, `generate_report`) para encapsular
  configuración y reportes avanzados.
- El método `_collect_state_snapshot` usa `pretty_print_state`; se podría
  ofrecer una representación estructurada además del texto.
- La exportación a CSV podría parametrizar la ruta o el formato.

---

# Mapa de dependencias

```
__main__ ──▶ cli ──▶ simulator ──▶ {scheduler, memory, io.pretty_print_state, models}
           │            │
           │            ├─▶ memory ──▶ models.Partition
           │            ├─▶ scheduler ──▶ models.Process
           │            ├─▶ io.pretty_print_state ──▶ models.Process
           │            └─▶ models (Process, State, throughput)
           │
           └─▶ io.read_processes_csv ──▶ models.Process

gui ──▶ {simulator, io.read_processes_csv, models.Process}
```

# Ejemplo de flujo completo

1. **Carga de procesos desde CSV (`io.py`)**
   ```python
   from memsim.io import read_processes_csv

   procesos = read_processes_csv("examples/processes_example.csv")
   ```
2. **Inicialización del simulador (`simulator.py`)**
   ```python
   from memsim.simulator import MemorySimulator

   simulador = MemorySimulator(log_level="INFO")
   simulador.initialize(procesos)
   ```
3. **Ejecución automática**
   ```python
   resumen = simulador.run_simulation(procesos)
   ```
4. **Presentación de resultados**
   - **CLI (`cli.py`)**: `python -m memsim --csv examples/processes_example.csv` imprime tabla por proceso y resumen.
   - **GUI (`gui.py`)**: ejecutar `python -m memsim.gui` abre la aplicación gráfica que muestra snapshots, métricas y bitácoras.

Este flujo refleja cómo los módulos colaboran: `io.py` provee procesos, el
`MemorySimulator` coordina `scheduler.py` (SRTF) y `memory.py` (Best-Fit), y
las interfaces (CLI/GUI) consumen los resultados para usuarios finales.
