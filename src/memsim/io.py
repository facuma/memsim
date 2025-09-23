"""
Input/Output operations for the memory simulation.

This module handles reading process data from files (CSV, JSON),
writing simulation results, and managing data persistence.
"""

import csv
from typing import List, Optional
from .models import Process


def read_processes_csv(path: str) -> List[Process]:
    """
    Read process data from a CSV file.
    
    Expected CSV format with header: pid,size,arrival,burst
    Sets remaining=burst when loading.
    Returns list sorted by arrival time, then by pid.
    
    Args:
        path: Path to the CSV file
        
    Returns:
        List[Process]: List of Process objects sorted by arrival then pid
    """
    processes = []
    
    try:
        with open(path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Parse CSV row
                pid = int(row['pid'])
                size = int(row['size'])
                arrival = int(row['arrival'])
                burst = int(row['burst'])
                
                # Create Process with remaining=burst
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
        raise ValueError(f"Missing required column in CSV: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid data in CSV file: {e}")
    
    # Sort by arrival time, then by pid
    processes.sort(key=lambda p: (p.arrival, p.pid))
    
    return processes


def pretty_print_state(
    t: int, 
    running: Optional[Process], 
    mem_table: List[dict], 
    ready: List[Process], 
    ready_susp: List[Process]
) -> str:
    """
    Generate a formatted string representing the current simulation state.
    
    Args:
        t: Current simulation time
        running: Currently running process (None if idle)
        mem_table: Memory table with partition information
        ready: List of processes in ready queue
        ready_susp: List of processes in ready_susp queue
        
    Returns:
        str: Formatted state string
    """
    lines = []
    
    # Time and CPU status
    cpu_status = f"pid={running.pid}" if running else "IDLE"
    lines.append(f"t={t} | CPU: {cpu_status}")
    
    # Memory table
    lines.append("Memory:")
    if mem_table:
        # Header
        lines.append("  id  start  size  pid  frag  free")
        lines.append("  --  -----  ----  ---  ----  ----")
        
        # Data rows
        for entry in mem_table:
            pid_str = str(entry['pid']) if entry['pid'] is not None else "---"
            free_str = "Yes" if entry.get('free', True) else "No"
            lines.append(f"  {entry['id']:2}  {entry['start']:5}  {entry['size']:4}  {pid_str:3}  {entry['frag_interna']:4}  {free_str:4}")
    else:
        lines.append("  (no memory partitions)")
    
    # Ready queue
    lines.append("Ready:")
    if ready:
        ready_info = []
        for proc in ready:
            ready_info.append(f"pid={proc.pid}(rem={proc.remaining})")
        lines.append(f"  {' '.join(ready_info)}")
    else:
        lines.append("  (empty)")
    
    # Ready suspended queue
    lines.append("Ready_susp:")
    if ready_susp:
        susp_info = []
        for proc in ready_susp:
            susp_info.append(f"pid={proc.pid}(size={proc.size})")
        lines.append(f"  {' '.join(susp_info)}")
    else:
        lines.append("  (empty)")
    
    return "\n".join(lines)


def load_processes_from_csv(filepath):
    """
    Load process data from a CSV file.
    
    Expected CSV format:
    pid,size,arrival,burst
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        list: List of Process objects
    """
    pass


def save_results_to_file(results, filepath, format="csv"):
    """
    Save simulation results to a file.
    
    Args:
        results: Dictionary containing simulation results
        filepath: Path where to save the results
        format: Output format ("csv", "json", "txt")
        
    Returns:
        bool: True if save successful, False otherwise
    """
    pass


def export_memory_map(memory_state, filepath):
    """
    Export the current memory map to a file.
    
    Args:
        memory_state: Current state of memory allocation
        filepath: Path where to save the memory map
        
    Returns:
        bool: True if export successful, False otherwise
    """
    pass


def validate_process_data(processes):
    """
    Validate process data for consistency and correctness.
    
    Args:
        processes: List of Process objects to validate
        
    Returns:
        tuple: (is_valid, error_messages)
    """
    pass
