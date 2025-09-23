# Memsim

Memory simulation tool for process scheduling and memory management.

## Installation

1. Install Poetry if you haven't already:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Install the package in editable mode:
   ```bash
   poetry install
   ```

## Usage

### Command Line Interface

Run simulations using the CLI:

```bash
# Basic simulation with event logging
python -m memsim --csv examples/processes_example.csv --tick-log events

# Detailed simulation with every tick logged
python -m memsim --csv examples/processes_example.csv --tick-log ticks

# Simulation with debug logging (shows decisions)
python -m memsim --csv examples/processes_example.csv --tick-log events --log-level DEBUG

# Simulation without intermediate output
python -m memsim --csv examples/processes_example.csv --tick-log none

# Output without headers (for scripting)
python -m memsim --csv examples/processes_example.csv --tick-log events --no-header
```

### CLI Options

- `--csv PATH`: Path to CSV file with process data (required)
- `--tick-log {none,events,ticks}`: State logging level (default: none)
  - `none`: No intermediate state output
  - `events`: Show only arrivals and terminations
  - `ticks`: Show every simulation tick
- `--log-level {INFO,DEBUG}`: Decision logging level (default: INFO)
  - `INFO`: Basic information only
  - `DEBUG`: Detailed decision logging (admission, best-fit, preemption, etc.)
- `--no-header`: Don't print column headers in output

### Example Output

```
--- Tick 0 ---
t=0 | CPU: pid=1
Memory:
  id  start  size  pid  frag  free
  --  -----  ----  ---  ----  ----
  P1    100   250    1   186   No
  P2    350   150  ---     0  Yes
  P3    500    50  ---     0  Yes
Ready:
  (empty)
Ready_susp:
  (empty)

Process Results:
pid  arrival  burst  start_time  finish_time  turnaround  wait
---  -------  -----  ----------  -----------  ----------  ----
  1        0      5           0            5           5     0
  2        2      8           2           10           8     0

Summary:
Average Turnaround Time: 6.50
Average Wait Time: 0.00
Throughput: 0.4000 processes/time unit
Total Simulation Time: 10
```

## Testing

Run the test suite:
```bash
poetry run pytest
```

## Project Structure

- `src/memsim/` - Main package source code
- `tests/` - Test files
- `examples/` - Example data files
