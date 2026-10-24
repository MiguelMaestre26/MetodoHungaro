"""Motor del Metodo Hungaro implementado desde cero.

No se utiliza ninguna libreria de optimizacion: tanto el manejo de matrices
como el cruce de lineas (cobertura de ceros) se implementan con listas nativas.
"""

import math
from typing import List, Tuple

from .models import AssignmentResult

# Tolerancia usada para comparar numeros decimales con cero.
EPS = 1e-9


class HungarianSolver:
    """Resuelve problemas de asignacion uno a uno con el Metodo Hungaro.

    El flujo general es:
        1. Validar la matriz recibida.
        2. Balancear la matriz si no es cuadrada (auto-balanceo).
        3. Convertir a minimizacion si el objetivo es maximizar.
        4. Aplicar los pasos clasicos del Metodo Hungaro.
        5. Traducir la solucion a agentes/tareas, detectando nodos ficticios.
    """

    def __init__(self, matrix: List[List[float]], objective: str = "min") -> None:
        self._validate_matrix(matrix)
        self.original_matrix: List[List[float]] = [
            [float(value) for value in row] for row in matrix
        ]
        self.objective: str = self._normalize_objective(objective)
        self.num_agents: int = len(self.original_matrix)
        self.num_tasks: int = len(self.original_matrix[0])

        # Datos calculados durante la resolucion.
        self.balanced_matrix: List[List[float]] = []
        self.working_matrix: List[List[float]] = []
        self.agent_labels: List[str] = []
        self.task_labels: List[str] = []

    # ------------------------------------------------------------------
    # Validacion y normalizacion
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_matrix(matrix: List[List[float]]) -> None:
        """Comprueba que la matriz sea rectangular, no vacia y numerica."""
        if not matrix or not matrix[0]:
            raise ValueError("La matriz no puede estar vacia.")

        columnas = len(matrix[0])
        for indice, fila in enumerate(matrix):
            if len(fila) != columnas:
                raise ValueError(
                    f"La fila {indice + 1} tiene {len(fila)} columnas; "
                    f"se esperaban {columnas}."
                )
            for valor in fila:
                if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                    raise ValueError(
                        f"La fila {indice + 1} contiene un valor no numerico: {valor!r}."
                    )
                if not math.isfinite(float(valor)):
                    raise ValueError(
                        f"La fila {indice + 1} contiene un valor no finito: {valor!r}."
                    )

    @staticmethod
    def _normalize_objective(objective: str) -> str:
        """Acepta variantes como 'min', 'minimizar', 'max' o 'maximizar'."""
        texto = str(objective).strip().lower()
        if texto in {"min", "minimizar", "minimizacion"}:
            return "min"
        if texto in {"max", "maximizar", "maximizacion"}:
            return "max"
        raise ValueError("El objetivo debe ser 'min' (minimizar) o 'max' (maximizar).")

    # ------------------------------------------------------------------
    # Balanceo y transformacion del objetivo
    # ------------------------------------------------------------------
    def _balance_matrix(self) -> None:
        """Agrega filas o columnas ficticias con costo/beneficio cero."""
        tamano = max(self.num_agents, self.num_tasks)

        # Copia profunda de la matriz original para no modificarla.
        balanced = [fila[:] for fila in self.original_matrix]

        # Si hay menos agentes que tareas, se agregan agentes ficticios (filas).
        while len(balanced) < tamano:
            balanced.append([0.0] * tamano)

        # Si hay menos tareas que agentes, se agregan tareas ficticias (columnas).
        for fila in balanced:
            while len(fila) < tamano:
                fila.append(0.0)

        self.balanced_matrix = balanced

        # Etiquetas legibles para agentes y tareas (reales y ficticios).
        self.agent_labels = [f"A{i + 1}" for i in range(self.num_agents)]
        self.agent_labels.extend(
            f"Agente ficticio {i + 1}" for i in range(tamano - self.num_agents)
        )
        self.task_labels = [f"T{j + 1}" for j in range(self.num_tasks)]
        self.task_labels.extend(
            f"Tarea ficticia {j + 1}" for j in range(tamano - self.num_tasks)
        )

    def _to_minimization(self) -> None:
        """Convierte un problema de maximizacion en uno de minimizacion.

        Para maximizar se aplica la transformacion  valor' = maximo - valor.
        Asi el mayor beneficio se convierte en el menor costo.
        """
        if self.objective == "max":
            maximo = max(max(fila) for fila in self.balanced_matrix)
            self.working_matrix = [
                [maximo - valor for valor in fila] for fila in self.balanced_matrix
            ]
        else:
            self.working_matrix = [fila[:] for fila in self.balanced_matrix]

    # ------------------------------------------------------------------
    # Algoritmo hungaro clasico por pasos
    # ------------------------------------------------------------------
    def solve(self) -> AssignmentResult:
        """Ejecuta el algoritmo y devuelve un AssignmentResult."""
        self._balance_matrix()
        self._to_minimization()

        matriz = [fila[:] for fila in self.working_matrix]
        tamano = len(matriz)

        # Paso 1: restar el minimo de cada fila.
        for i in range(tamano):
            minimo_fila = min(matriz[i])
            if abs(minimo_fila) > EPS:
                for j in range(tamano):
                    matriz[i][j] -= minimo_fila

        # Paso 2: restar el minimo de cada columna.
        for j in range(tamano):
            minimo_columna = min(matriz[i][j] for i in range(tamano))
            if abs(minimo_columna) > EPS:
                for i in range(tamano):
                    matriz[i][j] -= minimo_columna

        # Pasos 3 y 4: cubrir ceros con el minimo numero de lineas (König) y,
        # si no son suficientes, ajustar la matriz y repetir.
        max_iteraciones = max(1, tamano * tamano * 20)
        for _ in range(max_iteraciones):
            match_row, filas_cubiertas, columnas_cubiertas = self._matching_and_cover(
                matriz
            )
            if len(filas_cubiertas) + len(columnas_cubiertas) >= tamano:
                break

            # Menor valor no cubierto por ninguna linea.
            conj_filas = set(filas_cubiertas)
            conj_columnas = set(columnas_cubiertas)
            minimo_no_cubierto = min(
                matriz[i][j]
                for i in range(tamano)
                for j in range(tamano)
                if i not in conj_filas and j not in conj_columnas
            )

            # Restar a las celdas no cubiertas y sumar en las intersecciones.
            for i in range(tamano):
                for j in range(tamano):
                    if i in conj_filas and j in conj_columnas:
                        matriz[i][j] += minimo_no_cubierto
                    elif i not in conj_filas and j not in conj_columnas:
                        matriz[i][j] -= minimo_no_cubierto
        else:
            raise RuntimeError("El algoritmo no convergio; revise los datos de entrada.")

        # Construccion del resultado a partir del emparejamiento final.
        assignment_matrix = [[0] * tamano for _ in range(tamano)]
        for i in range(tamano):
            j = match_row[i]
            if j < 0:
                raise RuntimeError("No se encontro una asignacion completa.")
            assignment_matrix[i][j] = 1

        return self._build_result(assignment_matrix)

    def _matching_and_cover(
        self, matriz: List[List[float]]
    ) -> Tuple[List[int], List[int], List[int]]:
        """Calcula el maximo emparejamiento sobre ceros y la cobertura minima.

        Se usa el teorema de König: en un grafo bipartito, el tamano del
        emparejamiento maximo es igual al de la cobertura minima de vertices.
        Las lineas (filas/columnas) cubiertas son esa cobertura.
        """
        tamano = len(matriz)

        # Grafo bipartito de ceros: fila i conectada con columna j si matriz[i][j] ~ 0.
        adyacencia = [
            [j for j in range(tamano) if abs(matriz[i][j]) <= EPS]
            for i in range(tamano)
        ]

        match_row = [-1] * tamano  # match_row[i] = columna asignada a la fila i
        match_col = [-1] * tamano  # match_col[j] = fila asignada a la columna j

        def aumentar(fila: int, visitadas: List[bool]) -> bool:
            """Busca un camino de aumento (Kuhn) para la fila indicada."""
            for columna in adyacencia[fila]:
                if visitadas[columna]:
                    continue
                visitadas[columna] = True
                if match_col[columna] == -1 or aumentar(
                    match_col[columna], visitadas
                ):
                    match_col[columna] = fila
                    match_row[fila] = columna
                    return True
            return False

        for fila in range(tamano):
            aumentar(fila, [False] * tamano)

        # Cobertura minima de vertices a partir del emparejamiento maximo.
        filas_visitadas = [False] * tamano
        columnas_visitadas = [False] * tamano

        pila = [i for i in range(tamano) if match_row[i] == -1]
        for fila in pila:
            filas_visitadas[fila] = True

        while pila:
            fila = pila.pop()
            for columna in adyacencia[fila]:
                # Solo se recorren aristas que NO pertenecen al emparejamiento.
                if match_row[fila] == columna:
                    continue
                if not columnas_visitadas[columna]:
                    columnas_visitadas[columna] = True
                    fila_emparejada = match_col[columna]
                    if fila_emparejada != -1 and not filas_visitadas[fila_emparejada]:
                        filas_visitadas[fila_emparejada] = True
                        pila.append(fila_emparejada)

        # Cobertura = (filas no visitadas) union (columnas visitadas).
        filas_cubiertas = [
            i for i in range(tamano) if not filas_visitadas[i]
        ]
        columnas_cubiertas = [
            j for j in range(tamano) if columnas_visitadas[j]
        ]
        return match_row, filas_cubiertas, columnas_cubiertas

    # ------------------------------------------------------------------
    # Traduccion de la solucion
    # ------------------------------------------------------------------
    def _build_result(self, assignment_matrix: List[List[int]]) -> AssignmentResult:
        """Convierte la matriz de asignacion en informacion para el usuario."""
        real_assignments: List[Tuple[str, str, float]] = []
        inactive_agents: List[str] = []
        orphan_tasks: List[str] = []
        total = 0.0

        for i, fila in enumerate(assignment_matrix):
            for j, marcado in enumerate(fila):
                if not marcado:
                    continue

                agente_real = i < self.num_agents
                tarea_real = j < self.num_tasks
                etiqueta_agente = self.agent_labels[i]
                etiqueta_tarea = self.task_labels[j]

                if agente_real and tarea_real:
                    # Asignacion real: se toma el valor de la matriz original.
                    valor = self.original_matrix[i][j]
                    real_assignments.append((etiqueta_agente, etiqueta_tarea, valor))
                    total += valor
                elif agente_real and not tarea_real:
                    # Un agente real quedo sin tarea real: recurso inactivo.
                    inactive_agents.append(etiqueta_agente)
                elif not agente_real and tarea_real:
                    # Una tarea real quedo sin agente real: tarea huerfana.
                    orphan_tasks.append(etiqueta_tarea)
                # Si ambos son ficticios no aporta informacion relevante.

        return AssignmentResult(
            original_matrix=self.original_matrix,
            objective=self.objective,
            num_agents=self.num_agents,
            num_tasks=self.num_tasks,
            balanced_matrix=self.balanced_matrix,
            assignment_matrix=assignment_matrix,
            agent_labels=self.agent_labels,
            task_labels=self.task_labels,
            real_assignments=real_assignments,
            inactive_agents=inactive_agents,
            orphan_tasks=orphan_tasks,
            total_value=total,
            was_balanced=self.num_agents != self.num_tasks,
        )
