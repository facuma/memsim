# Memsim

Herramienta de simulación de memoria para planificación de procesos y administración de particiones.

## Instalación

1. Instala Poetry si aún no lo tienes:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Instala el proyecto en modo editable:
   ```bash
   poetry install
   ```

## Uso

### Interfaz de línea de comandos

Ejecuta simulaciones desde la CLI:

```bash
# Simulación básica registrando solo eventos relevantes
python -m memsim --csv examples/processes_example.csv --tick-log events

# Simulación detallada registrando cada tick
python -m memsim --csv examples/processes_example.csv --tick-log ticks

# Simulación con bitácora de depuración (muestra decisiones internas)
python -m memsim --csv examples/processes_example.csv --tick-log events --log-level DEBUG

# Simulación sin mostrar estados intermedios
python -m memsim --csv examples/processes_example.csv --tick-log none

# Salida sin encabezados (útil para automatización)
python -m memsim --csv examples/processes_example.csv --tick-log events --no-header

# Ejecución interactiva tick a tick
python -m memsim --csv examples/processes_example.csv --interactive
```

### Modo interactivo

Con la opción `--interactive` la simulación se inicializa y queda a la espera de entradas del usuario:

- `Enter`: avanza un único tick y muestra el estado actualizado.
- `s`: salta hasta el siguiente tick con un evento significativo (llegada, expulsión, terminación o desuspensión) e indica cuántos ticks fueron agregados automáticamente.
- `q`: finaliza el modo interactivo y ejecuta el resto de ticks de forma automática antes de mostrar el resumen.

Todos los mensajes del modo interactivo están localizados en español para facilitar su uso en clases y demostraciones.

### Opciones de la CLI

- `--csv RUTA`: Ruta al archivo CSV con la definición de procesos (obligatorio).
- `--tick-log {none,events,ticks}`: Nivel de detalle al reproducir la bitácora (predeterminado: `none`).
  - `none`: No se muestran estados intermedios.
  - `events`: Se muestran únicamente los ticks con eventos relevantes.
  - `ticks`: Se muestra cada tick de la simulación.
- `--log-level {INFO,DEBUG}`: Nivel de detalle de los mensajes informativos (predeterminado: `INFO`).
  - `INFO`: Mensajes generales.
  - `DEBUG`: Mensajes detallados sobre admisión, asignación y desalojos.
- `--no-header`: Omite los encabezados de las tablas finales.
- `--interactive`: Activa la ejecución tick a tick descrita anteriormente.

### Ejemplo de salida

```
--- Tick 0 ---
t=0 | CPU: pid=1
Memoria:
  id  inicio  tamaño  pid  frag  libre
  --  ------  ------  ---  ----  -----
  P1    100      250    1   186     No
  P2    350      150  ---     0    Sí
  P3    500       50  ---     0    Sí
Listos:
  (vacío)
Listos_suspendidos:
  (vacío)

Resultados por proceso:
pid  arrival  burst  start_time  finish_time  turnaround  wait
---  -------  -----  ----------  -----------  ----------  ----
  1        0      5           0            5           5     0
  2        2      8           2           10           8     0

Resumen:
Tiempo promedio de turnaround: 6.50
Tiempo promedio de espera: 0.00
Throughput: 0.4000 procesos/unidad de tiempo
Tiempo total de simulación: 10
```

## Pruebas

Ejecuta la batería de pruebas con:
```bash
poetry run pytest
```

## Estructura del proyecto

- `src/memsim/`: Código fuente principal del paquete.
- `tests/`: Casos de prueba automatizados.
- `examples/`: Archivos CSV de ejemplo para ejecutar simulaciones.
