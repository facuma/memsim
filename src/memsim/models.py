"""
Data models for memory simulation.

This module defines the core data structures used throughout the simulation,
including Process, Partition, and other essential entities.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class State(Enum):
    """Process states in the simulation."""
    NEW = "NEW"
    READY = "READY"
    READY_SUSP = "READY_SUSP"
    RUNNING = "RUNNING"
    TERMINATED = "TERMINATED"


@dataclass
class Process:
    """
    Represents a process in the memory simulation.
    
    Attributes:
        pid: Process identifier
        size: Memory size required by the process
        arrival: Time when the process arrives
        burst: CPU burst time for the process
        remaining: Remaining burst time (default: 0)
        start_time: Time when the process started execution (default: None)
        finish_time: Time when the process finished execution (default: None)
        state: Current state of the process (default: State.NEW)
    """
    pid: int
    size: int
    arrival: int
    burst: int
    remaining: int = 0
    start_time: Optional[int] = None
    finish_time: Optional[int] = None
    state: State = State.NEW
    
    def to_row(self) -> dict:
        """
        Convert process to dictionary for logging purposes.
        
        Returns:
            dict: Dictionary representation of the process
        """
        return {
            'pid': self.pid,
            'size': self.size,
            'arrival': self.arrival,
            'burst': self.burst,
            'remaining': self.remaining,
            'start_time': self.start_time,
            'finish_time': self.finish_time,
            'state': self.state.value
        }


@dataclass
class Partition:
    """
    Represents a memory partition in the system.
    
    Attributes:
        id: Unique identifier for the partition
        start: Starting memory address
        size: Size of the partition
        pid_assigned: ID of the process assigned to this partition (default: None)
    """
    id: str
    start: int
    size: int
    pid_assigned: Optional[int] = None
    
    @property
    def is_free(self) -> bool:
        """
        Check if the partition is free (not assigned to any process).
        
        Returns:
            bool: True if partition is free, False otherwise
        """
        return self.pid_assigned is None
    
    def frag_interna(self, process_size: int) -> int:
        """
        Calculate internal fragmentation for a given process size.
        
        Args:
            process_size: Size of the process to be allocated
            
        Returns:
            int: Internal fragmentation (wasted space) if this partition
                 were assigned to a process of the given size
        """
        if self.is_free:
            return 0
        return max(0, self.size - process_size)


def throughput(finished: int, total_time: int) -> float:
    """
    Calculate throughput as processes completed per unit time.
    
    Args:
        finished: Number of processes that finished execution
        total_time: Total simulation time
        
    Returns:
        float: Throughput (processes per unit time), or 0.0 if total_time is 0
    """
    if total_time == 0:
        return 0.0
    return finished / total_time
