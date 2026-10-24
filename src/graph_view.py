"""Representacion visual del resultado como grafo bipartito."""

from typing import Dict, List, Tuple

import networkx as nx
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from .models import AssignmentResult

# Colores usados en la visualizacion.
COLOR_AGENTE = "#1f6fb2"
COLOR_TAREA = "#2e8b57"
COLOR_FICTICIO = "#8a8a8a"
COLOR_ARISTA_REAL = "#2e7d32"
COLOR_ARISTA_FICTICIA = "#c62828"


class BipartiteGraphView:
    """Widget de Matplotlib embebido en Tkinter para dibujar el grafo bipartito."""

    def __init__(self, parent) -> None:
        self.parent = parent
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.toolbar = NavigationToolbar2Tk(self.canvas, parent)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self._draw_placeholder()

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def clear(self) -> None:
        """Restablece el widget a su estado inicial."""
        self._draw_placeholder()

    def _draw_placeholder(self) -> None:
        """Mensaje inicial cuando aun no existe una solucion."""
        self.figure.clear()
        eje = self.figure.add_subplot(111)
        eje.text(
            0.5,
            0.5,
            "Resuelva un problema de asignacion\npara visualizar el grafo bipartito.",
            ha="center",
            va="center",
            fontsize=12,
            color="#555555",
        )
        eje.axis("off")
        self.canvas.draw()

    def draw(self, result: AssignmentResult) -> None:
        """Dibuja agentes, tareas y las aristas de la asignacion optima."""
        self.figure.clear()
        eje = self.figure.add_subplot(111)

        # Nodos reales a partir de las asignaciones y los recursos sin uso.
        agentes = [agente for agente, _, _ in result.real_assignments]
        agentes.extend(result.inactive_agents)
        tareas = [tarea for _, tarea, _ in result.real_assignments]
        tareas.extend(result.orphan_tasks)

        agentes = self._unique(agentes)
        tareas = self._unique(tareas)

        # Nodos ficticios (solo existen si el problema original era desbalanceado).
        nodo_agente_ficticio = "Ficticio: agente" if result.orphan_tasks else None
        nodo_tarea_ficticia = "Ficticio: tarea" if result.inactive_agents else None

        if nodo_agente_ficticio:
            agentes.append(nodo_agente_ficticio)
        if nodo_tarea_ficticia:
            tareas.append(nodo_tarea_ficticia)

        grafo = nx.Graph()
        grafo.add_nodes_from(agentes)
        grafo.add_nodes_from(tareas)

        # Aristas reales y aristas que tocan un nodo ficticio.
        aristas_reales: List[Tuple[str, str]] = [
            (agente, tarea) for agente, tarea, _ in result.real_assignments
        ]
        aristas_ficticias: List[Tuple[str, str]] = []
        if nodo_tarea_ficticia:
            aristas_ficticias.extend(
                (agente, nodo_tarea_ficticia) for agente in result.inactive_agents
            )
        if nodo_agente_ficticio:
            aristas_ficticias.extend(
                (nodo_agente_ficticio, tarea) for tarea in result.orphan_tasks
            )

        grafo.add_edges_from(aristas_reales)
        grafo.add_edges_from(aristas_ficticias)

        posiciones = self._positions(agentes, tareas)
        atributos_nodos = self._node_attributes(grafo, agentes, tareas)

        nx.draw_networkx_nodes(
            grafo,
            posiciones,
            node_color=atributos_nodos["colores"],
            node_size=atributos_nodos["tamanos"],
            edgecolors="white",
            linewidths=1.5,
            ax=eje,
        )
        nx.draw_networkx_labels(
            grafo,
            posiciones,
            labels=atributos_nodos["etiquetas"],
            font_size=9,
            font_color="white",
            font_weight="bold",
            ax=eje,
        )

        aristas = aristas_reales + aristas_ficticias
        colores = [COLOR_ARISTA_REAL] * len(aristas_reales) + [
            COLOR_ARISTA_FICTICIA
        ] * len(aristas_ficticias)
        estilos = ["solid"] * len(aristas_reales) + ["dashed"] * len(
            aristas_ficticias
        )
        anchos = [2.4] * len(aristas_reales) + [2.0] * len(aristas_ficticias)

        nx.draw_networkx_edges(
            grafo,
            posiciones,
            edgelist=aristas,
            edge_color=colores,
            style=estilos,
            width=anchos,
            ax=eje,
        )

        # Etiqueta con el valor solo en las aristas reales.
        etiquetas_aristas = {
            (agente, tarea): self._format_value(valor)
            for agente, tarea, valor in result.real_assignments
        }
        if etiquetas_aristas:
            nx.draw_networkx_edge_labels(
                grafo,
                posiciones,
                edge_labels=etiquetas_aristas,
                font_size=8,
                font_color="#1a1a1a",
                bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none"},
                ax=eje,
            )

        # Leyenda explicativa.
        leyenda = [
            Line2D([0], [0], color=COLOR_ARISTA_REAL, lw=2.5, label="Asignacion optima"),
            Line2D(
                [0],
                [0],
                color=COLOR_ARISTA_FICTICIA,
                lw=2.0,
                linestyle="--",
                label="Recurso/tarea ficticia",
            ),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=COLOR_AGENTE,
                   markersize=10, label="Agente"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=COLOR_TAREA,
                   markersize=10, label="Tarea"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=COLOR_FICTICIO,
                   markersize=10, label="Nodo ficticio"),
        ]
        eje.legend(handles=leyenda, loc="upper center", bbox_to_anchor=(0.5, -0.02),
                   ncol=3, frameon=False, fontsize=8)

        objetivo = "Maximizacion" if result.objective == "max" else "Minimizacion"
        eje.set_title(
            f"Asignacion optima ({objetivo}) - Grafo bipartito", fontsize=12
        )
        eje.axis("off")
        eje.margins(x=0.18, y=0.08)
        self.figure.tight_layout()
        self.canvas.draw()

    # ------------------------------------------------------------------
    # Utilidades de dibujo
    # ------------------------------------------------------------------
    @staticmethod
    def _unique(items: List[str]) -> List[str]:
        """Mantiene el orden eliminando elementos repetidos."""
        vistos: set = set()
        resultado: List[str] = []
        for item in items:
            if item not in vistos:
                vistos.add(item)
                resultado.append(item)
        return resultado

    @staticmethod
    def _positions(
        agentes: List[str], tareas: List[str]
    ) -> Dict[str, Tuple[float, float]]:
        """Asigna posiciones en dos columnas (agentes a la izquierda)."""
        posiciones: Dict[str, Tuple[float, float]] = {}

        def distribuir(nodos: List[str], x: float) -> None:
            cantidad = len(nodos)
            if cantidad == 1:
                posiciones[nodos[0]] = (x, 0.5)
                return
            for indice, nodo in enumerate(nodos):
                y = 1.0 - indice * (1.0 / (cantidad - 1))
                posiciones[nodo] = (x, y)

        distribuir(agentes, 0.0)
        distribuir(tareas, 1.0)
        return posiciones

    @staticmethod
    def _node_attributes(
        grafo: nx.Graph, agentes: List[str], tareas: List[str]
    ) -> Dict[str, object]:
        """Calcula colores, tamanos y etiquetas de cada nodo."""
        colores: List[str] = []
        tamanos: List[int] = []
        etiquetas: Dict[str, str] = {}

        for nodo in grafo.nodes():
            if nodo.startswith("Ficticio"):
                colores.append(COLOR_FICTICIO)
                tamanos.append(1500)
                etiquetas[nodo] = nodo.replace("Ficticio: ", "")
            elif nodo in agentes:
                colores.append(COLOR_AGENTE)
                tamanos.append(1800)
                etiquetas[nodo] = nodo
            else:
                colores.append(COLOR_TAREA)
                tamanos.append(1800)
                etiquetas[nodo] = nodo

        return {"colores": colores, "tamanos": tamanos, "etiquetas": etiquetas}

    @staticmethod
    def _format_value(valor: float) -> str:
        """Formatea un valor evitando decimales innecesarios."""
        if abs(valor - round(valor)) < 1e-9:
            return str(int(round(valor)))
        return f"{valor:.2f}"
