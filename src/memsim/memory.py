"""
Memory management operations and algorithms.

This module implements various memory allocation strategies such as:
- First Fit
- Best Fit
- Worst Fit
- Next Fit

It also handles memory fragmentation and compaction.
"""

from typing import Optional, Dict, List
from .models import Partition


class MemoryManager:
    """
    Manages memory allocation and deallocation using different strategies.
    
    This class manages three partitions (excluding OS reserved space):
    - P1: start=100, size=250
    - P2: start=350, size=150  
    - P3: start=500, size=50
    
    Invariant: Each partition contains 0 or 1 process; OS 100K is reserved and outside these partitions.
    """
    
    def __init__(self):
        """Initialize MemoryManager with three partitions."""
        self.partitions = [
            Partition(id="P1", start=100, size=250),
            Partition(id="P2", start=350, size=150),
            Partition(id="P3", start=500, size=50)
        ]
    
    def best_fit(self, size: int) -> Optional[Partition]:
        """
        Find the smallest free partition that can accommodate the given size.
        
        Args:
            size: Size of memory required by the process
            
        Returns:
            Partition: The smallest free partition with size >= required size, or None if no suitable partition found
        """
        suitable_partitions = [p for p in self.partitions if p.is_free and p.size >= size]
        
        if not suitable_partitions:
            return None
            
        # Return the partition with the smallest size among suitable ones
        return min(suitable_partitions, key=lambda p: p.size)
    
    def assign(self, part: Partition, pid: int) -> None:
        """
        Assign a partition to a process.
        
        Args:
            part: The partition to assign
            pid: Process ID to assign to the partition
        """
        part.pid_assigned = pid
    
    def release(self, pid: int) -> None:
        """
        Release the partition assigned to the given process ID.
        
        Args:
            pid: Process ID whose partition should be released
        """
        for partition in self.partitions:
            if partition.pid_assigned == pid:
                partition.pid_assigned = None
                break
    
    def table_snapshot(self, process_sizes: Dict[int, int]) -> List[Dict]:
        """
        Generate a snapshot of the memory table for display.
        
        Args:
            process_sizes: Dictionary mapping process IDs to their sizes
            
        Returns:
            List[Dict]: List of dictionaries containing partition information
                      with keys: {id, start, size, pid, frag_interna}
        """
        snapshot = []
        
        for partition in self.partitions:
            pid = partition.pid_assigned
            frag_interna = 0
            
            if pid is not None and pid in process_sizes:
                # Calculate internal fragmentation: partition_size - process_size
                frag_interna = partition.size - process_sizes[pid]
            elif pid is not None:
                # If process size not found, assume no fragmentation
                frag_interna = 0
            
            snapshot.append({
                'id': partition.id,
                'start': partition.start,
                'size': partition.size,
                'pid': pid,
                'frag_interna': frag_interna,
                'free': partition.is_free
            })
        
        return snapshot


class MemoryCompactor:
    """
    Handles memory compaction to reduce fragmentation.
    
    This class manages the compaction of memory blocks to minimize
    external fragmentation.
    """
    pass


def allocate_memory(process, strategy="first_fit"):
    """
    Allocate memory for a process using the specified strategy.
    
    Args:
        process: Process object requiring memory
        strategy: Allocation strategy to use
        
    Returns:
        bool: True if allocation successful, False otherwise
    """
    pass


def deallocate_memory(process_id):
    """
    Deallocate memory for a process.
    
    Args:
        process_id: ID of the process to deallocate
        
    Returns:
        bool: True if deallocation successful, False otherwise
    """
    pass
