from __future__ import annotations

import tkinter as tk
from tkinter import END, DISABLED, NORMAL, filedialog, messagebox, ttk
from typing import Dict, List, Optional

from memsim.io import leer_procesos_csv, pretty_print_estado
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

        self._crear_widgets()
        self._configurar_atajos()
        self._actualizar_estado_acciones()
        self._establecer_estado("Seleccione un CSV para comenzar.")
    
    # ------------------------------------------------------------------
    # Configuración de la interfaz
    # ------------------------------------------------------------------
    def _crear_widgets(self) -> None:
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
            command=self.al_abrir_csv,
        )
        self.menu_archivo.add_separator()
        self.menu_archivo.add_command(label="Salir", command=self.quit)

        # Menú Simulación
        self.menu_simulacion = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label="Simulación", menu=self.menu_simulacion) # Keep "Simulación"
        self.menu_simulacion.add_command(
            label="Inicializar",
            accelerator="F5",
            command=self.al_inicializar,
        )
        self.menu_simulacion.add_command(
            label="Paso (+1 tick)",
            accelerator="F6",
            command=self.al_dar_paso,
        )
        self.menu_simulacion.add_command(
            label="Hasta evento",
            accelerator="F7",
            command=self.al_ir_a_evento,
        )
        self.menu_simulacion.add_separator()
        self.menu_simulacion.add_command(
            label="Finalizar",
            accelerator="F8",
            command=self.al_finalizar,
        )

    def _create_toolbar(self) -> None:
        toolbar = ttk.Frame(self, padding=(8, 4))
        toolbar.pack(fill=tk.X)

        self.toolbar_buttons: Dict[str, ttk.Button] = {}

        self.toolbar_buttons["open_csv"] = ttk.Button(
            toolbar, text="Abrir CSV", command=self.al_abrir_csv
        )
        self.toolbar_buttons["open_csv"].pack(side=tk.LEFT, padx=4)

        self.toolbar_buttons["initialize"] = ttk.Button(
            toolbar, text="Inicializar", command=self.al_inicializar
        )
        self.toolbar_buttons["initialize"].pack(side=tk.LEFT, padx=4)

        self.toolbar_buttons["step"] = ttk.Button(
            toolbar, text="Paso", command=self.al_dar_paso
        )
        self.toolbar_buttons["step"].pack(side=tk.LEFT, padx=4)

        self.toolbar_buttons["step_event"] = ttk.Button(
            toolbar, text="Hasta evento", command=self.al_ir_a_evento
        )
        self.toolbar_buttons["step_event"].pack(side=tk.LEFT, padx=4)

        self.toolbar_buttons["finalize"] = ttk.Button(
            toolbar, text="Finalizar", command=self.al_finalizar
        )
        self.toolbar_buttons["finalize"].pack(side=tk.LEFT, padx=4)

    def _create_main_panel(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo: snapshot
        left_frame = ttk.Frame(paned, padding=8)
        paned.add(left_frame, weight=3)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1) # Tabla de memoria
        left_frame.rowconfigure(3, weight=1) # Cola de listos
        left_frame.rowconfigure(5, weight=1) # Cola de suspendidos

        # -- Tabla de Memoria --
        ttk.Label(left_frame, text="Tabla de Memoria").grid(row=0, column=0, sticky="w", pady=(0, 4))
        mem_container = ttk.Frame(left_frame)
        mem_container.grid(row=1, column=0, sticky="nsew")
        mem_container.columnconfigure(0, weight=1)
        mem_container.rowconfigure(0, weight=1)

        self.mem_tree = ttk.Treeview(mem_container, columns=("id", "inicio", "tam", "pid", "frag", "libre"), show="headings")
        self.mem_tree.grid(row=0, column=0, sticky="nsew")
        mem_scrollbar = ttk.Scrollbar(mem_container, orient="vertical", command=self.mem_tree.yview)
        mem_scrollbar.grid(row=0, column=1, sticky="ns")
        self.mem_tree.configure(yscrollcommand=mem_scrollbar.set)

        self.mem_tree.heading("id", text="ID")
        self.mem_tree.heading("inicio", text="Inicio")
        self.mem_tree.heading("tam", text="Tamaño")
        self.mem_tree.heading("pid", text="PID")
        self.mem_tree.heading("frag", text="Frag. Int.")
        self.mem_tree.heading("libre", text="Libre")
        for col in self.mem_tree['columns']:
            self.mem_tree.column(col, width=60, anchor="center")

        # -- Cola de Listos --
        ttk.Label(left_frame, text="Cola de Listos").grid(row=2, column=0, sticky="w", pady=(10, 4))
        ready_container = ttk.Frame(left_frame)
        ready_container.grid(row=3, column=0, sticky="nsew")
        ready_container.columnconfigure(0, weight=1)
        ready_container.rowconfigure(0, weight=1)

        self.ready_tree = ttk.Treeview(ready_container, columns=("pid", "restante"), show="headings")
        self.ready_tree.grid(row=0, column=0, sticky="nsew")
        self.ready_tree.heading("pid", text="PID")
        self.ready_tree.heading("restante", text="Restante")
        self.ready_tree.column("pid", anchor="center", width=80)
        self.ready_tree.column("restante", anchor="center", width=80)

        # -- Cola de Listos/Suspendidos --
        ttk.Label(left_frame, text="Cola de Listos/Suspendidos").grid(row=4, column=0, sticky="w", pady=(10, 4))
        susp_container = ttk.Frame(left_frame)
        susp_container.grid(row=5, column=0, sticky="nsew")
        susp_container.columnconfigure(0, weight=1)
        susp_container.rowconfigure(0, weight=1)

        self.susp_tree = ttk.Treeview(susp_container, columns=("pid", "tam"), show="headings")
        self.susp_tree.grid(row=0, column=0, sticky="nsew")
        self.susp_tree.heading("pid", text="PID")
        self.susp_tree.heading("tam", text="Tamaño")
        self.susp_tree.column("pid", anchor="center", width=80)
        self.susp_tree.column("tam", anchor="center", width=80)

        # Panel derecho: estado y métricas
        right_frame = ttk.Frame(paned, padding=8)
        paned.add(right_frame, weight=2)

        estado_frame = ttk.LabelFrame(right_frame, text="Estado actual")
        estado_frame.pack(fill=tk.X)

        self.tick_var = tk.StringVar(value="Tick: -")
        ttk.Label(estado_frame, textvariable=self.tick_var).pack(anchor=tk.W, pady=2)

        self.cpu_var = tk.StringVar(value="CPU: (sin datos)")
        ttk.Label(estado_frame, textvariable=self.cpu_var).pack(anchor=tk.W, pady=2)

        self.multiprogramming_var = tk.StringVar(value="Grado multiprog.: -")
        ttk.Label(estado_frame, textvariable=self.multiprogramming_var).pack(anchor=tk.W, pady=2)

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

    def _configurar_atajos(self) -> None:
        self.bind("<Control-o>", lambda _: self.al_abrir_csv())
        self.bind("<Control-O>", lambda _: self.al_abrir_csv())
        self.bind("<F5>", lambda _: self.al_inicializar())
        self.bind("<F6>", lambda _: self.al_dar_paso())
        self.bind("<F7>", lambda _: self.al_ir_a_evento())
        self.bind("<F8>", lambda _: self.al_finalizar())

    # ------------------------------------------------------------------
    # Acciones de usuario
    # ------------------------------------------------------------------
    def al_abrir_csv(self) -> None:
        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
        )
        if not filepath:
            return

        try:
            processes = leer_procesos_csv(filepath)
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
        self._limpiar_vista_simulacion()

        self._establecer_estado(f"CSV cargado: {filepath}")
        self._actualizar_estado_acciones()

    def al_inicializar(self) -> None:
        if not self.processes:
            messagebox.showwarning(
                self,
                "Procesos no disponibles",
                "Debe cargar un archivo CSV antes de inicializar la simulación.",
            )
            return

        self.simulator.inicializar(self.processes)
        self.simulation_started = True
        self.simulation_finished = False

        snapshot = self._recolectar_snapshot()
        self._actualizar_vista_snapshot(snapshot)
        self._actualizar_panel_estado(tick=0, running_pid=None, multiprogramming=0)
        self._limpiar_metricas()

        self._establecer_estado("Simulador inicializado. Utilice Paso o Hasta evento.")
        self._actualizar_estado_acciones()

    def al_dar_paso(self) -> None:
        if not self.simulation_started:
            messagebox.showwarning(
                self,
                "Simulación no inicializada",
                "Inicialice la simulación antes de avanzar ticks.",
            )
            return

        info = self.simulator.paso()
        if info is None:
            self._establecer_estado("No hay más ticks por ejecutar. Finalizando simulación...")
            self.al_finalizar()
            return

        self._mostrar_info_tick(info)

    def al_ir_a_evento(self) -> None:
        if not self.simulation_started:
            messagebox.showwarning(
                self,
                "Simulación no inicializada",
                "Inicialice la simulación antes de avanzar ticks.",
            )
            return

        info = self.simulator.paso_hasta_evento()
        if info is None:
            self._establecer_estado("No hay más eventos. Finalizando simulación...")
            self.al_finalizar()
            return

        salto = info.get("ticks_agregados", 1)
        self._mostrar_info_tick(info)
        if salto > 1:
            self._establecer_estado(
                f"Se avanzaron {salto} ticks hasta el siguiente evento significativo."
            )

    def al_finalizar(self) -> None:
        if not self.simulation_started:
            messagebox.showwarning(
                self,
                "Simulación no inicializada",
                "Inicialice la simulación antes de finalizar.",
            )
            return

        summary = self.simulator.finalizar()
        self.simulation_finished = True

        # Actualizar el panel de estado con el tiempo final correcto
        self._actualizar_panel_estado(
            tick=summary.get("tiempo_total", self.simulator.current_time),
            running_pid=None,
            multiprogramming=0
        )

        self._poblar_metricas(summary)
        self._establecer_estado("Simulación finalizada. Métricas disponibles.")
        self._actualizar_estado_acciones()

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    def _mostrar_info_tick(self, info: Dict[str, object]) -> None:
        snapshot = info.get("snapshot_data", {})
        tick = int(info.get("time", 0))
        running_pid = info.get("running_pid") # type: ignore
        multiprogramming = int(info.get("degree_of_multiprogramming", 0))

        self._actualizar_vista_snapshot(snapshot)
        self._actualizar_panel_estado(tick=tick, running_pid=running_pid, multiprogramming=multiprogramming)
        self._establecer_estado(f"Tick {tick} ejecutado.")

    def _actualizar_vista_snapshot(self, snapshot_data: Dict) -> None:
        # Limpiar vistas
        for tree in [self.mem_tree, self.ready_tree, self.susp_tree]:
            for item in tree.get_children():
                tree.delete(item)

        # Poblar tabla de memoria
        mem_table = snapshot_data.get("mem_table", [])
        # Fila del SO
        self.mem_tree.insert("", END, values=("SO", "0", "100", "---", "---", "No"))
        for entry in mem_table:
            pid_str = str(entry['pid']) if entry['pid'] is not None else "---"
            free_str = "Sí" if entry.get('free', True) else "No"
            self.mem_tree.insert("", END, values=(
                entry['id'], entry['start'], entry['size'], pid_str,
                entry['frag_interna'], free_str
            ))

        # Poblar cola de listos
        ready_list = snapshot_data.get("ready", [])
        for proc in ready_list:
            self.ready_tree.insert("", END, values=(proc.pid, proc.remaining))

        # Poblar cola de suspendidos
        susp_list = snapshot_data.get("ready_susp", [])
        for proc in susp_list:
            self.susp_tree.insert("", END, values=(proc.pid, proc.size))

    def _set_snapshot(self, text: str) -> None:
        pass # Obsoleto, se mantiene para evitar errores si es llamado.

    def _actualizar_panel_estado(self, tick: int, running_pid: Optional[int], multiprogramming: int) -> None:
        self.tick_var.set(f"Tick: {tick}")
        if running_pid is None:
            self.cpu_var.set("CPU: inactiva")
        else:
            self.cpu_var.set(f"CPU: PID {running_pid}")

        self.multiprogramming_var.set(f"Grado multiprog.: {multiprogramming}")

    def _poblar_metricas(self, summary: Dict[str, object]) -> None:
        self._limpiar_metricas()

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

    def _limpiar_metricas(self) -> None:
        for child in self.metrics_tree.get_children():
            self.metrics_tree.delete(child)
        self.avg_turnaround_var.set("Promedio retorno: -")
        self.avg_wait_var.set("Promedio espera: -")
        self.throughput_var.set("Productividad: -")
        self.total_time_var.set("Tiempo total: -")

    def _limpiar_vista_simulacion(self) -> None:
        self._actualizar_vista_snapshot({})
        self._actualizar_panel_estado(tick=0, running_pid=None, multiprogramming=0)
        self._limpiar_metricas()

    def _establecer_estado(self, message: str) -> None:
        self.status_var.set(message)

    def _actualizar_estado_acciones(self) -> None:
        csv_cargado = bool(self.processes)
        puede_avanzar = self.simulation_started and not self.simulation_finished

        self._establecer_estado_accion("initialize", csv_cargado)
        self._establecer_estado_accion("step", puede_avanzar)
        self._establecer_estado_accion("step_event", puede_avanzar)
        self._establecer_estado_accion(
            "finalize", self.simulation_started and not self.simulation_finished
        )

    def _establecer_estado_accion(self, action: str, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED

        if action == "initialize":
            self.menu_simulacion.entryconfig("Inicializar", state=state) # Keep "Inicializar"
        elif action == "step":
            self.menu_simulacion.entryconfig("Paso (+1 tick)", state=state)
        elif action == "step_event":
            self.menu_simulacion.entryconfig("Hasta evento", state=state)
        elif action == "finalize":
            self.menu_simulacion.entryconfig("Finalizar", state=state)

        button = self.toolbar_buttons.get(action)
        if button is not None:
            button.configure(state=state)

    def _recolectar_snapshot(self) -> str:
        try:
            return self.simulator._recolectar_snapshot_estado(structured=True)  # type: ignore[attr-defined]
        except AttributeError:
            return {}  # Respaldo si cambia la API interna

    # ------------------------------------------------------------------
    # Entrada principal
    # ------------------------------------------------------------------
    def mainloop(self, n: int = 0) -> None:  # type: ignore[override]
        try:
            super().mainloop(n)
        finally:
            self.destroy()


def ejecutar_gui() -> None:
    app = MemSimGUI()
    app.mainloop()


if __name__ == "__main__":
    ejecutar_gui()
