"""Modelos de datos compartidos por los modulos del sistema."""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class AssignmentResult:
    """Resultado completo de la resolucion de un problema de asignacion.

    Atributos:
        original_matrix: Matriz tal como la ingreso el usuario.
        objective: Objetivo del problema ("min" o "max").
        num_agents: Cantidad original de agentes (filas).
        num_tasks: Cantidad original de tareas (columnas).
        balanced_matrix: Matriz ya balanceada con ceros en filas/columnas ficticias.
        assignment_matrix: Matriz cuadrada con 1 en las asignaciones elegidas.
        agent_labels: Etiquetas de todos los agentes (incluye ficticios).
        task_labels: Etiquetas de todas las tareas (incluye ficticias).
        real_assignments: Lista de (agente, tarea, valor) reales.
        inactive_agents: Agentes reales asignados a tareas ficticias.
        orphan_tasks: Tareas reales asignadas a agentes ficticios.
        total_value: Costo total (min) o beneficio total (max) de la asignacion real.
        was_balanced: Indica si fue necesario aplicar auto-balanceo.
    """

    original_matrix: List[List[float]]
    objective: str
    num_agents: int
    num_tasks: int
    balanced_matrix: List[List[float]]
    assignment_matrix: List[List[int]]
    agent_labels: List[str]
    task_labels: List[str]
    real_assignments: List[Tuple[str, str, float]]
    inactive_agents: List[str]
    orphan_tasks: List[str]
    total_value: float
    was_balanced: bool
