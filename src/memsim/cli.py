"""
Interfaz de línea de comandos para la herramienta de simulación de memoria.

Este módulo ofrece la interfaz CLI para ejecutar simulaciones, configurar
parámetros y mostrar resultados.
"""

import argparse
import sys
from .simulator import MemorySimulator
from .io import read_processes_csv


def create_parser():
    """
    Crea el parser de argumentos de la línea de comandos.

    Returns:
        argparse.ArgumentParser: Parser configurado.
    """
    parser = argparse.ArgumentParser(
        description="Herramienta de simulación de memoria y planificación de procesos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python -m memsim --csv examples/processes_example.csv --tick-log events
  python -m memsim --csv data/processes.csv --tick-log ticks --no-header
        """
    )

    parser.add_argument(
        "--csv",
        required=True,
        help="Ruta al archivo CSV con los procesos (obligatorio)"
    )

    parser.add_argument(
        "--tick-log",
        choices=["none", "events", "ticks"],
        default="none",
        help="Nivel de registro: none (sin estados), events (eventos), ticks (cada tick)"
    )

    parser.add_argument(
        "--no-header",
        action="store_true",
        help="No imprimir encabezados en la salida"
    )

    parser.add_argument(
        "--log-level",
        choices=["INFO", "DEBUG"],
        default="INFO",
        help="Nivel de log: INFO (básico) o DEBUG (detallado)"
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Ejecuta la simulación en modo interactivo"
    )

    return parser


def print_process_table(processes, show_header=True):
    """
    Imprime la tabla de resultados por proceso.

    Args:
        processes: Lista de métricas por proceso.
        show_header: Si se deben imprimir encabezados.
    """
    if not processes:
        print("No se completaron procesos.")
        return

    if show_header:
        print("\nResultados por proceso:")
        print("pid  arrival  burst  start_time  finish_time  turnaround  wait")
        print("---  -------  -----  ----------  -----------  ----------  ----")
    
    for proc in processes:
        print(f"{proc['pid']:3}  {proc['arrival']:7}  {proc['burst']:5}  {proc['start_time']:10}  {proc['finish_time']:11}  {proc['turnaround']:10}  {proc['wait']:4}")


def print_summary(avg_turnaround, avg_wait, throughput, tiempo_total, show_header=True):
    """
    Imprime las estadísticas de resumen.

    Args:
        avg_turnaround: Tiempo promedio de turnaround.
        avg_wait: Tiempo promedio de espera.
        throughput: Valor de throughput.
        tiempo_total: Tiempo total de simulación.
        show_header: Si se imprime el encabezado de sección.
    """
    if show_header:
        print("\nResumen:")

    print(f"Tiempo promedio de turnaround: {avg_turnaround:.2f}")
    print(f"Tiempo promedio de espera: {avg_wait:.2f}")
    print(f"Throughput: {throughput:.4f} procesos/unidad de tiempo")
    print(f"Tiempo total de simulación: {tiempo_total}")


def should_log_tick(tick_log_mode, current_time, last_logged_time, events_occurred):
    """
    Determina si se debe registrar el tick actual según el modo elegido.

    Args:
        tick_log_mode: Modo de registro ("none", "events", "ticks").
        current_time: Tiempo actual de la simulación.
        last_logged_time: Último tiempo registrado.
        events_occurred: Si ocurrieron eventos en el tick.

    Returns:
        bool: True si corresponde registrar el tick.
    """
    if tick_log_mode == "none":
        return False
    elif tick_log_mode == "events":
        return events_occurred
    elif tick_log_mode == "ticks":
        return True
    return False


def main():
    """
    Punto de entrada principal de la aplicación CLI.
    """
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Cargar procesos desde CSV
        processes = read_processes_csv(args.csv)

        if not processes:
            print("No se cargaron procesos desde el archivo CSV.")
            return 1
        
        # Validar que la cantidad de procesos no supere los 10
        if len(processes) > 10:
            print("Error: La carga de trabajo no puede superar los 10 procesos.", file=sys.stderr)
            return 1

        # Ejecutar simulación
        simulator = MemorySimulator(log_level=args.log_level)

        if args.interactive:
            simulator.initialize(processes)
            print("Modo interactivo activado. Presiona Enter para avanzar un tick, 's' para saltar al siguiente evento o escribe 'q' para finalizar.")

            while True:
                if simulator.is_complete():
                    print("La simulación ha finalizado.")
                    break

                user_input = input("Acción [Enter=1 tick, s=evento, q=salir]: ")
                comando = user_input.strip().lower()
                if comando in {"q", "quit", "exit"}:
                    print("Finalizando modo interactivo. Ejecutando los ticks restantes automáticamente...")
                    break

                if comando == "s":
                    tick_info = simulator.step_hasta_evento()
                    if tick_info is None:
                        print("La simulación ha finalizado.")
                        break

                    print(f"\n--- Tick {tick_info['time']} (saltados {tick_info.get('ticks_agregados', 1) - 1}) ---")
                    print(tick_info['snapshot'])
                    continue

                tick_info = simulator.step()
                if tick_info is None:
                    print("La simulación ha finalizado.")
                    break

                print(f"\n--- Tick {tick_info['time']} ---")
                print(tick_info['snapshot'])

            results = simulator.finalize()
        else:
            results = simulator.run_simulation(processes)

        # Mostrar estados intermedios según tick-log (reproducción no interactiva)
        if not args.interactive and args.tick_log != "none":
            last_logged_time = -1

            for i, log_entry in enumerate(results['simulation_log']):
                current_time = i
                events_occurred = False

                # Verificar si ocurrieron eventos (revisión simple)
                if "CPU: pid=" in log_entry or "CPU: IDLE" in log_entry:
                    events_occurred = True

                if should_log_tick(args.tick_log, current_time, last_logged_time, events_occurred):
                    print(f"\n--- Tick {current_time} ---")
                    print(log_entry)
                    last_logged_time = current_time

        # Mostrar resultados finales
        print_process_table(results['processes'], not args.no_header)
        print_summary(
            results['avg_turnaround'],
            results['avg_wait'],
            results['throughput'],
            results['tiempo_total'],
            not args.no_header
        )

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error inesperado: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
