# Example CSV Scenarios

The `processes_example.csv` file is designed to test all key aspects of the memory simulation:

## Process Data

| PID | Size | Arrival | Burst | Scenario |
|-----|------|---------|-------|----------|
| 1   | 45   | 0       | 3     | Simultaneous arrival, fits in P3 |
| 2   | 100  | 0       | 1     | Simultaneous arrival, fits in P2, shortest burst |
| 3   | 220  | 1       | 2     | Only fits in P1 |
| 4   | 300  | 2       | 4     | Doesn't fit anywhere (stays in ready_susp) |
| 5   | 90   | 3       | 5     | Fits in P2, longest burst |
| 6   | 35   | 4       | 1     | Fits in P3, shortest burst |
| 7   | 110  | 5       | 2     | Fits in P2 |
| 8   | 50   | 6       | 3     | Fits in P3 |

## Tested Scenarios

### 1. Simultaneous Arrivals
- **Processes 1 & 2** arrive at t=0
- Tests multiprogramming degree limit and Best-Fit allocation
- Process 1 (size=45) → P3 (size=50)
- Process 2 (size=100) → P2 (size=150)

### 2. Memory Partition Allocation
- **P3 (size=50)**: Processes 1, 6, 8 (sizes 45, 35, 50)
- **P2 (size=150)**: Processes 2, 5, 7 (sizes 100, 90, 110)
- **P1 (size=250)**: Process 3 (size=220)
- **Too large**: Process 4 (size=300) stays in ready_susp

### 3. SRTF Preemption
- **Shortest bursts**: Processes 2, 6 (burst=1) will preempt others
- **Medium bursts**: Processes 3, 7 (burst=2)
- **Longer bursts**: Processes 1, 8 (burst=3), Process 4 (burst=4), Process 5 (burst=5)

### 4. Ready_Susp Behavior
- **Process 4** (size=300) cannot fit in any partition
- Will remain in ready_susp throughout simulation
- Tests the simulator's handling of processes that never get memory

## Expected Behavior

1. **t=0**: Processes 1,2 arrive → P3,P2 allocated → Process 2 runs (shortest burst)
2. **t=1**: Process 2 completes → Process 1 runs
3. **t=2**: Process 3 arrives → P1 allocated → Process 3 preempts Process 1
4. **t=3**: Process 4 arrives → no memory available → goes to ready_susp
5. **t=4**: Process 3 completes → Process 1 resumes
6. **t=5**: Process 5 arrives → P2 allocated → Process 5 runs
7. **t=6**: Process 6 arrives → P3 allocated → Process 6 preempts Process 5
8. **t=7**: Process 6 completes → Process 5 resumes
9. **t=8**: Process 7 arrives → P2 allocated → Process 7 runs
10. **t=9**: Process 8 arrives → P3 allocated → Process 8 runs
11. **t=10**: Process 7 completes → Process 1 resumes
12. **t=11**: Process 1 completes → Process 5 resumes
13. **t=12**: Process 5 completes → Process 8 runs
14. **t=13**: Process 8 completes
15. **Process 4** remains in ready_susp (never gets memory)

## CLI Testing

Run with different logging levels to observe the behavior:

```bash
# See only arrivals and terminations
python -m memsim --csv examples/processes_example.csv --tick-log events

# See every simulation tick
python -m memsim --csv examples/processes_example.csv --tick-log ticks

# See only final results
python -m memsim --csv examples/processes_example.csv --tick-log none
```

## Key Observations

- **Multiprogramming degree** never exceeds 5
- **Best-Fit allocation** minimizes internal fragmentation
- **SRTF preemption** ensures shortest jobs run first
- **Ready_susp** properly handles processes that cannot fit
- **Memory release** allows new processes to get partitions
