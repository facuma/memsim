"""
Tests for the models module.

This module contains unit tests for the data models used in the simulation.
"""

import pytest
import tempfile
import os
from src.memsim.models import Process, Partition, State, throughput
from src.memsim.io import read_processes_csv, pretty_print_state


class TestState:
    """Test cases for the State enum."""
    
    def test_state_values(self):
        """Test that State enum has correct values."""
        assert State.NEW.value == "NEW"
        assert State.READY.value == "READY"
        assert State.READY_SUSP.value == "READY_SUSP"
        assert State.RUNNING.value == "RUNNING"
        assert State.TERMINATED.value == "TERMINATED"


class TestProcess:
    """Test cases for the Process class."""
    
    def test_process_creation_with_defaults(self):
        """Test creating a Process with default values."""
        process = Process(pid=1, size=64, arrival=0, burst=5)
        
        assert process.pid == 1
        assert process.size == 64
        assert process.arrival == 0
        assert process.burst == 5
        assert process.remaining == 0
        assert process.start_time is None
        assert process.finish_time is None
        assert process.state == State.NEW
    
    def test_process_creation_with_all_values(self):
        """Test creating a Process with all values specified."""
        process = Process(
            pid=2, 
            size=128, 
            arrival=5, 
            burst=10,
            remaining=8,
            start_time=6,
            finish_time=16,
            state=State.RUNNING
        )
        
        assert process.pid == 2
        assert process.size == 128
        assert process.arrival == 5
        assert process.burst == 10
        assert process.remaining == 8
        assert process.start_time == 6
        assert process.finish_time == 16
        assert process.state == State.RUNNING
    
    def test_process_to_row(self):
        """Test Process.to_row() method."""
        process = Process(
            pid=3,
            size=256,
            arrival=10,
            burst=15,
            remaining=12,
            start_time=11,
            finish_time=26,
            state=State.TERMINATED
        )
        
        row = process.to_row()
        
        expected = {
            'pid': 3,
            'size': 256,
            'arrival': 10,
            'burst': 15,
            'remaining': 12,
            'start_time': 11,
            'finish_time': 26,
            'state': 'TERMINATED'
        }
        
        assert row == expected
    
    def test_process_state_transitions(self):
        """Test basic state transitions by manual setting."""
        process = Process(pid=1, size=64, arrival=0, burst=5)
        
        # Test initial state
        assert process.state == State.NEW
        
        # Test state transitions
        process.state = State.READY
        assert process.state == State.READY
        
        process.state = State.RUNNING
        assert process.state == State.RUNNING
        
        process.state = State.TERMINATED
        assert process.state == State.TERMINATED
        
        process.state = State.READY_SUSP
        assert process.state == State.READY_SUSP


class TestPartition:
    """Test cases for the Partition class."""
    
    def test_partition_creation_with_defaults(self):
        """Test creating a Partition with default values."""
        partition = Partition(id="P1", start=0, size=1024)
        
        assert partition.id == "P1"
        assert partition.start == 0
        assert partition.size == 1024
        assert partition.pid_assigned is None
    
    def test_partition_creation_with_assigned_process(self):
        """Test creating a Partition with assigned process."""
        partition = Partition(id="P2", start=512, size=2048, pid_assigned=5)
        
        assert partition.id == "P2"
        assert partition.start == 512
        assert partition.size == 2048
        assert partition.pid_assigned == 5
    
    def test_partition_is_free_property(self):
        """Test Partition.is_free property."""
        # Free partition
        free_partition = Partition(id="P1", start=0, size=1024)
        assert free_partition.is_free is True
        
        # Assigned partition
        assigned_partition = Partition(id="P2", start=0, size=1024, pid_assigned=1)
        assert assigned_partition.is_free is False
    
    def test_partition_frag_interna_free_partition(self):
        """Test frag_interna for free partition."""
        partition = Partition(id="P1", start=0, size=1024)
        
        # Free partition should return 0 fragmentation
        assert partition.frag_interna(512) == 0
        assert partition.frag_interna(1024) == 0
        assert partition.frag_interna(2048) == 0
    
    def test_partition_frag_interna_assigned_partition(self):
        """Test frag_interna for assigned partition."""
        partition = Partition(id="P1", start=0, size=1024, pid_assigned=1)
        
        # Test different process sizes
        assert partition.frag_interna(512) == 512  # 1024 - 512 = 512
        assert partition.frag_interna(1024) == 0   # 1024 - 1024 = 0
        assert partition.frag_interna(800) == 224   # 1024 - 800 = 224
        assert partition.frag_interna(1500) == 0    # max(0, 1024 - 1500) = 0
    
    def test_partition_frag_interna_edge_cases(self):
        """Test frag_interna edge cases."""
        partition = Partition(id="P1", start=0, size=100, pid_assigned=1)
        
        # Process size equals partition size
        assert partition.frag_interna(100) == 0
        
        # Process size larger than partition size
        assert partition.frag_interna(150) == 0
        
        # Process size zero
        assert partition.frag_interna(0) == 100


class TestThroughput:
    """Test cases for the throughput function."""
    
    def test_throughput_normal_case(self):
        """Test throughput calculation with normal values."""
        result = throughput(finished=10, total_time=20)
        assert result == 0.5  # 10/20 = 0.5
    
    def test_throughput_zero_finished(self):
        """Test throughput with zero finished processes."""
        result = throughput(finished=0, total_time=10)
        assert result == 0.0  # 0/10 = 0.0
    
    def test_throughput_zero_total_time(self):
        """Test throughput with zero total time (edge case)."""
        result = throughput(finished=5, total_time=0)
        assert result == 0.0  # Should return 0.0 when total_time is 0
    
    def test_throughput_both_zero(self):
        """Test throughput with both finished and total_time zero."""
        result = throughput(finished=0, total_time=0)
        assert result == 0.0
    
    def test_throughput_high_values(self):
        """Test throughput with high values."""
        result = throughput(finished=1000, total_time=500)
        assert result == 2.0  # 1000/500 = 2.0
    
    def test_throughput_fractional_result(self):
        """Test throughput with fractional result."""
        result = throughput(finished=3, total_time=7)
        assert abs(result - 0.42857142857142855) < 1e-10  # 3/7 ≈ 0.42857142857142855


class TestIO:
    """Test cases for IO module functions."""
    
    def test_read_processes_csv_basic(self):
        """Test reading processes from CSV file."""
        # Create temporary CSV file
        csv_content = "pid,size,arrival,burst\n1,64,0,5\n2,128,2,8\n3,32,1,3\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            processes = read_processes_csv(temp_path)
            
            # Should have 3 processes
            assert len(processes) == 3
            
            # Should be sorted by arrival, then pid
            assert processes[0].pid == 1  # arrival=0, pid=1
            assert processes[1].pid == 3  # arrival=1, pid=3
            assert processes[2].pid == 2  # arrival=2, pid=2
            
            # Check that remaining=burst
            assert processes[0].remaining == 5
            assert processes[1].remaining == 3
            assert processes[2].remaining == 8
            
        finally:
            os.unlink(temp_path)
    
    def test_read_processes_csv_file_not_found(self):
        """Test reading non-existent CSV file."""
        with pytest.raises(FileNotFoundError):
            read_processes_csv("nonexistent.csv")
    
    def test_pretty_print_state_basic(self):
        """Test basic pretty_print_state formatting."""
        # Create test data
        running = Process(pid=1, size=64, arrival=0, burst=5, remaining=3)
        
        mem_table = [
            {'id': 'P1', 'start': 100, 'size': 250, 'pid': 1, 'frag_interna': 186},
            {'id': 'P2', 'start': 350, 'size': 150, 'pid': None, 'frag_interna': 0}
        ]
        
        ready = [
            Process(pid=2, size=128, arrival=1, burst=8, remaining=6),
            Process(pid=3, size=256, arrival=2, burst=12, remaining=4)
        ]
        
        ready_susp = [
            Process(pid=4, size=512, arrival=3, burst=10, remaining=7)
        ]
        
        result = pretty_print_state(5, running, mem_table, ready, ready_susp)
        
        # Check that result contains expected elements
        assert "t=5 | CPU: pid=1" in result
        assert "Memory:" in result
        assert "P1" in result
        assert "P2" in result
        assert "Ready:" in result
        assert "pid=2(rem=6)" in result
        assert "pid=3(rem=4)" in result
        assert "Ready_susp:" in result
        assert "pid=4(size=512)" in result
    
    def test_pretty_print_state_idle_cpu(self):
        """Test pretty_print_state with idle CPU."""
        result = pretty_print_state(10, None, [], [], [])
        
        assert "t=10 | CPU: IDLE" in result
        assert "(no memory partitions)" in result
        assert "(empty)" in result
    
    def test_pretty_print_state_empty_queues(self):
        """Test pretty_print_state with empty queues."""
        running = Process(pid=1, size=64, arrival=0, burst=5, remaining=2)
        mem_table = [{'id': 'P1', 'start': 100, 'size': 250, 'pid': 1, 'frag_interna': 186}]
        
        result = pretty_print_state(3, running, mem_table, [], [])
        
        assert "t=3 | CPU: pid=1" in result
        assert "Ready:" in result
        assert "(empty)" in result
        assert "Ready_susp:" in result
        assert "(empty)" in result
