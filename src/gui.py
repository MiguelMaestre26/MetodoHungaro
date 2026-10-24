"""Interfaz grafica (Tkinter) del sistema de asignacion optima."""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from .ai_agent import AIAgentError, GeminiAgent
from .data_loader import DataLoader, LoadedData
from .graph_view import BipartiteGraphView
from .hungarian import HungarianSolver
from .models import AssignmentResult


class ScrollableFrame(ttk.Frame):
    """Contenedor con barras de desplazamiento para matrices grandes."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.inner = ttk.Frame(self.canvas)

        scroll_v = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        scroll_h = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

        self.canvas.configure(
            yscrollcommand=scroll_v.set, xscrollcommand=scroll_h.set
        )
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll_v.grid(row=0, column=1, sticky="ns")
        scroll_h.grid(row=1, column=0, sticky="ew")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_inner_configure(self, _event) -> None:
        """Actualiza la region desplazable cuando cambia el contenido."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_wheel(self, _event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_wheel(self, _event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event) -> None:
        """Desplazamiento vertical con la rueda del raton."""
        self.canvas.yview_scroll(int(-event.delta / 120), "units")


class App(tk.Tk):
    """Ventana principal de la aplicacion."""

    MAX_DIMENSION = 20

    def __init__(self) -> None:
        super().__init__()
        self.title("Optimizacion de Asignacion - Metodo Hungaro")
        self.geometry("1120x780")
        self.minsize(960, 640)

        # Variables de estado de la interfaz.
        self.objective_var = tk.StringVar(value="min")
        self.rows_var = tk.IntVar(value=4)
        self.cols_var = tk.IntVar(value=4)
        self.matrix_vars: List[List[tk.StringVar]] = []
        self.current_result: Optional[AssignmentResult] = None
        self.ai_agent = GeminiAgent()

        self._configure_style()
        self._build_ui()
        self.set_matrix(DataLoader.default_data().matrix)
        self._update_ai_status()

    # ------------------------------------------------------------------
    # Construccion de la interfaz
    # ------------------------------------------------------------------
    def _configure_style(self) -> None:
        """Aplica un estilo visual sencillo y legible."""
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 12, "bold"))
        estilo.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        contenedor = ttk.Frame(self, padding=10)
        contenedor.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(contenedor)
        self.notebook.pack(fill="both", expand=True)

        self.tab_datos = ttk.Frame(self.notebook, padding=10)
        self.tab_grafo = ttk.Frame(self.notebook, padding=10)
        self.tab_ia = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.tab_datos, text="1. Datos y resultados")
        self.notebook.add(self.tab_grafo, text="2. Grafo bipartito")
        self.notebook.add(self.tab_ia, text="3. Analisis con IA")

        self._build_tab_datos()
        self.graph_view = BipartiteGraphView(self.tab_grafo)
        self._build_tab_ia()

        self.status_var = tk.StringVar(value="Listo.")
        barra = ttk.Label(contenedor, textvariable=self.status_var, anchor="w")
        barra.pack(fill="x", pady=(6, 0))

    def _build_tab_datos(self) -> None:
        """Pestana con controles, grilla de matriz y resultados."""
        controles = ttk.Frame(self.tab_datos)
        controles.pack(fill="x")

        # Objetivo del problema (minimizar / maximizar).
        marco_objetivo = ttk.LabelFrame(controles, text="Objetivo", padding=8)
        marco_objetivo.pack(side="left", padx=(0, 10))
        ttk.Radiobutton(
            marco_objetivo,
            text="Minimizar",
            variable=self.objective_var,
            value="min",
        ).pack(side="left")
        ttk.Radiobutton(
            marco_objetivo,
            text="Maximizar",
            variable=self.objective_var,
            value="max",
        ).pack(side="left")

        # Carga de datos externa y matriz por defecto.
        marco_carga = ttk.LabelFrame(controles, text="Carga de datos", padding=8)
        marco_carga.pack(side="left", padx=(0, 10))
        ttk.Button(
            marco_carga, text="Cargar CSV", command=self.load_csv
        ).pack(side="left", padx=2)
        ttk.Button(
            marco_carga, text="Cargar JSON", command=self.load_json
        ).pack(side="left", padx=2)
        ttk.Button(
            marco_carga, text="Matriz por defecto", command=self.load_default
        ).pack(side="left", padx=2)

        # Dimensiones de la matriz editable.
        marco_dim = ttk.LabelFrame(controles, text="Dimensiones", padding=8)
        marco_dim.pack(side="left", padx=(0, 10))
        ttk.Label(marco_dim, text="Agentes:").pack(side="left")
        ttk.Spinbox(
            marco_dim,
            from_=1,
            to=self.MAX_DIMENSION,
            textvariable=self.rows_var,
            width=4,
        ).pack(side="left", padx=(2, 8))
        ttk.Label(marco_dim, text="Tareas:").pack(side="left")
        ttk.Spinbox(
            marco_dim,
            from_=1,
            to=self.MAX_DIMENSION,
            textvariable=self.cols_var,
            width=4,
        ).pack(side="left", padx=(2, 8))
        ttk.Button(
            marco_dim, text="Generar grilla", command=self.generate_grid
        ).pack(side="left")

        ttk.Button(
            controles,
            text="Resolver asignacion",
            command=self.resolve,
            style="Accent.TButton",
        ).pack(side="right")

        # Cuerpo: grilla de la matriz (arriba) y resultados (abajo).
        cuerpo = ttk.Frame(self.tab_datos)
        cuerpo.pack(fill="both", expand=True, pady=(10, 0))
        cuerpo.rowconfigure(0, weight=3)
        cuerpo.rowconfigure(1, weight=2)
        cuerpo.columnconfigure(0, weight=1)

        self.matrix_container = ScrollableFrame(cuerpo)
        self.matrix_container.grid(row=0, column=0, sticky="nsew")

        marco_resultados = ttk.LabelFrame(cuerpo, text="Resultado", padding=8)
        marco_resultados.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        marco_resultados.rowconfigure(0, weight=1)
        marco_resultados.columnconfigure(0, weight=1)

        self.results_text = tk.Text(
            marco_resultados, height=10, wrap="word", state="disabled", padx=8, pady=8
        )
        self.results_text.grid(row=0, column=0, sticky="nsew")
        scroll_resultados = ttk.Scrollbar(
            marco_resultados, orient="vertical", command=self.results_text.yview
        )
        scroll_resultados.grid(row=0, column=1, sticky="ns")
        self.results_text.configure(yscrollcommand=scroll_resultados.set)

    def _build_tab_ia(self) -> None:
        """Pestana para mostrar el analisis ejecutivo generado por Gemini."""
        superior = ttk.Frame(self.tab_ia)
        superior.pack(fill="x")

        self.ai_button = ttk.Button(
            superior,
            text="Generar analisis con IA",
            command=self.generate_ai,
            style="Accent.TButton",
        )
        self.ai_button.pack(side="left")

        self.ai_status = ttk.Label(superior, text="", foreground="#555555")
        self.ai_status.pack(side="left", padx=12)

        marco_texto = ttk.Frame(self.tab_ia)
        marco_texto.pack(fill="both", expand=True, pady=(10, 0))
        marco_texto.rowconfigure(0, weight=1)
        marco_texto.columnconfigure(0, weight=1)

        self.ai_text = tk.Text(
            marco_texto, wrap="word", state="disabled", padx=12, pady=12
        )
        self.ai_text.grid(row=0, column=0, sticky="nsew")
        scroll_ia = ttk.Scrollbar(
            marco_texto, orient="vertical", command=self.ai_text.yview
        )
        scroll_ia.grid(row=0, column=1, sticky="ns")
        self.ai_text.configure(yscrollcommand=scroll_ia.set)

    # ------------------------------------------------------------------
    # Grilla de la matriz
    # ------------------------------------------------------------------
    def generate_grid(self) -> None:
        """Reconstruye la grilla con las dimensiones indicadas por el usuario."""
        try:
            filas = int(self.rows_var.get())
            columnas = int(self.cols_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror(
                "Dimensiones invalidas",
                "Las dimensiones deben ser numeros enteros.",
            )
            return

        if not (1 <= filas <= self.MAX_DIMENSION) or not (
            1 <= columnas <= self.MAX_DIMENSION
        ):
            messagebox.showerror(
                "Dimensiones invalidas",
                f"Use valores entre 1 y {self.MAX_DIMENSION} para filas y columnas.",
            )
            return

        # Conserva los valores existentes en la medida de lo posible.
        actuales = [[var.get() for var in fila] for fila in self.matrix_vars]
        self._create_grid(filas, columnas)
        for i in range(min(filas, len(actuales))):
            for j in range(min(columnas, len(actuales[i]))):
                self.matrix_vars[i][j].set(actuales[i][j])

    def _create_grid(self, filas: int, columnas: int) -> None:
        """Crea las celdas editables (tk.Entry) para la matriz."""
        for hijo in self.matrix_container.inner.winfo_children():
            hijo.destroy()

        self.matrix_vars = []

        # Encabezados de tareas (columnas).
        ttk.Label(
            self.matrix_container.inner, text="", width=10
        ).grid(row=0, column=0, padx=3, pady=3)
        for j in range(columnas):
            ttk.Label(
                self.matrix_container.inner,
                text=f"T{j + 1}",
                font=("Segoe UI", 9, "bold"),
                anchor="center",
            ).grid(row=0, column=j + 1, padx=3, pady=3, sticky="ew")

        for i in range(filas):
            # Encabezado de agente (fila).
            ttk.Label(
                self.matrix_container.inner,
                text=f"A{i + 1}",
                font=("Segoe UI", 9, "bold"),
                anchor="center",
            ).grid(row=i + 1, column=0, padx=3, pady=3, sticky="ew")

            fila_vars: List[tk.StringVar] = []
            for j in range(columnas):
                var = tk.StringVar()
                entrada = ttk.Entry(
                    self.matrix_container.inner,
                    textvariable=var,
                    width=10,
                    justify="center",
                )
                entrada.grid(row=i + 1, column=j + 1, padx=3, pady=3)
                fila_vars.append(var)
            self.matrix_vars.append(fila_vars)

    def set_matrix(self, matrix: List[List[float]]) -> None:
        """Carga una matriz en la grilla editable."""
        filas = len(matrix)
        columnas = len(matrix[0]) if filas else 0
        self.rows_var.set(filas)
        self.cols_var.set(columnas)
        self._create_grid(filas, columnas)

        for i, fila in enumerate(matrix):
            for j, valor in enumerate(fila):
                self.matrix_vars[i][j].set(self._format_number(valor))

    def get_matrix(self) -> List[List[float]]:
        """Lee y valida la matriz escrita en la grilla."""
        if not self.matrix_vars:
            raise ValueError("La matriz esta vacia. Genere una grilla primero.")

        matriz: List[List[float]] = []
        for i, fila in enumerate(self.matrix_vars):
            fila_numerica: List[float] = []
            for j, var in enumerate(fila):
                texto = var.get().strip().replace(",", ".")
                if not texto:
                    raise ValueError(
                        f"La celda (A{i + 1}, T{j + 1}) esta vacia."
                    )
                try:
                    fila_numerica.append(float(texto))
                except ValueError as error:
                    raise ValueError(
                        f"La celda (A{i + 1}, T{j + 1}) no es numerica: '{texto}'."
                    ) from error
            matriz.append(fila_numerica)

        DataLoader.validate_matrix(matriz)
        return matriz

    # ------------------------------------------------------------------
    # Acciones de carga de datos
    # ------------------------------------------------------------------
    def load_csv(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Seleccione un archivo CSV",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        try:
            datos = DataLoader.load_csv(ruta)
        except (OSError, ValueError) as error:
            self._handle_load_error("Error al cargar CSV", error)
            return
        self._apply_loaded_data(datos)

    def load_json(self) -> None:
        ruta = filedialog.askopenfilename(
            title="Seleccione un archivo JSON",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        try:
            datos = DataLoader.load_json(ruta)
        except (OSError, ValueError) as error:
            self._handle_load_error("Error al cargar JSON", error)
            return
        self._apply_loaded_data(datos)

    def _handle_load_error(self, titulo: str, error: Exception) -> None:
        """Informa el error y ofrece la matriz por defecto como contingencia."""
        messagebox.showerror(titulo, f"{error}\n\nSe mantiene la matriz actual.")
        if messagebox.askyesno(
            "Matriz por defecto",
            "¿Desea cargar la matriz por defecto como contingencia?",
        ):
            self.load_default()

    def load_default(self) -> None:
        self._apply_loaded_data(DataLoader.default_data())

    def _apply_loaded_data(self, datos: LoadedData) -> None:
        """Vuelca los datos cargados en la interfaz y reinicia el estado."""
        self.set_matrix(datos.matrix)
        if datos.objective:
            self.objective_var.set(datos.objective)

        self.current_result = None
        self.graph_view.clear()
        self._clear_ai_text()

        filas = len(datos.matrix)
        columnas = len(datos.matrix[0]) if filas else 0
        self._set_results(
            f"Fuente: {datos.source}\n"
            f"Dimensiones: {filas} agentes x {columnas} tareas\n"
            f"Objetivo: {'Maximizacion' if self.objective_var.get() == 'max' else 'Minimizacion'}\n\n"
            "Presione 'Resolver asignacion' para calcular el optimo."
        )
        self.status_var.set(f"Datos cargados desde {datos.source}.")
        self.notebook.select(self.tab_datos)

    # ------------------------------------------------------------------
    # Resolucion del problema
    # ------------------------------------------------------------------
    def resolve(self) -> None:
        """Ejecuta el Metodo Hungaro y actualiza resultados y grafo."""
        try:
            matriz = self.get_matrix()
            solver = HungarianSolver(matriz, self.objective_var.get())
            resultado = solver.solve()
        except (ValueError, RuntimeError) as error:
            messagebox.showerror("No se pudo resolver", str(error))
            return
        except Exception as error:  # Red de seguridad ante errores inesperados.
            messagebox.showerror(
                "Error inesperado", f"Ocurrio un error al resolver: {error}"
            )
            return

        self.current_result = resultado
        self._show_results(resultado)
        self.graph_view.draw(resultado)
        self._clear_ai_text()
        self.status_var.set("Asignacion optima calculada correctamente.")
        self.notebook.select(self.tab_grafo)

    def _show_results(self, resultado: AssignmentResult) -> None:
        """Redacta el resumen de la solucion en el panel de resultados."""
        objetivo = (
            "Maximizacion (beneficios/desempeno)"
            if resultado.objective == "max"
            else "Minimizacion (costos/tiempos)"
        )
        lineas = [
            f"Objetivo: {objetivo}",
            f"Dimensiones originales: {resultado.num_agents} agentes x "
            f"{resultado.num_tasks} tareas",
            "Auto-balanceo: "
            + ("Aplicado (se agregaron nodos ficticios)" if resultado.was_balanced
               else "No requerido"),
            "",
            "Asignaciones optimas:",
        ]

        if resultado.real_assignments:
            for agente, tarea, valor in resultado.real_assignments:
                lineas.append(
                    f"  {agente} -> {tarea}   (valor: {self._format_number(valor)})"
                )
        else:
            lineas.append("  (no hubo asignaciones reales)")

        etiqueta_total = "beneficio" if resultado.objective == "max" else "costo"
        lineas.extend(
            [
                "",
                f"Valor total ({etiqueta_total}): "
                f"{self._format_number(resultado.total_value)}",
            ]
        )

        if resultado.inactive_agents:
            lineas.append(
                "Recursos inactivos (asignados a tareas ficticias): "
                + ", ".join(resultado.inactive_agents)
            )
        if resultado.orphan_tasks:
            lineas.append(
                "Tareas huerfanas (sin agente real): "
                + ", ".join(resultado.orphan_tasks)
            )

        self._set_results("\n".join(lineas))

    # ------------------------------------------------------------------
    # Integracion con IA
    # ------------------------------------------------------------------
    def _update_ai_status(self) -> None:
        """Muestra si la clave de Gemini esta configurada."""
        if self.ai_agent.is_configured:
            self.ai_status.configure(
                text=f"Configurado con el modelo {self.ai_agent.model}."
            )
        else:
            self.ai_status.configure(
                text="Falta GEMINI_API_KEY en el archivo .env.",
                foreground="#b00020",
            )

    def generate_ai(self) -> None:
        """Lanza el analisis de IA en un hilo para no congelar la interfaz."""
        if self.current_result is None:
            messagebox.showwarning(
                "Sin resultados",
                "Primero resuelva una asignacion antes de solicitar el analisis.",
            )
            return
        if not self.ai_agent.is_configured:
            messagebox.showerror(
                "IA no configurada",
                "Agregue su GEMINI_API_KEY en el archivo .env y reinicie la aplicacion.",
            )
            return

        self.ai_button.configure(state="disabled")
        self.ai_status.configure(text="Consultando a Gemini...", foreground="#555555")
        hilo = threading.Thread(
            target=self._ai_worker, args=(self.current_result,), daemon=True
        )
        hilo.start()

    def _ai_worker(self, resultado: AssignmentResult) -> None:
        """Trabajo del hilo secundario: solo llama a la API, no toca la GUI."""
        try:
            texto = self.ai_agent.analyze(resultado)
        except AIAgentError as error:
            self.after(0, self._ai_done, None, str(error))
        except Exception as error:  # Red de seguridad.
            self.after(0, self._ai_done, None, f"Error inesperado: {error}")
        else:
            self.after(0, self._ai_done, texto, None)

    def _ai_done(self, texto: Optional[str], error: Optional[str]) -> None:
        """Actualiza la interfaz cuando termina la llamada a la IA."""
        self.ai_button.configure(state="normal")

        if error:
            self.ai_status.configure(text="Error en la consulta.", foreground="#b00020")
            messagebox.showerror("Error de IA", error)
            return

        self.ai_status.configure(text="Analisis generado.", foreground="#1b5e20")
        self.ai_text.configure(state="normal")
        self.ai_text.delete("1.0", "end")
        self.ai_text.insert("end", texto or "")
        self.ai_text.configure(state="disabled")

    def _clear_ai_text(self) -> None:
        """Limpia el panel de IA al cambiar de problema."""
        self.ai_text.configure(state="normal")
        self.ai_text.delete("1.0", "end")
        self.ai_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Utilidades de presentacion
    # ------------------------------------------------------------------
    def _set_results(self, texto: str) -> None:
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.insert("end", texto)
        self.results_text.configure(state="disabled")

    @staticmethod
    def _format_number(valor: float) -> str:
        """Muestra enteros sin decimales y el resto con dos decimales."""
        if abs(valor - round(valor)) < 1e-9:
            return str(int(round(valor)))
        return f"{valor:.2f}"
