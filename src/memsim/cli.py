"""
Command-line interface for the memory simulation tool.

This module provides the CLI interface for running simulations,
configuring parameters, and displaying results.
"""

import argparse
import sys
from .simulator import MemorySimulator
from .io import read_processes_csv


def create_parser():
    """
    Create the command-line argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Memory simulation tool for process scheduling and memory management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m memsim --csv examples/processes_example.csv --tick-log events
  python -m memsim --csv data/processes.csv --tick-log ticks --no-header
        """
    )
    
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to the CSV file containing process data (required)"
    )
    
    parser.add_argument(
        "--tick-log",
        choices=["none", "events", "ticks"],
        default="none",
        help="Logging level: none (no intermediate state), events (arrivals/terminations), ticks (every tick) (default: none)"
    )
    
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Don't print column headers in output"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["INFO", "DEBUG"],
        default="INFO",
        help="Logging level: INFO (basic info) or DEBUG (detailed decisions) (default: INFO)"
    )
    
    return parser


def print_process_table(processes, show_header=True):
    """
    Print the process results table.
    
    Args:
        processes: List of process metrics dictionaries
        show_header: Whether to print column headers
    """
    if not processes:
        print("No processes completed.")
        return
    
    if show_header:
        print("\nProcess Results:")
        print("pid  arrival  burst  start_time  finish_time  turnaround  wait")
        print("---  -------  -----  ----------  -----------  ----------  ----")
    
    for proc in processes:
        print(f"{proc['pid']:3}  {proc['arrival']:7}  {proc['burst']:5}  {proc['start_time']:10}  {proc['finish_time']:11}  {proc['turnaround']:10}  {proc['wait']:4}")


def print_summary(avg_turnaround, avg_wait, throughput, tiempo_total, show_header=True):
    """
    Print the summary statistics.
    
    Args:
        avg_turnaround: Average turnaround time
        avg_wait: Average wait time
        throughput: Throughput value
        tiempo_total: Total simulation time
        show_header: Whether to print section header
    """
    if show_header:
        print("\nSummary:")
    
    print(f"Average Turnaround Time: {avg_turnaround:.2f}")
    print(f"Average Wait Time: {avg_wait:.2f}")
    print(f"Throughput: {throughput:.4f} processes/time unit")
    print(f"Total Simulation Time: {tiempo_total}")


def should_log_tick(tick_log_mode, current_time, last_logged_time, events_occurred):
    """
    Determine if we should log the current tick based on the logging mode.
    
    Args:
        tick_log_mode: Logging mode ("none", "events", "ticks")
        current_time: Current simulation time
        last_logged_time: Last time we logged
        events_occurred: Whether events occurred this tick
        
    Returns:
        bool: True if we should log this tick
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
    Main entry point for the CLI application.
    """
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # Load processes from CSV
        processes = read_processes_csv(args.csv)
        
        if not processes:
            print("No processes loaded from CSV file.")
            return 1
        
        # Run simulation
        simulator = MemorySimulator(log_level=args.log_level)
        results = simulator.run_simulation(processes)
        
        # Print intermediate states based on tick-log mode
        if args.tick_log != "none":
            last_logged_time = -1
            
            for i, log_entry in enumerate(results['simulation_log']):
                current_time = i
                events_occurred = False
                
                # Check if events occurred (simplified check)
                if "CPU: pid=" in log_entry or "CPU: IDLE" in log_entry:
                    events_occurred = True
                
                if should_log_tick(args.tick_log, current_time, last_logged_time, events_occurred):
                    print(f"\n--- Tick {current_time} ---")
                    print(log_entry)
                    last_logged_time = current_time
        
        # Print final results
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
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
