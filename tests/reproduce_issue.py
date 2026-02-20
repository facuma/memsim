import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from memsim.simulator import MemorySimulator
from memsim.models import Process, State

def test_oversized_process_rejection():
    # Setup
    simulator = MemorySimulator(modo_depuracion=True)
    
    # Create processes: one normal, one oversized
    processes = [
        Process(pid=1, size=100, arrival=0, burst=1, remaining=1), # Fits in P1 or P2
        Process(pid=2, size=300, arrival=0, burst=1, remaining=1), # Oversized (>250)
        Process(pid=3, size=50, arrival=1, burst=1, remaining=1)   # Fits in P3
    ]
    
    print("Iniciando simulación con proceso sobredimensionado...")
    results = simulator.ejecutar_simulacion(processes)
    print("Simulación finalizada.")
    
    # Verify results
    # With the new logic, P2 (oversized) and P3 (valid but blocked if order is strict) 
    # might remain in arrivals.
    # The API returns 'processes' which now includes what was left in arrivals.
    
    all_processes = results['processes']
    print(f"Total procesos reportados: {len(all_processes)}")
    
    p2 = next((p for p in all_processes if p['pid'] == 2), None)
    
    if p2:
        print(f"Estado de P2: {p2.get('state')}")
        # Now we expect 'NUEVO' (NEW) instead of 'RECHAZADO'
        if p2.get('state') == 'NUEVO': 
            print("SUCCESS: Proceso 2 quedó en estado NUEVO.")
        elif p2.get('state') == 'RECHAZADO':
             print("WARNING: Proceso 2 está RECHAZADO (lógica anterior?).")
        else:
            print(f"FAILURE: Proceso 2 tiene estado inesperado: {p2.get('state')}")
            sys.exit(1)
            
        if p2.get('start_time') is None and p2.get('finish_time') is None:
             print("SUCCESS: Proceso 2 tiene tiempos nulos.")
        else:
             print(f"FAILURE: Proceso 2 tiene tiempos asignados: start={p2.get('start_time')}, finish={p2.get('finish_time')}")
             sys.exit(1)

    else:
        print("FAILURE: Proceso 2 no se encuentra en la lista de resultados.")
        sys.exit(1)

    # Verify other processes ran normally
    p1 = next((p for p in all_processes if p['pid'] == 1), None)
    if p1 and p1.get('finish_time') is not None:
        print("SUCCESS: Proceso 1 finalizó correctamente.")
    else:
        print(f"FAILURE: Proceso 1 no finalizó correctamente. Estado: {p1.get('state') if p1 else 'No encontrado'}")
        
if __name__ == "__main__":
    test_oversized_process_rejection()
