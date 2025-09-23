"""
Main simulation engine and coordination.

This module orchestrates the memory simulation by coordinating between
memory management, process scheduling, and I/O operations.
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
    Main simulation engine for memory management.
    
    This class coordinates the entire simulation process, managing the
    interaction between memory allocation, process scheduling, and system events.
    """
    
    def __init__(self, debug_mode: bool = False, log_level: str = "INFO"):
        """
        Initialize the simulator with memory manager and scheduler.
        
        Args:
            debug_mode: Enable invariant validation and debug assertions
            log_level: Logging level ("INFO" or "DEBUG")
        """
        self.memory_manager = MemoryManager()
        self.scheduler = Scheduler()
        self.arrivals: List[Process] = []
        self.terminated: List[Process] = []
        self.current_time = 0
        self.max_multiprogramming = 5
        self.debug_mode = debug_mode
        
        # Setup logger
        self.logger = logging.getLogger('memsim')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create console handler if not already exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def run_simulation(self, processes: List[Process]) -> Dict:
        """
        Run the complete memory simulation.
        
        Args:
            processes: List of Process objects to simulate
            
        Returns:
            dict: Simulation results and metrics
        """
        # Initialize simulation state
        self.arrivals = sorted(processes, key=lambda p: (p.arrival, p.pid))
        self.terminated = []
        self.current_time = 0
        self.scheduler = Scheduler()
        self.memory_manager = MemoryManager()
        
        # Simulation log for debugging
        simulation_log = []
        
        # Main simulation loop
        while self._has_pending_processes():
            # 1) Handle arrivals at current time
            self._handle_arrivals()
            
            # 2) SRTF Scheduling
            self._schedule_srtf()
            
            # 3) Execute 1 tick
            self._execute_tick()
            
            # 4) Handle process termination
            self._handle_termination()
            
            # 5) Handle desuspension
            self._handle_desuspension()
            
            # 6) Validate invariants (debug mode)
            self._validate_invariants()
            
            # 7) Collect state snapshot for logging
            state_snapshot = self._collect_state_snapshot()
            simulation_log.append(state_snapshot)
            
            # 8) Increment time
            self.current_time += 1
        
        # Calculate final metrics
        summary = self._calculate_metrics()
        summary['simulation_log'] = simulation_log
        
        # Export CSV report
        self._export_csv_report(summary)
        
        return summary
    
    def _has_pending_processes(self) -> bool:
        """Check if there are still processes to process."""
        return (len(self.arrivals) > 0 or 
                len(self.scheduler.ready_heap) > 0 or 
                len(self.scheduler.ready_susp) > 0 or 
                self.scheduler.running is not None)
    
    def _handle_arrivals(self):
        """Handle process arrivals at current time."""
        arriving_processes = []
        
        # Find all processes arriving at current time
        while self.arrivals and self.arrivals[0].arrival == self.current_time:
            arriving_processes.append(self.arrivals.pop(0))
        
        # Try to admit each arriving process
        for process in arriving_processes:
            if self.scheduler.count_in_memory() < self.max_multiprogramming:
                # Try to allocate memory with Best-Fit
                partition = self.memory_manager.best_fit(process.size)
                if partition is not None:
                    # Allocate memory and add to ready queue
                    self.memory_manager.assign(partition, process.pid)
                    self.scheduler.push_ready(process)
                    self.logger.debug(f"Process {process.pid} admitted to {partition.id} (size={process.size})")
                else:
                    # No suitable partition, add to suspended queue
                    self.scheduler.enqueue_suspended(process)
                    self.logger.debug(f"Process {process.pid} suspended - no suitable partition (size={process.size})")
            else:
                # Memory full, add to suspended queue
                self.scheduler.enqueue_suspended(process)
                self.logger.debug(f"Process {process.pid} suspended - memory full (degree={self.scheduler.count_in_memory()})")
    
    def _schedule_srtf(self):
        """Handle SRTF scheduling with preemption."""
        if self.scheduler.running is None:
            # CPU is free, take next process from ready queue
            if self.scheduler.ready_heap:
                process = self.scheduler.pop_ready_min()
                self.scheduler.running = process
                if process.start_time is None:
                    process.start_time = self.current_time
                self.logger.debug(f"Process {process.pid} started running (remaining={process.remaining})")
        else:
            # CPU is occupied, check for preemption
            if self.scheduler.ready_heap:
                min_ready = self.scheduler.peek_ready_min()
                if min_ready.remaining < self.scheduler.running.remaining:
                    # Preempt current process
                    preempted = self.scheduler.running
                    self.scheduler.running = None
                    self.scheduler.push_ready(preempted)
                    
                    # Take new process
                    new_process = self.scheduler.pop_ready_min()
                    self.scheduler.running = new_process
                    if new_process.start_time is None:
                        new_process.start_time = self.current_time
                    self.logger.debug(f"SRTF preemption: Process {preempted.pid} preempted by {new_process.pid} (remaining: {preempted.remaining} -> {new_process.remaining})")
    
    def _execute_tick(self):
        """Execute one time tick."""
        if self.scheduler.running is not None:
            self.scheduler.running.remaining -= 1
    
    def _handle_termination(self):
        """Handle process termination."""
        if (self.scheduler.running is not None and 
            self.scheduler.running.remaining <= 0):
            # Process finished
            finished_process = self.scheduler.running
            finished_process.finish_time = self.current_time + 1
            finished_process.state = State.TERMINATED
            
            # Release memory partition
            self.memory_manager.release(finished_process.pid)
            self.logger.debug(f"Process {finished_process.pid} terminated, partition released")
            
            # Move to terminated list
            self.terminated.append(finished_process)
            self.scheduler.running = None
    
    def _handle_desuspension(self):
        """Handle desuspension of suspended processes."""
        while (self.scheduler.ready_susp and 
               self.scheduler.count_in_memory() < self.max_multiprogramming):
            # Take front of suspended queue
            process = self.scheduler.dequeue_suspended()
            
            # Try to allocate memory with Best-Fit
            partition = self.memory_manager.best_fit(process.size)
            if partition is not None:
                # Allocate memory and add to ready queue
                self.memory_manager.assign(partition, process.pid)
                self.scheduler.push_ready(process)
                self.logger.debug(f"Process {process.pid} desuspended to {partition.id} (size={process.size})")
            else:
                # No suitable partition, put back at front of suspended queue
                self.scheduler.ready_susp.appendleft(process)
                self.logger.debug(f"Process {process.pid} remains suspended - no suitable partition")
                break  # Stop trying to desuspend
    
    def _collect_state_snapshot(self) -> str:
        """Collect current state snapshot for logging."""
        # Get memory table
        process_sizes = {p.pid: p.size for p in self.terminated}
        if self.scheduler.running:
            process_sizes[self.scheduler.running.pid] = self.scheduler.running.size
        
        # Add ready processes
        for _, _, _, process in self.scheduler.ready_heap:
            process_sizes[process.pid] = process.size
        
        mem_table = self.memory_manager.table_snapshot(process_sizes)
        
        # Get ready processes list
        ready_processes = [process for _, _, _, process in self.scheduler.ready_heap]
        
        # Get suspended processes list
        suspended_processes = list(self.scheduler.ready_susp)
        
        return pretty_print_state(
            self.current_time,
            self.scheduler.running,
            mem_table,
            ready_processes,
            suspended_processes
        )
    
    def _calculate_metrics(self) -> Dict:
        """Calculate final simulation metrics."""
        if not self.terminated:
            return {
                'processes': [],
                'avg_turnaround': 0.0,
                'avg_wait': 0.0,
                'throughput': 0.0,
                'tiempo_total': self.current_time
            }
        
        # Calculate per-process metrics
        process_metrics = []
        total_turnaround = 0
        total_wait = 0
        
        for process in self.terminated:
            # Precise calculations
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
        
        # Calculate averages
        num_processes = len(self.terminated)
        avg_turnaround = total_turnaround / num_processes if num_processes > 0 else 0.0
        avg_wait = total_wait / num_processes if num_processes > 0 else 0.0
        
        # Defensive throughput calculation
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
        Validate simulation invariants in debug mode.
        
        Raises:
            AssertionError: If any invariant is violated
        """
        if not self.debug_mode:
            return
        
        # Invariant 1: Multiprogramming degree <= 5
        current_count = self.scheduler.count_in_memory()
        assert current_count <= 5, f"Multiprogramming degree exceeded: {current_count} > 5"
        
        # Invariant 2: No duplicate PIDs in partitions
        assigned_pids = set()
        for partition in self.memory_manager.partitions:
            if partition.pid_assigned is not None:
                assert partition.pid_assigned not in assigned_pids, f"Duplicate PID {partition.pid_assigned} in partitions"
                assigned_pids.add(partition.pid_assigned)
        
        # Invariant 3: Each process is in exactly one container
        all_processes = set()
        
        # Check arrivals
        for process in self.arrivals:
            assert process.pid not in all_processes, f"Process {process.pid} found in multiple containers (arrivals)"
            all_processes.add(process.pid)
        
        # Check ready queue
        for _, _, _, process in self.scheduler.ready_heap:
            assert process.pid not in all_processes, f"Process {process.pid} found in multiple containers (ready)"
            all_processes.add(process.pid)
        
        # Check suspended queue
        for process in self.scheduler.ready_susp:
            assert process.pid not in all_processes, f"Process {process.pid} found in multiple containers (ready_susp)"
            all_processes.add(process.pid)
        
        # Check running
        if self.scheduler.running is not None:
            assert self.scheduler.running.pid not in all_processes, f"Process {self.scheduler.running.pid} found in multiple containers (running)"
            all_processes.add(self.scheduler.running.pid)
        
        # Check terminated
        for process in self.terminated:
            assert process.pid not in all_processes, f"Process {process.pid} found in multiple containers (terminated)"
            all_processes.add(process.pid)
    
    def _export_csv_report(self, summary: Dict):
        """
        Export simulation metrics to CSV file.
        
        Args:
            summary: Simulation results dictionary
        """
        csv_path = os.path.join(os.getcwd(), "simulation_report.csv")
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow([
                    'pid', 'arrival', 'burst', 'start_time', 'finish_time', 
                    'turnaround', 'wait', 'size'
                ])
                
                # Write process data
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
                
                # Write summary row
                writer.writerow([])  # Empty row
                writer.writerow(['SUMMARY', '', '', '', '', '', '', ''])
                writer.writerow(['avg_turnaround', summary['avg_turnaround']])
                writer.writerow(['avg_wait', summary['avg_wait']])
                writer.writerow(['throughput', summary['throughput']])
                writer.writerow(['tiempo_total', summary['tiempo_total']])
                
        except Exception as e:
            # Don't fail simulation if CSV export fails
            print(f"Warning: Failed to export CSV report: {e}")
            import traceback
            traceback.print_exc()


class SimulationConfig:
    """
    Configuration settings for the simulation.
    
    This class holds all configuration parameters needed to run
    the simulation, including memory size, scheduling algorithm, etc.
    """
    pass


def run_simulation(config, processes):
    """
    Run the complete memory simulation.
    
    Args:
        config: SimulationConfig object with simulation parameters
        processes: List of Process objects to simulate
        
    Returns:
        dict: Simulation results and metrics
    """
    simulator = MemorySimulator()
    return simulator.run_simulation(processes)


def generate_report(results):
    """
    Generate a detailed simulation report.
    
    Args:
        results: Dictionary containing simulation results
        
    Returns:
        str: Formatted simulation report
    """
    pass
