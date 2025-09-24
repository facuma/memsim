# Memsim - Estructura del Proyecto

Este documento describe la organización de los archivos en el paquete `memsim`.

```
src/memsim
```

## Archivos principales

### `src/memsim/__init__.py`
Define la descripción general del paquete **Memsim** y expone el número de versión para que otros componentes puedan consultar la release actual.

### `src/memsim/__main__.py`
Actúa como punto de entrada cuando se ejecuta `python -m memsim`, importando y delegando en `cli.main()` para lanzar la interfaz de línea de comandos.

### `src/memsim/cli.py`
Implementa la interfaz CLI: construye el `argparse.ArgumentParser`, carga procesos desde CSV, ejecuta la simulación, decide si mostrar los registros por tick y formatea tanto la tabla de procesos como el resumen estadístico, controlando los mensajes de error en la consola.

### `src/memsim/io.py`
Gestiona la E/S de datos de procesos, incluida la lectura de CSV en objetos `Process`, la creación de una vista legible del estado del simulador y deja *stubs* para futuras funciones de carga, guardado y validación adicionales.

### `src/memsim/memory.py`
Proporciona `MemoryManager`, encargado de tres particiones fijas con asignación, liberación y búsqueda *Best-Fit* (incluyendo el *fallback* cuando no hay bloques suficientemente grandes), junto con *snapshots* de memoria que calculan la fragmentación interna mediante `Partition.frag_interna`; además, define esbozos para compactación y utilidades de asignación/desasignación aún no implementadas.

### `src/memsim/models.py`
Declara las estructuras de datos principales:
- El enum `State`.
- Las *dataclasses* `Process` y `Partition` (con utilidades como `to_row`, `is_free` y `frag_interna`).
- La función `throughput` para métricas globales.

### `src/memsim/scheduler.py`
Implementa un planificador basado en **SRTF** que usa un *heap* para la cola lista y un `deque` para la cola suspendida, con operaciones de inserción, extracción y preempción; además, reserva lugares para futuras clases y funciones de planificación y métricas más avanzadas.

### `src/memsim/simulator.py`
Orquesta la simulación completa:
- Inicializa memoria y planificador.
- Gestiona llegadas, planificación SRTF, ejecución, terminaciones, desuspensiones.
- Valida invariantes.
- Captura estados y exporta reportes CSV.
- Deja esbozados componentes de configuración y generación de reportes adicionales.
