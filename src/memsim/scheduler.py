"""
Process scheduling algorithms and management.

This module implements various CPU scheduling algorithms such as:
- First Come First Served (FCFS)
- Shortest Job First (SJF)
- Round Robin (RR)
- Priority Scheduling
"""

import heapq
from collections import deque
from typing import Optional, List, Tuple
from .models import Process


class Scheduler:
    """
    Manages process scheduling using priority queues and FIFO queues.
    
    Uses heapq for ready queue (priority by remaining time) and collections.deque
    for ready_susp queue (FIFO). Implements preemptive scheduling based on
    remaining burst time.
    """
    
    def __init__(self):
        """Initialize the scheduler with empty queues."""
        self.ready_heap: List[Tuple[int, int, int, Process]] = []  # (remaining, tiebreak, pid, Process)
        self.ready_susp: deque = deque()  # FIFO queue for suspended processes
        self.running: Optional[Process] = None
        self.tiebreak_counter: int = 0
    
    def push_ready(self, proc: Process) -> None:
        """
        Insert a process into the ready queue with priority based on remaining time.
        
        Args:
            proc: Process to insert into ready queue
        """
        # Use negative remaining time for min-heap behavior (smallest remaining first)
        # Tiebreak ensures FIFO order for processes with same remaining time
        heapq.heappush(self.ready_heap, (proc.remaining, self.tiebreak_counter, proc.pid, proc))
        self.tiebreak_counter += 1
    
    def pop_ready_min(self) -> Optional[Process]:
        """
        Remove and return the process with minimum remaining time from ready queue.
        
        Returns:
            Process: Process with minimum remaining time, or None if queue is empty
        """
        if not self.ready_heap:
            return None
        
        _, _, _, process = heapq.heappop(self.ready_heap)
        return process
    
    def peek_ready_min(self) -> Optional[Process]:
        """
        Return the process with minimum remaining time without removing it.
        
        Returns:
            Process: Process with minimum remaining time, or None if queue is empty
        """
        if not self.ready_heap:
            return None
        
        _, _, _, process = self.ready_heap[0]
        return process
    
    def enqueue_suspended(self, proc: Process) -> None:
        """
        Add a process to the suspended ready queue (FIFO).
        
        Args:
            proc: Process to add to suspended queue
        """
        self.ready_susp.append(proc)
    
    def dequeue_suspended(self) -> Optional[Process]:
        """
        Remove and return the first process from suspended ready queue (FIFO).
        
        Returns:
            Process: First process in suspended queue, or None if queue is empty
        """
        if not self.ready_susp:
            return None
        
        return self.ready_susp.popleft()
    
    def preempt_if_needed(self, incoming_min_remaining: int) -> bool:
        """
        Check if current running process should be preempted.
        
        Args:
            incoming_min_remaining: Minimum remaining time of incoming processes
            
        Returns:
            bool: True if running process should be preempted, False otherwise
        """
        if self.running is None:
            return False
        
        # Preempt if incoming process has less remaining time
        return incoming_min_remaining < self.running.remaining
    
    def count_in_memory(self) -> int:
        """
        Count total processes currently in memory (ready + running).
        
        Returns:
            int: Number of processes in memory
        """
        return len(self.ready_heap) + (1 if self.running is not None else 0)


class ProcessScheduler:
    """
    Manages process scheduling and CPU allocation.
    
    This class implements different scheduling algorithms and manages
    the ready queue and process execution order.
    """
    pass


class ReadyQueue:
    """
    Manages the ready queue of processes waiting for CPU.
    
    This class handles the insertion, removal, and ordering of processes
    based on the scheduling algorithm being used.
    """
    pass


def schedule_processes(processes, algorithm="fcfs"):
    """
    Schedule a list of processes using the specified algorithm.
    
    Args:
        processes: List of Process objects to schedule
        algorithm: Scheduling algorithm to use
        
    Returns:
        list: Ordered list of processes for execution
    """
    pass


def calculate_metrics(processes):
    """
    Calculate scheduling metrics for the processes.
    
    Args:
        processes: List of scheduled processes
        
    Returns:
        dict: Dictionary containing average waiting time, turnaround time, etc.
    """
    pass
