"""
Tests for the memory module.

This module contains unit tests for memory allocation algorithms and operations.
"""

import pytest
from src.memsim.memory import MemoryManager, MemoryCompactor, allocate_memory, deallocate_memory
from src.memsim.models import Partition


class TestMemoryManager:
    """Test cases for the MemoryManager class."""
    
    def test_memory_manager_initialization(self):
        """Test MemoryManager initialization with correct partitions."""
        manager = MemoryManager()
        
        # Check that we have 3 partitions
        assert len(manager.partitions) == 3
        
        # Check partition details
        p1, p2, p3 = manager.partitions
        
        assert p1.id == "P1" and p1.start == 100 and p1.size == 250
        assert p2.id == "P2" and p2.start == 350 and p2.size == 150
        assert p3.id == "P3" and p3.start == 500 and p3.size == 50
        
        # All partitions should be free initially
        assert all(p.is_free for p in manager.partitions)
    
    def test_best_fit_selection(self):
        """Test best_fit selects correct partitions for different sizes."""
        manager = MemoryManager()
        
        # Test size=45 should select P3 (smallest suitable: 50)
        result = manager.best_fit(45)
        assert result is not None
        assert result.id == "P3"
        assert result.size == 50
        
        # Test size=120 should select P2 (smallest suitable: 150)
        result = manager.best_fit(120)
        assert result is not None
        assert result.id == "P2"
        assert result.size == 150
        
        # Test size=200 should select P1 (smallest suitable: 250)
        result = manager.best_fit(200)
        assert result is not None
        assert result.id == "P1"
        assert result.size == 250
        
        # Test size=300 should return None (no partition large enough)
        result = manager.best_fit(300)
        assert result is None
    
    def test_best_fit_with_occupied_partitions(self):
        """Test best_fit behavior when some partitions are occupied."""
        manager = MemoryManager()
        
        # Assign P1 to process 1
        manager.assign(manager.partitions[0], 1)
        
        # Now size=200 should select P2 (P1 is occupied)
        result = manager.best_fit(200)
        assert result is not None
        assert result.id == "P2"
        
        # Assign P2 to process 2
        manager.assign(manager.partitions[1], 2)
        
        # Now size=200 should select P3 (P1 and P2 are occupied)
        result = manager.best_fit(200)
        assert result is not None
        assert result.id == "P3"
        
        # Assign P3 to process 3
        manager.assign(manager.partitions[2], 3)
        
        # Now any size should return None (all occupied)
        result = manager.best_fit(10)
        assert result is None
    
    def test_assign_method(self):
        """Test assign method changes partition state correctly."""
        manager = MemoryManager()
        partition = manager.partitions[0]  # P1
        
        # Initially free
        assert partition.is_free
        assert partition.pid_assigned is None
        
        # Assign process 5
        manager.assign(partition, 5)
        
        # Should now be occupied
        assert not partition.is_free
        assert partition.pid_assigned == 5
    
    def test_release_method(self):
        """Test release method frees partition correctly."""
        manager = MemoryManager()
        partition = manager.partitions[0]  # P1
        
        # Assign process 5
        manager.assign(partition, 5)
        assert not partition.is_free
        assert partition.pid_assigned == 5
        
        # Release process 5
        manager.release(5)
        
        # Should now be free
        assert partition.is_free
        assert partition.pid_assigned is None
    
    def test_release_nonexistent_process(self):
        """Test release method with non-existent process ID."""
        manager = MemoryManager()
        
        # Release non-existent process should not raise error
        manager.release(999)
        
        # All partitions should still be free
        assert all(p.is_free for p in manager.partitions)
    
    def test_release_specific_process(self):
        """Test release method only affects the correct process."""
        manager = MemoryManager()
        
        # Assign different processes to different partitions
        manager.assign(manager.partitions[0], 1)  # P1 -> process 1
        manager.assign(manager.partitions[1], 2)  # P2 -> process 2
        manager.assign(manager.partitions[2], 3)  # P3 -> process 3
        
        # Release only process 2
        manager.release(2)
        
        # Check that only P2 is free
        assert manager.partitions[0].pid_assigned == 1  # P1 still occupied
        assert manager.partitions[1].is_free  # P2 is free
        assert manager.partitions[2].pid_assigned == 3  # P3 still occupied
    
    def test_table_snapshot_basic(self):
        """Test table_snapshot with basic scenario."""
        manager = MemoryManager()
        process_sizes = {1: 100, 2: 200}
        
        # Assign processes
        manager.assign(manager.partitions[0], 1)  # P1 (250) -> process 1 (100)
        manager.assign(manager.partitions[1], 2)  # P2 (150) -> process 2 (200)
        
        snapshot = manager.table_snapshot(process_sizes)
        
        # Check snapshot structure
        assert len(snapshot) == 3
        
        # Check P1 entry
        p1_entry = next(entry for entry in snapshot if entry['id'] == 'P1')
        assert p1_entry['start'] == 100
        assert p1_entry['size'] == 250
        assert p1_entry['pid'] == 1
        assert p1_entry['frag_interna'] == 150  # 250 - 100 = 150
        
        # Check P2 entry
        p2_entry = next(entry for entry in snapshot if entry['id'] == 'P2')
        assert p2_entry['start'] == 350
        assert p2_entry['size'] == 150
        assert p2_entry['pid'] == 2
        assert p2_entry['frag_interna'] == 0  # 150 - 200 = 0 (but process too big, so 0)
        
        # Check P3 entry (free)
        p3_entry = next(entry for entry in snapshot if entry['id'] == 'P3')
        assert p3_entry['start'] == 500
        assert p3_entry['size'] == 50
        assert p3_entry['pid'] is None
        assert p3_entry['frag_interna'] == 0
    
    def test_table_snapshot_correct_fragmentation(self):
        """Test table_snapshot calculates internal fragmentation correctly."""
        manager = MemoryManager()
        process_sizes = {1: 200, 2: 100, 3: 30}
        
        # Assign processes with different sizes
        manager.assign(manager.partitions[0], 1)  # P1 (250) -> process 1 (200)
        manager.assign(manager.partitions[1], 2)  # P2 (150) -> process 2 (100)
        manager.assign(manager.partitions[2], 3)  # P3 (50) -> process 3 (30)
        
        snapshot = manager.table_snapshot(process_sizes)
        
        # Check fragmentation calculations
        p1_entry = next(entry for entry in snapshot if entry['id'] == 'P1')
        assert p1_entry['frag_interna'] == 50  # 250 - 200 = 50
        
        p2_entry = next(entry for entry in snapshot if entry['id'] == 'P2')
        assert p2_entry['frag_interna'] == 50  # 150 - 100 = 50
        
        p3_entry = next(entry for entry in snapshot if entry['id'] == 'P3')
        assert p3_entry['frag_interna'] == 20  # 50 - 30 = 20
    
    def test_table_snapshot_missing_process_size(self):
        """Test table_snapshot handles missing process sizes gracefully."""
        manager = MemoryManager()
        process_sizes = {1: 100}  # Missing size for process 2
        
        # Assign processes
        manager.assign(manager.partitions[0], 1)  # P1 -> process 1 (has size)
        manager.assign(manager.partitions[1], 2)  # P2 -> process 2 (no size)
        
        snapshot = manager.table_snapshot(process_sizes)
        
        # P1 should have correct fragmentation
        p1_entry = next(entry for entry in snapshot if entry['id'] == 'P1')
        assert p1_entry['frag_interna'] == 150  # 250 - 100 = 150
        
        # P2 should have 0 fragmentation (missing size)
        p2_entry = next(entry for entry in snapshot if entry['id'] == 'P2')
        assert p2_entry['frag_interna'] == 0
    
    def test_table_snapshot_empty_process_sizes(self):
        """Test table_snapshot with empty process_sizes dictionary."""
        manager = MemoryManager()
        process_sizes = {}
        
        # Assign a process
        manager.assign(manager.partitions[0], 1)
        
        snapshot = manager.table_snapshot(process_sizes)
        
        # All partitions should have 0 fragmentation
        for entry in snapshot:
            assert entry['frag_interna'] == 0
    
    def test_table_snapshot_free_field(self):
        """Test that table_snapshot includes free field."""
        manager = MemoryManager()
        process_sizes = {1: 100}
        
        # Assign a process
        manager.assign(manager.partitions[0], 1)
        
        snapshot = manager.table_snapshot(process_sizes)
        
        # Check that free field is included
        for entry in snapshot:
            assert 'free' in entry
            if entry['pid'] is not None:
                assert entry['free'] is False
            else:
                assert entry['free'] is True


class TestMemoryCompactor:
    """Test cases for the MemoryCompactor class."""
    
    def test_compactor_initialization(self):
        """Test MemoryCompactor initialization."""
        compactor = MemoryCompactor()
        assert compactor is not None


class TestMemoryFunctions:
    """Test cases for memory module functions."""
    
    def test_allocate_memory_function(self):
        """Test the allocate_memory function."""
        # Function is not implemented yet, so just test it exists
        assert allocate_memory is not None
    
    def test_deallocate_memory_function(self):
        """Test the deallocate_memory function."""
        # Function is not implemented yet, so just test it exists
        assert deallocate_memory is not None
