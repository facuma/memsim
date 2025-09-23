"""
Tests for the simulator module.

This module contains unit tests for the main simulation engine and coordination.
"""

import csv
import os
import pytest
from src.memsim.simulator import MemorySimulator, SimulationConfig, run_simulation, generate_report
from src.memsim.models import Process, State


class TestMemorySimulator:
    """Test cases for the MemorySimulator class."""
    
    def test_simulator_initialization(self):
        """Test MemorySimulator initialization."""
        simulator = MemorySimulator()
        
        assert simulator.memory_manager is not None
        assert simulator.scheduler is not None
        assert simulator.arrivals == []
        assert simulator.terminated == []
        assert simulator.current_time == 0
        assert simulator.max_multiprogramming == 5
    
    def test_simple_simulation_no_preemption(self):
        """Test simple simulation without preemption."""
        # Create 3 processes with different arrival times
        processes = [
            Process(pid=1, size=64, arrival=0, burst=3, remaining=3),   # Small, arrives first
            Process(pid=2, size=128, arrival=1, burst=2, remaining=2),  # Medium, arrives second
            Process(pid=3, size=32, arrival=2, burst=1, remaining=1)    # Smallest, arrives last
        ]
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # All processes should terminate
        assert len(results['processes']) == 3
        
        # Check that all processes finished
        pids = [p['pid'] for p in results['processes']]
        assert 1 in pids
        assert 2 in pids
        assert 3 in pids
        
        # Check multiprogramming degree never exceeded 5
        for log_entry in results['simulation_log']:
            # Count processes in memory from log
            lines = log_entry.split('\n')
            cpu_line = next(line for line in lines if line.startswith('t='))
            ready_line = next(line for line in lines if 'Ready:' in line)
            
            # Count ready processes (simplified check)
            ready_count = ready_line.count('pid=') if 'pid=' in ready_line else 0
            cpu_count = 1 if 'CPU: pid=' in cpu_line else 0
            total_in_memory = ready_count + cpu_count
            
            assert total_in_memory <= 5
    
    def test_srtf_preemption(self):
        """Test SRTF scheduling with preemption."""
        # Create processes that will cause preemption
        processes = [
            Process(pid=1, size=64, arrival=0, burst=5, remaining=5),   # Long process starts first
            Process(pid=2, size=128, arrival=1, burst=1, remaining=1),  # Short process arrives and preempts
            Process(pid=3, size=32, arrival=2, burst=2, remaining=2)    # Medium process
        ]
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # All processes should terminate
        assert len(results['processes']) == 3
        
        # Process 2 (shortest) should finish first due to preemption
        process_metrics = {p['pid']: p for p in results['processes']}
        
        # Process 2 should have shortest turnaround time
        turnaround_times = {pid: metrics['turnaround'] for pid, metrics in process_metrics.items()}
        assert turnaround_times[2] <= turnaround_times[1]
        assert turnaround_times[2] <= turnaround_times[3]
    
    def test_best_fit_memory_allocation(self):
        """Test that processes are allocated to appropriate partitions by Best-Fit."""
        # Create processes with sizes that will test Best-Fit
        # P1: 250, P2: 150, P3: 50
        processes = [
            Process(pid=1, size=45, arrival=0, burst=2, remaining=2),   # Should go to P3 (50)
            Process(pid=2, size=120, arrival=1, burst=2, remaining=2),  # Should go to P2 (150)
            Process(pid=3, size=200, arrival=2, burst=2, remaining=2),  # Should go to P1 (250)
            Process(pid=4, size=30, arrival=3, burst=2, remaining=2),   # Should go to P3 (50) after P1 finishes
        ]
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # All processes should terminate
        assert len(results['processes']) == 4
        
        # Check that memory was allocated efficiently
        # We can verify this by checking that all processes completed
        # and that the simulation log shows proper memory allocation
        for log_entry in results['simulation_log']:
            if 'Memory:' in log_entry:
                # Check that partitions are being used appropriately
                lines = log_entry.split('\n')
                memory_lines = [line for line in lines if 'P' in line and 'start' not in line and '--' not in line]
                
                # Should have some partitions allocated
                allocated_partitions = [line for line in memory_lines if 'pid=' in line and '---' not in line]
                assert len(allocated_partitions) <= 3  # Max 3 partitions
    
    def test_multiprogramming_degree_limit(self):
        """Test that multiprogramming degree never exceeds 5."""
        # Create 7 processes that arrive at the same time
        processes = []
        for i in range(7):
            processes.append(Process(pid=i+1, size=32, arrival=0, burst=1, remaining=1))
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # All processes should terminate
        assert len(results['processes']) == 7
        
        # Check multiprogramming degree in each time step
        for log_entry in results['simulation_log']:
            lines = log_entry.split('\n')
            
            # Count processes in memory
            cpu_line = next(line for line in lines if line.startswith('t='))
            ready_line = next(line for line in lines if 'Ready:' in line)
            
            ready_count = ready_line.count('pid=') if 'pid=' in ready_line else 0
            cpu_count = 1 if 'CPU: pid=' in cpu_line else 0
            total_in_memory = ready_count + cpu_count
            
            assert total_in_memory <= 5, f"Multiprogramming degree exceeded 5: {total_in_memory}"
    
    def test_process_state_invariants(self):
        """Test that each process is in exactly one state at any time."""
        processes = [
            Process(pid=1, size=64, arrival=0, burst=2, remaining=2),
            Process(pid=2, size=128, arrival=1, burst=3, remaining=3),
            Process(pid=3, size=32, arrival=2, burst=1, remaining=1)
        ]
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # All processes should terminate
        assert len(results['processes']) == 3
        
        # Check that all processes have valid state transitions
        for process_metrics in results['processes']:
            assert process_metrics['start_time'] is not None
            assert process_metrics['finish_time'] is not None
            assert process_metrics['turnaround'] > 0
            assert process_metrics['wait'] >= 0
    
    def test_metrics_calculation(self):
        """Test that metrics are calculated correctly."""
        processes = [
            Process(pid=1, size=64, arrival=0, burst=2, remaining=2),
            Process(pid=2, size=128, arrival=1, burst=3, remaining=3),
            Process(pid=3, size=32, arrival=2, burst=1, remaining=1)
        ]
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # Check that all required metrics are present
        assert 'processes' in results
        assert 'avg_turnaround' in results
        assert 'avg_wait' in results
        assert 'throughput' in results
        assert 'tiempo_total' in results
        
        # Check that metrics are reasonable
        assert results['avg_turnaround'] > 0
        assert results['avg_wait'] >= 0
        assert results['throughput'] > 0
        assert results['tiempo_total'] > 0
        
        # Check per-process metrics
        for process_metrics in results['processes']:
            assert 'pid' in process_metrics
            assert 'turnaround' in process_metrics
            assert 'wait' in process_metrics
            assert 'arrival' in process_metrics
            assert 'burst' in process_metrics
            assert 'start_time' in process_metrics
            assert 'finish_time' in process_metrics
    
    def test_simulation_termination_condition(self):
        """Test that simulation terminates when all processes are done."""
        processes = [
            Process(pid=1, size=64, arrival=0, burst=1, remaining=1),
            Process(pid=2, size=128, arrival=1, burst=1, remaining=1)
        ]
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # Simulation should terminate
        assert len(results['processes']) == 2
        
        # All processes should be terminated
        for process_metrics in results['processes']:
            assert process_metrics['finish_time'] is not None
    
    def test_memory_partition_release(self):
        """Test that memory partitions are released when processes terminate."""
        # Create processes that will use all partitions
        processes = [
            Process(pid=1, size=200, arrival=0, burst=1, remaining=1),  # Uses P1
            Process(pid=2, size=100, arrival=0, burst=1, remaining=1),  # Uses P2
            Process(pid=3, size=30, arrival=0, burst=1, remaining=1),   # Uses P3
            Process(pid=4, size=50, arrival=2, burst=1, remaining=1),   # Should get P3 after P3 is released
        ]
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # All processes should terminate
        assert len(results['processes']) == 4
        
        # Process 4 should have been able to run (memory was released)
        process_metrics = {p['pid']: p for p in results['processes']}
        assert 4 in process_metrics
        assert process_metrics[4]['finish_time'] is not None


class TestSimulationConfig:
    """Test cases for the SimulationConfig class."""
    
    def test_config_initialization(self):
        """Test SimulationConfig initialization."""
        config = SimulationConfig()
        assert config is not None


class TestSimulatorFunctions:
    """Test cases for simulator module functions."""
    
    def test_run_simulation_function(self):
        """Test the run_simulation function."""
        processes = [
            Process(pid=1, size=64, arrival=0, burst=1, remaining=1),
            Process(pid=2, size=128, arrival=1, burst=1, remaining=1)
        ]
        
        results = run_simulation(None, processes)
        
        assert 'processes' in results
        assert 'avg_turnaround' in results
        assert 'avg_wait' in results
        assert 'throughput' in results
        assert 'tiempo_total' in results
        assert len(results['processes']) == 2
    
    def test_generate_report_function(self):
        """Test the generate_report function."""
        # Function is not implemented yet, so just test it exists
        assert generate_report is not None
    
    def test_debug_mode_invariants(self):
        """Test that debug mode validates invariants."""
        processes = [
            Process(pid=1, size=64, arrival=0, burst=1, remaining=1),
            Process(pid=2, size=128, arrival=1, burst=1, remaining=1)
        ]
        
        # Test with debug mode enabled
        simulator = MemorySimulator(debug_mode=True)
        results = simulator.run_simulation(processes)
        
        # Should complete without assertion errors
        assert len(results['processes']) == 2
        assert results['avg_turnaround'] > 0
    
    def test_invariant_multiprogramming_degree(self):
        """Test that multiprogramming degree invariant fails when violated."""
        # Create a simulator that artificially violates the invariant
        class BrokenSimulator(MemorySimulator):
            def _validate_invariants(self):
                if not self.debug_mode:
                    return
                # Artificially violate the invariant
                current_count = 10  # Exceeds limit of 5
                assert current_count <= 5, f"Multiprogramming degree exceeded: {current_count} > 5"
        
        processes = [Process(pid=1, size=64, arrival=0, burst=1, remaining=1)]
        
        with pytest.raises(AssertionError, match="Multiprogramming degree exceeded"):
            simulator = BrokenSimulator(debug_mode=True)
            simulator.run_simulation(processes)
    
    def test_invariant_duplicate_pids(self):
        """Test that duplicate PID invariant fails when violated."""
        class BrokenSimulator(MemorySimulator):
            def _validate_invariants(self):
                if not self.debug_mode:
                    return
                # Artificially create duplicate PIDs
                assigned_pids = set()
                for partition in self.memory_manager.partitions:
                    if partition.pid_assigned is not None:
                        if partition.pid_assigned in assigned_pids:
                            raise AssertionError(f"Duplicate PID {partition.pid_assigned} in partitions")
                        assigned_pids.add(partition.pid_assigned)
                # Artificially add duplicate
                assigned_pids.add(1)
                assigned_pids.add(1)  # This should trigger the assertion
        
        processes = [Process(pid=1, size=64, arrival=0, burst=1, remaining=1)]
        
        with pytest.raises(AssertionError, match="Duplicate PID"):
            simulator = BrokenSimulator(debug_mode=True)
            simulator.run_simulation(processes)
    
    def test_invariant_process_in_multiple_containers(self):
        """Test that process in multiple containers invariant fails when violated."""
        class BrokenSimulator(MemorySimulator):
            def _validate_invariants(self):
                if not self.debug_mode:
                    return
                # Artificially create a process in multiple containers
                all_processes = set()
                # Add a process to arrivals
                all_processes.add(1)
                # Try to add the same process to ready (should fail)
                if 1 in all_processes:
                    raise AssertionError("Process 1 found in multiple containers")
        
        processes = [Process(pid=1, size=64, arrival=0, burst=1, remaining=1)]
        
        with pytest.raises(AssertionError, match="found in multiple containers"):
            simulator = BrokenSimulator(debug_mode=True)
            simulator.run_simulation(processes)
    
    def test_precise_metrics_calculation(self):
        """Test that metrics are calculated precisely."""
        processes = [
            Process(pid=1, size=64, arrival=0, burst=3, remaining=3),
            Process(pid=2, size=128, arrival=1, burst=2, remaining=2)
        ]
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # Check precise calculations
        for process_metrics in results['processes']:
            pid = process_metrics['pid']
            arrival = process_metrics['arrival']
            burst = process_metrics['burst']
            start_time = process_metrics['start_time']
            finish_time = process_metrics['finish_time']
            turnaround = process_metrics['turnaround']
            wait = process_metrics['wait']
            
            # Verify precise calculations
            expected_turnaround = finish_time - arrival
            expected_wait = turnaround - burst
            
            assert turnaround == expected_turnaround, f"Process {pid}: turnaround {turnaround} != {expected_turnaround}"
            assert wait == expected_wait, f"Process {pid}: wait {wait} != {expected_wait}"
    
    def test_defensive_throughput_zero_time(self):
        """Test that throughput is 0.0 when total_time is 0."""
        # Create a simulator that finishes immediately
        class InstantSimulator(MemorySimulator):
            def _has_pending_processes(self):
                return False  # No pending processes immediately
        
        processes = [Process(pid=1, size=64, arrival=0, burst=1, remaining=1)]
        
        simulator = InstantSimulator()
        results = simulator.run_simulation(processes)
        
        # Should handle zero time gracefully
        assert results['throughput'] == 0.0
        assert results['tiempo_total'] == 0
    
    def test_csv_export(self):
        """Test that CSV report is exported."""
        processes = [
            Process(pid=1, size=64, arrival=0, burst=2, remaining=2),
            Process(pid=2, size=128, arrival=1, burst=1, remaining=1)
        ]
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # Check that CSV file was created
        assert os.path.exists("simulation_report.csv")
        
        # Verify CSV content
        with open("simulation_report.csv", 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            # Check header
            assert rows[0] == ['pid', 'arrival', 'burst', 'start_time', 'finish_time', 'turnaround', 'wait', 'size']
            
            # Check process data (skip empty row and summary)
            process_rows = [row for row in rows[1:-5] if row]  # Skip empty and summary rows
            assert len(process_rows) == 2  # Two processes
            
            # Check summary
            summary_rows = rows[-4:]
            assert any('avg_turnaround' in row for row in summary_rows)
            assert any('avg_wait' in row for row in summary_rows)
            assert any('throughput' in row for row in summary_rows)
            assert any('tiempo_total' in row for row in summary_rows)
        
        # Clean up
        os.remove("simulation_report.csv")
    
    def test_metrics_consistency(self):
        """Test that metrics are consistent with definitions."""
        processes = [
            Process(pid=1, size=64, arrival=0, burst=3, remaining=3),
            Process(pid=2, size=128, arrival=2, burst=2, remaining=2)
        ]
        
        simulator = MemorySimulator()
        results = simulator.run_simulation(processes)
        
        # Verify each process metrics
        for process_metrics in results['processes']:
            pid = process_metrics['pid']
            arrival = process_metrics['arrival']
            burst = process_metrics['burst']
            start_time = process_metrics['start_time']
            finish_time = process_metrics['finish_time']
            turnaround = process_metrics['turnaround']
            wait = process_metrics['wait']
            
            # Check that start_time >= arrival
            assert start_time >= arrival, f"Process {pid}: start_time {start_time} < arrival {arrival}"
            
            # Check that finish_time > start_time
            assert finish_time > start_time, f"Process {pid}: finish_time {finish_time} <= start_time {start_time}"
            
            # Check that turnaround = finish_time - arrival
            assert turnaround == finish_time - arrival, f"Process {pid}: turnaround calculation incorrect"
            
            # Check that wait = turnaround - burst
            assert wait == turnaround - burst, f"Process {pid}: wait calculation incorrect"
            
            # Check that wait >= 0 (process can't have negative wait time)
            assert wait >= 0, f"Process {pid}: negative wait time {wait}"
        
        # Verify averages are calculated correctly
        process_turnarounds = [p['turnaround'] for p in results['processes']]
        process_waits = [p['wait'] for p in results['processes']]
        
        expected_avg_turnaround = sum(process_turnarounds) / len(process_turnarounds)
        expected_avg_wait = sum(process_waits) / len(process_waits)
        
        assert abs(results['avg_turnaround'] - expected_avg_turnaround) < 1e-10
        assert abs(results['avg_wait'] - expected_avg_wait) < 1e-10
    
    def test_logging_functionality(self):
        """Test that logging works correctly."""
        processes = [
            Process(pid=1, size=64, arrival=0, burst=1, remaining=1),
            Process(pid=2, size=128, arrival=1, burst=1, remaining=1)
        ]
        
        # Test INFO level
        simulator_info = MemorySimulator(log_level="INFO")
        results_info = simulator_info.run_simulation(processes)
        assert len(results_info['processes']) == 2
        
        # Test DEBUG level
        simulator_debug = MemorySimulator(log_level="DEBUG")
        results_debug = simulator_debug.run_simulation(processes)
        assert len(results_debug['processes']) == 2
        
        # Both should complete successfully
        assert results_info['avg_turnaround'] > 0
        assert results_debug['avg_turnaround'] > 0
