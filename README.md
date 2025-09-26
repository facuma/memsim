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

### Interfaz gráfica de usuario (GUI)

La aplicación también cuenta con una interfaz Tkinter que permite cargar un CSV, inicializar la simulación y avanzar tick a tick o hasta el próximo evento significativo.

```bash
# Ejecutar la GUI directamente
python -m memsim.gui

# O bien, usando Poetry
poetry run python -m memsim.gui
```

En Windows puedes crear un acceso directo que ejecute `python -m memsim.gui` o empaquetar el programa con PyInstaller para distribuir un `.exe`.

### Creación de ejecutable en Windows con PyInstaller

Con PyInstaller es posible generar un ejecutable autónomo que incluya la GUI y acepte un CSV proporcionado por el usuario:

```bash
poetry run pyinstaller -F -n memsim_gui src/memsim/gui.py
```

El binario quedará en `dist/memsim_gui.exe`. Puedes distribuirlo tal cual o integrarlo en un instalador (por ejemplo, Inno Setup). Asegúrate de incluir los ejemplos de CSV o indicar que el usuario debe seleccionar su propio archivo al abrir la aplicación.


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

### Ejemplo de salid

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
