"""
Tests for the scheduler module.

This module contains unit tests for process scheduling algorithms and management.
"""

import pytest
from src.memsim.scheduler import Scheduler, ProcessScheduler, ReadyQueue, schedule_processes, calculate_metrics
from src.memsim.models import Process, State


class TestScheduler:
    """Test cases for the Scheduler class."""
    
    def test_scheduler_initialization(self):
        """Test Scheduler initialization with empty queues."""
        scheduler = Scheduler()
        
        assert scheduler.ready_heap == []
        assert len(scheduler.ready_susp) == 0
        assert scheduler.running is None
        assert scheduler.tiebreak_counter == 0
    
    def test_push_ready_insertion_order(self):
        """Test push_ready maintains order by remaining time."""
        scheduler = Scheduler()
        
        # Create processes with different remaining times
        proc1 = Process(pid=1, size=64, arrival=0, burst=10, remaining=5)
        proc2 = Process(pid=2, size=128, arrival=1, burst=8, remaining=3)
        proc3 = Process(pid=3, size=256, arrival=2, burst=12, remaining=7)
        
        # Insert in arbitrary order
        scheduler.push_ready(proc1)  # remaining=5, tiebreak=0
        scheduler.push_ready(proc3)  # remaining=7, tiebreak=1
        scheduler.push_ready(proc2)  # remaining=3, tiebreak=2
        
        # Should be ordered by remaining time (3, 5, 7)
        assert scheduler.pop_ready_min().pid == 2  # remaining=3
        assert scheduler.pop_ready_min().pid == 1  # remaining=5
        assert scheduler.pop_ready_min().pid == 3  # remaining=7
        assert scheduler.pop_ready_min() is None   # empty
    
    def test_tiebreak_fifo_order(self):
        """Test that ties in remaining time are resolved by FIFO order."""
        scheduler = Scheduler()
        
        # Create processes with same remaining time
        proc1 = Process(pid=1, size=64, arrival=0, burst=10, remaining=5)
        proc2 = Process(pid=2, size=128, arrival=1, burst=8, remaining=5)
        proc3 = Process(pid=3, size=256, arrival=2, burst=12, remaining=5)
        
        # Insert in order
        scheduler.push_ready(proc1)  # remaining=5, tiebreak=0
        scheduler.push_ready(proc2)  # remaining=5, tiebreak=1
        scheduler.push_ready(proc3)  # remaining=5, tiebreak=2
        
        # Should maintain FIFO order (1, 2, 3)
        assert scheduler.pop_ready_min().pid == 1
        assert scheduler.pop_ready_min().pid == 2
        assert scheduler.pop_ready_min().pid == 3
    
    def test_pop_ready_min_empty_queue(self):
        """Test pop_ready_min with empty queue."""
        scheduler = Scheduler()
        
        assert scheduler.pop_ready_min() is None
    
    def test_peek_ready_min(self):
        """Test peek_ready_min without removing process."""
        scheduler = Scheduler()
        
        proc1 = Process(pid=1, size=64, arrival=0, burst=10, remaining=5)
        proc2 = Process(pid=2, size=128, arrival=1, burst=8, remaining=3)
        
        scheduler.push_ready(proc1)
        scheduler.push_ready(proc2)
        
        # Peek should return process with min remaining (proc2)
        peeked = scheduler.peek_ready_min()
        assert peeked.pid == 2
        assert peeked.remaining == 3
        
        # Queue should still have both processes
        assert len(scheduler.ready_heap) == 2
        
        # Pop should still return the same process
        popped = scheduler.pop_ready_min()
        assert popped.pid == 2
    
    def test_peek_ready_min_empty_queue(self):
        """Test peek_ready_min with empty queue."""
        scheduler = Scheduler()
        
        assert scheduler.peek_ready_min() is None
    
    def test_enqueue_dequeue_suspended(self):
        """Test suspended queue FIFO behavior."""
        scheduler = Scheduler()
        
        proc1 = Process(pid=1, size=64, arrival=0, burst=10, remaining=5)
        proc2 = Process(pid=2, size=128, arrival=1, burst=8, remaining=3)
        proc3 = Process(pid=3, size=256, arrival=2, burst=12, remaining=7)
        
        # Enqueue in order
        scheduler.enqueue_suspended(proc1)
        scheduler.enqueue_suspended(proc2)
        scheduler.enqueue_suspended(proc3)
        
        # Dequeue should maintain FIFO order
        assert scheduler.dequeue_suspended().pid == 1
        assert scheduler.dequeue_suspended().pid == 2
        assert scheduler.dequeue_suspended().pid == 3
        assert scheduler.dequeue_suspended() is None
    
    def test_dequeue_suspended_empty_queue(self):
        """Test dequeue_suspended with empty queue."""
        scheduler = Scheduler()
        
        assert scheduler.dequeue_suspended() is None
    
    def test_preempt_if_needed_no_running_process(self):
        """Test preempt_if_needed when no process is running."""
        scheduler = Scheduler()
        
        # No running process, should not preempt
        assert scheduler.preempt_if_needed(1) is False
        assert scheduler.preempt_if_needed(0) is False
    
    def test_preempt_if_needed_should_preempt(self):
        """Test preempt_if_needed when preemption is needed."""
        scheduler = Scheduler()
        
        # Set running process with remaining=5
        running_proc = Process(pid=1, size=64, arrival=0, burst=10, remaining=5)
        scheduler.running = running_proc
        
        # Incoming process with remaining=3 should preempt
        assert scheduler.preempt_if_needed(3) is True
        
        # Incoming process with remaining=5 should not preempt (equal)
        assert scheduler.preempt_if_needed(5) is False
        
        # Incoming process with remaining=7 should not preempt
        assert scheduler.preempt_if_needed(7) is False
    
    def test_preempt_if_needed_edge_cases(self):
        """Test preempt_if_needed edge cases."""
        scheduler = Scheduler()
        
        # Running process with remaining=0
        running_proc = Process(pid=1, size=64, arrival=0, burst=10, remaining=0)
        scheduler.running = running_proc
        
        # Should not preempt when incoming has same remaining time
        assert scheduler.preempt_if_needed(0) is False
        
        # Should not preempt when incoming has more remaining time
        assert scheduler.preempt_if_needed(1) is False
    
    def test_count_in_memory_empty(self):
        """Test count_in_memory with no processes."""
        scheduler = Scheduler()
        
        assert scheduler.count_in_memory() == 0
    
    def test_count_in_memory_with_ready_processes(self):
        """Test count_in_memory with processes in ready queue."""
        scheduler = Scheduler()
        
        proc1 = Process(pid=1, size=64, arrival=0, burst=10, remaining=5)
        proc2 = Process(pid=2, size=128, arrival=1, burst=8, remaining=3)
        
        scheduler.push_ready(proc1)
        scheduler.push_ready(proc2)
        
        assert scheduler.count_in_memory() == 2
    
    def test_count_in_memory_with_running_process(self):
        """Test count_in_memory with running process."""
        scheduler = Scheduler()
        
        running_proc = Process(pid=1, size=64, arrival=0, burst=10, remaining=5)
        scheduler.running = running_proc
        
        assert scheduler.count_in_memory() == 1
    
    def test_count_in_memory_with_both_ready_and_running(self):
        """Test count_in_memory with both ready and running processes."""
        scheduler = Scheduler()
        
        # Add ready processes
        proc1 = Process(pid=1, size=64, arrival=0, burst=10, remaining=5)
        proc2 = Process(pid=2, size=128, arrival=1, burst=8, remaining=3)
        scheduler.push_ready(proc1)
        scheduler.push_ready(proc2)
        
        # Add running process
        running_proc = Process(pid=3, size=256, arrival=2, burst=12, remaining=7)
        scheduler.running = running_proc
        
        assert scheduler.count_in_memory() == 3
    
    def test_complex_scheduling_scenario(self):
        """Test complex scenario with multiple operations."""
        scheduler = Scheduler()
        
        # Create processes
        proc1 = Process(pid=1, size=64, arrival=0, burst=10, remaining=8)
        proc2 = Process(pid=2, size=128, arrival=1, burst=5, remaining=3)
        proc3 = Process(pid=3, size=256, arrival=2, burst=12, remaining=6)
        proc4 = Process(pid=4, size=512, arrival=3, burst=7, remaining=4)
        
        # Add to ready queue
        scheduler.push_ready(proc1)  # remaining=8, tiebreak=0
        scheduler.push_ready(proc3)  # remaining=6, tiebreak=1
        scheduler.push_ready(proc2)  # remaining=3, tiebreak=2
        scheduler.push_ready(proc4)  # remaining=4, tiebreak=3
        
        # Check ordering: 3, 4, 6, 8
        assert scheduler.pop_ready_min().pid == 2  # remaining=3
        assert scheduler.pop_ready_min().pid == 4  # remaining=4
        assert scheduler.pop_ready_min().pid == 3  # remaining=6
        assert scheduler.pop_ready_min().pid == 1  # remaining=8
        
        # Test suspended queue
        scheduler.enqueue_suspended(proc1)
        scheduler.enqueue_suspended(proc2)
        
        assert scheduler.dequeue_suspended().pid == 1
        assert scheduler.dequeue_suspended().pid == 2
        
        # Test preemption
        scheduler.running = proc3  # remaining=6
        assert scheduler.preempt_if_needed(2) is True   # 2 < 6
        assert scheduler.preempt_if_needed(6) is False  # 6 == 6
        assert scheduler.preempt_if_needed(8) is False  # 8 > 6


class TestProcessScheduler:
    """Test cases for the ProcessScheduler class."""
    
    def test_scheduler_initialization(self):
        """Test ProcessScheduler initialization."""
        scheduler = ProcessScheduler()
        assert scheduler is not None


class TestReadyQueue:
    """Test cases for the ReadyQueue class."""
    
    def test_queue_initialization(self):
        """Test ReadyQueue initialization."""
        queue = ReadyQueue()
        assert queue is not None


class TestSchedulerFunctions:
    """Test cases for scheduler module functions."""
    
    def test_schedule_processes_function(self):
        """Test the schedule_processes function."""
        # Function is not implemented yet, so just test it exists
        assert schedule_processes is not None
    
    def test_calculate_metrics_function(self):
        """Test the calculate_metrics function."""
        # Function is not implemented yet, so just test it exists
        assert calculate_metrics is not None
