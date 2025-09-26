from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from memsim.io import read_processes_csv
from memsim.models import Process
from memsim.simulator import MemorySimulator


class MemSimGUI(tk.Tk):
    """Interfaz gráfica principal del simulador de memoria."""

    def __init__(self) -> None:
        super().__init__()
        self.title("MemSim - Simulador de Memoria")
        self.geometry("1100x700")

        self.simulator = MemorySimulator()
        self.processes: List[Process] = []
        self.csv_path: Optional[str] = None
        self.simulation_started = False
        self.simulation_finished = False

        self._create_widgets()
        self._configure_shortcuts()
        self._update_actions_state()
        self._set_status("Seleccione un CSV para comenzar.")

    # ------------------------------------------------------------------
    # Configuración de la interfaz
    # ------------------------------------------------------------------
    def _create_widgets(self) -> None:
        self._create_menu()
        self._create_toolbar()
        self._create_main_panel()
        self._create_status_bar()

    def _create_menu(self) -> None:
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)

        # Menú Archivo
        self.menu_archivo = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label="Archivo", menu=self.menu_archivo)
        self.menu_archivo.add_command(
            label="Abrir CSV…",
            accelerator="Ctrl+O",
            command=self.on_open_csv,
        )
        self.menu_archivo.add_separator()
        self.menu_archivo.add_command(label="Salir", command=self.quit)

        # Menú Simulación
        self.menu_simulacion = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label="Simulación", menu=self.menu_simulacion)
        self.menu_simulacion.add_command(
            label="Inicializar",
            accelerator="F5",
            command=self.on_initialize,
        )
        self.menu_simulacion.add_command(
            label="Paso (+1 tick)",
            accelerator="F6",
            command=self.on_step,
        )
        self.menu_simulacion.add_command(
            label="Hasta evento",
            accelerator="F7",
            command=self.on_step_to_event,
        )
        self.menu_simulacion.add_separator()
        self.menu_simulacion.add_command(
            label="Finalizar",
            accelerator="F8",
            command=self.on_finalize,
        )

    def _create_toolbar(self) -> None:
        toolbar = ttk.Frame(self, padding=(8, 4))
        toolbar.pack(fill=tk.X)

        self.toolbar_buttons: Dict[str, ttk.Button] = {}

        self.toolbar_buttons["open_csv"] = ttk.Button(
            toolbar, text="Abrir CSV", command=self.on_open_csv
        )
        self.toolbar_buttons["open_csv"].pack(side=tk.LEFT, padx=4)

        self.toolbar_buttons["initialize"] = ttk.Button(
            toolbar, text="Inicializar", command=self.on_initialize
        )
        self.toolbar_buttons["initialize"].pack(side=tk.LEFT, padx=4)

        self.toolbar_buttons["step"] = ttk.Button(
            toolbar, text="Paso", command=self.on_step
        )
        self.toolbar_buttons["step"].pack(side=tk.LEFT, padx=4)

        self.toolbar_buttons["step_event"] = ttk.Button(
            toolbar, text="Hasta evento", command=self.on_step_to_event
        )
        self.toolbar_buttons["step_event"].pack(side=tk.LEFT, padx=4)

        self.toolbar_buttons["finalize"] = ttk.Button(
            toolbar, text="Finalizar", command=self.on_finalize
        )
        self.toolbar_buttons["finalize"].pack(side=tk.LEFT, padx=4)

    def _create_main_panel(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo: snapshot
        left_frame = ttk.Frame(paned, padding=8)
        paned.add(left_frame, weight=3)

        ttk.Label(left_frame, text="Instantánea del estado").pack(anchor=tk.W)

        snapshot_container = ttk.Frame(left_frame)
        snapshot_container.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.snapshot_text = tk.Text(
            snapshot_container,
            wrap=tk.NONE,
            font=("Consolas", 10),
            state=tk.DISABLED,
        )
        self.snapshot_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            snapshot_container, orient=tk.VERTICAL, command=self.snapshot_text.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.snapshot_text.configure(yscrollcommand=scrollbar.set)

        # Panel derecho: estado y métricas
        right_frame = ttk.Frame(paned, padding=8)
        paned.add(right_frame, weight=2)

        estado_frame = ttk.LabelFrame(right_frame, text="Estado actual")
        estado_frame.pack(fill=tk.X)

        self.tick_var = tk.StringVar(value="Tick: -")
        ttk.Label(estado_frame, textvariable=self.tick_var).pack(anchor=tk.W, pady=2)

        self.cpu_var = tk.StringVar(value="CPU: (sin datos)")
        ttk.Label(estado_frame, textvariable=self.cpu_var).pack(anchor=tk.W, pady=2)

        resumen_frame = ttk.LabelFrame(right_frame, text="Métricas finales")
        resumen_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.metrics_tree = ttk.Treeview(
            resumen_frame,
            columns=(
                "pid",
                "llegada",
                "duracion",
                "inicio",
                "fin",
                "retorno",
                "espera",
                "tamano",
            ),
            show="headings",
            height=8,
        )
        headings = {
            "pid": "PID",
            "llegada": "Llegada",
            "duracion": "Duración",
            "inicio": "Inicio",
            "fin": "Fin",
            "retorno": "Retorno",
            "espera": "Espera",
            "tamano": "Tamaño",
        }
        for key, text in headings.items():
            self.metrics_tree.heading(key, text=text)
            self.metrics_tree.column(key, width=90, anchor=tk.CENTER)

        self.metrics_tree.pack(fill=tk.BOTH, expand=True)

        promedios_frame = ttk.Frame(resumen_frame)
        promedios_frame.pack(fill=tk.X, pady=(8, 0))

        self.avg_turnaround_var = tk.StringVar(value="Promedio retorno: -")
        ttk.Label(promedios_frame, textvariable=self.avg_turnaround_var).pack(
            anchor=tk.W
        )

        self.avg_wait_var = tk.StringVar(value="Promedio espera: -")
        ttk.Label(promedios_frame, textvariable=self.avg_wait_var).pack(anchor=tk.W)

        self.throughput_var = tk.StringVar(value="Productividad: -")
        ttk.Label(promedios_frame, textvariable=self.throughput_var).pack(anchor=tk.W)

        self.total_time_var = tk.StringVar(value="Tiempo total: -")
        ttk.Label(promedios_frame, textvariable=self.total_time_var).pack(anchor=tk.W)

    def _create_status_bar(self) -> None:
        status_frame = ttk.Frame(self, relief=tk.SUNKEN, padding=(6, 4))
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor=tk.W)

    def _configure_shortcuts(self) -> None:
        self.bind("<Control-o>", lambda _: self.on_open_csv())
        self.bind("<Control-O>", lambda _: self.on_open_csv())
        self.bind("<F5>", lambda _: self.on_initialize())
        self.bind("<F6>", lambda _: self.on_step())
        self.bind("<F7>", lambda _: self.on_step_to_event())
        self.bind("<F8>", lambda _: self.on_finalize())

    # ------------------------------------------------------------------
    # Acciones de usuario
    # ------------------------------------------------------------------
    def on_open_csv(self) -> None:
        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
        )
        if not filepath:
            return

        try:
            processes = read_processes_csv(filepath)
        except (FileNotFoundError, ValueError) as exc:
            messagebox.showwarning(
                self,
                "Error al abrir CSV",
                f"No se pudo cargar el archivo seleccionado.\nMotivo: {exc}",
            )
            return

        self.processes = processes
        self.csv_path = filepath
        self.simulation_started = False
        self.simulation_finished = False
        self._clear_simulation_view()

        self._set_status(f"CSV cargado: {filepath}")
        self._update_actions_state()

    def on_initialize(self) -> None:
        if not self.processes:
            messagebox.showwarning(
                self,
                "Procesos no disponibles",
                "Debe cargar un archivo CSV antes de inicializar la simulación.",
            )
            return

        self.simulator.initialize(self.processes)
        self.simulation_started = True
        self.simulation_finished = False

        snapshot = self._collect_snapshot()
        self._set_snapshot(snapshot)
        self._update_state_panel(tick=0, running_pid=None)
        self._clear_metrics()

        self._set_status("Simulador inicializado. Utilice Paso o Hasta evento.")
        self._update_actions_state()

    def on_step(self) -> None:
        if not self.simulation_started:
            messagebox.showwarning(
                self,
                "Simulación no inicializada",
                "Inicialice la simulación antes de avanzar ticks.",
            )
            return

        info = self.simulator.step()
        if info is None:
            messagebox.showwarning(
                self,
                "Simulación finalizada",
                "No hay más ticks por ejecutar. Finalice para ver métricas.",
            )
            self.simulation_finished = True
            self._update_actions_state()
            return

        self._show_tick_info(info)

    def on_step_to_event(self) -> None:
        if not self.simulation_started:
            messagebox.showwarning(
                self,
                "Simulación no inicializada",
                "Inicialice la simulación antes de avanzar ticks.",
            )
            return

        info = self.simulator.step_hasta_evento()
        if info is None:
            messagebox.showwarning(
                self,
                "Simulación finalizada",
                "No hay eventos restantes. Finalice para ver métricas.",
            )
            self.simulation_finished = True
            self._update_actions_state()
            return

        salto = info.get("ticks_agregados", 1)
        self._show_tick_info(info)
        if salto > 1:
            self._set_status(
                f"Se avanzaron {salto} ticks hasta el siguiente evento significativo."
            )

    def on_finalize(self) -> None:
        if not self.simulation_started:
            messagebox.showwarning(
                self,
                "Simulación no inicializada",
                "Inicialice la simulación antes de finalizar.",
            )
            return

        summary = self.simulator.finalize()
        self.simulation_finished = True

        # Mostrar último snapshot disponible
        log = summary.get("simulation_log", [])
        if log:
            ultimo_tick = len(log) - 1
            self._set_snapshot(log[-1])
            running_pid = self.simulator.scheduler.running.pid if self.simulator.scheduler.running else None
            self._update_state_panel(tick=ultimo_tick, running_pid=running_pid)
        else:
            self._update_state_panel(
                tick=self.simulator.current_time,
                running_pid=None,
            )

        self._populate_metrics(summary)
        self._set_status("Simulación finalizada. Métricas disponibles.")
        self._update_actions_state()

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    def _show_tick_info(self, info: Dict[str, object]) -> None:
        snapshot = info.get("snapshot", "")
        tick = int(info.get("time", 0))
        running_pid = info.get("running_pid")

        self._set_snapshot(snapshot)
        self._update_state_panel(tick=tick, running_pid=running_pid)
        self._set_status(f"Tick {tick} ejecutado.")

    def _set_snapshot(self, text: str) -> None:
        self.snapshot_text.configure(state=tk.NORMAL)
        self.snapshot_text.delete("1.0", tk.END)
        self.snapshot_text.insert(tk.END, text)
        self.snapshot_text.configure(state=tk.DISABLED)

    def _update_state_panel(self, tick: int, running_pid: Optional[int]) -> None:
        self.tick_var.set(f"Tick: {tick}")
        if running_pid is None:
            self.cpu_var.set("CPU: inactiva")
        else:
            self.cpu_var.set(f"CPU: PID {running_pid}")

    def _populate_metrics(self, summary: Dict[str, object]) -> None:
        self._clear_metrics()

        processes = summary.get("processes", [])
        for proc in processes:
            self.metrics_tree.insert(
                "",
                tk.END,
                values=(
                    proc.get("pid"),
                    proc.get("arrival"),
                    proc.get("burst"),
                    proc.get("start_time"),
                    proc.get("finish_time"),
                    proc.get("turnaround"),
                    proc.get("wait"),
                    proc.get("size"),
                ),
            )

        self.avg_turnaround_var.set(
            f"Promedio retorno: {summary.get('avg_turnaround', 0.0):.2f}"
        )
        self.avg_wait_var.set(f"Promedio espera: {summary.get('avg_wait', 0.0):.2f}")
        self.throughput_var.set(
            f"Productividad: {summary.get('throughput', 0.0):.2f} procesos/tick"
        )
        self.total_time_var.set(f"Tiempo total: {summary.get('tiempo_total', 0)} ticks")

    def _clear_metrics(self) -> None:
        for child in self.metrics_tree.get_children():
            self.metrics_tree.delete(child)
        self.avg_turnaround_var.set("Promedio retorno: -")
        self.avg_wait_var.set("Promedio espera: -")
        self.throughput_var.set("Productividad: -")
        self.total_time_var.set("Tiempo total: -")

    def _clear_simulation_view(self) -> None:
        self._set_snapshot("")
        self._update_state_panel(tick=0, running_pid=None)
        self._clear_metrics()

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _update_actions_state(self) -> None:
        csv_cargado = bool(self.processes)
        puede_avanzar = self.simulation_started and not self.simulation_finished

        self._set_action_state("initialize", csv_cargado)
        self._set_action_state("step", puede_avanzar)
        self._set_action_state("step_event", puede_avanzar)
        self._set_action_state(
            "finalize", self.simulation_started and not self.simulation_finished
        )

    def _set_action_state(self, action: str, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED

        if action == "initialize":
            self.menu_simulacion.entryconfig("Inicializar", state=state)
        elif action == "step":
            self.menu_simulacion.entryconfig("Paso (+1 tick)", state=state)
        elif action == "step_event":
            self.menu_simulacion.entryconfig("Hasta evento", state=state)
        elif action == "finalize":
            self.menu_simulacion.entryconfig("Finalizar", state=state)

        button = self.toolbar_buttons.get(action)
        if button is not None:
            button.configure(state=state)

    def _collect_snapshot(self) -> str:
        try:
            return self.simulator._collect_state_snapshot()  # type: ignore[attr-defined]
        except AttributeError:
            return "No hay datos para mostrar."  # Respaldo si cambia la API interna

    # ------------------------------------------------------------------
    # Entrada principal
    # ------------------------------------------------------------------
    def mainloop(self, n: int = 0) -> None:  # type: ignore[override]
        try:
            super().mainloop(n)
        finally:
            self.destroy()


def main() -> None:
    app = MemSimGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
