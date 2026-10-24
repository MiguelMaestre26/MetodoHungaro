"""Ingesta dinamica de matrices desde CSV, JSON o datos por defecto."""

import csv
import json
import math
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence


@dataclass
class LoadedData:
    """Datos leidos de una fuente, junto con metadatos utiles para la GUI."""

    matrix: List[List[float]]
    objective: Optional[str]
    source: str


class DataLoader:
    """Lee y valida matrices de costos/beneficios para el Metodo Hungaro."""

    # Matriz por defecto en memoria (contingencia si falla el archivo externo).
    DEFAULT_MATRIX: List[List[float]] = [
        [9.0, 2.0, 7.0, 8.0],
        [6.0, 4.0, 3.0, 7.0],
        [5.0, 8.0, 1.0, 8.0],
        [7.0, 6.0, 9.0, 4.0],
    ]

    # ------------------------------------------------------------------
    # Fuentes de datos
    # ------------------------------------------------------------------
    @classmethod
    def default_data(cls) -> LoadedData:
        """Devuelve una copia de la matriz de contingencia cargada en memoria."""
        matriz = [fila[:] for fila in cls.DEFAULT_MATRIX]
        return LoadedData(matrix=matriz, objective=None, source="Matriz por defecto")

    @classmethod
    def load_csv(cls, path: str) -> LoadedData:
        """Carga una matriz desde un archivo CSV.

        Se admite una fila de encabezado opcional. Las celdas deben ser numericas
        y todas las filas deben tener la misma cantidad de columnas.
        """
        if not path:
            raise ValueError("No se selecciono ningun archivo CSV.")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"No existe el archivo CSV: {path}")

        filas_crudas: List[List[str]] = []
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as archivo:
                lector = csv.reader(archivo)
                for fila in lector:
                    # Se ignoran filas totalmente vacias.
                    if any(celda.strip() for celda in fila):
                        filas_crudas.append(fila)
        except csv.Error as error:
            raise ValueError(f"El CSV tiene un formato invalido: {error}") from error
        except OSError as error:
            raise OSError(f"No se pudo leer el archivo CSV: {error}") from error

        if not filas_crudas:
            raise ValueError("El archivo CSV esta vacio.")

        # Si la primera fila no es numerica, se interpreta como encabezado,
        # salvo que solo su primera celda sea una etiqueta (fila de datos).
        primera = filas_crudas[0]
        if not cls._row_is_numeric(primera):
            es_fila_con_etiqueta = (
                len(primera) > 1
                and not cls._row_is_numeric([primera[0]])
                and cls._row_is_numeric(primera[1:])
            )
            if not es_fila_con_etiqueta:
                filas_crudas = filas_crudas[1:]

        if not filas_crudas:
            raise ValueError("El CSV no contiene datos despues del encabezado.")

        # Si la primera columna contiene etiquetas (por ejemplo "A1") y el resto
        # son numeros, se descarta esa columna de identificadores.
        if len(filas_crudas[0]) > 1 and all(
            len(fila) == len(filas_crudas[0])
            and not cls._row_is_numeric([fila[0]])
            and cls._row_is_numeric(fila[1:])
            for fila in filas_crudas
        ):
            filas_crudas = [fila[1:] for fila in filas_crudas]

        matriz = cls._convert_rows(filas_crudas, "CSV")
        cls.validate_matrix(matriz)
        return LoadedData(matrix=matriz, objective=None, source="Archivo CSV")

    @classmethod
    def load_json(cls, path: str) -> LoadedData:
        """Carga una matriz desde un JSON.

        Formatos aceptados:
            [[1, 2], [3, 4]]
            {"matrix": [[1, 2], [3, 4]], "objective": "max"}
        """
        if not path:
            raise ValueError("No se selecciono ningun archivo JSON.")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"No existe el archivo JSON: {path}")

        try:
            with open(path, "r", encoding="utf-8-sig") as archivo:
                datos = json.load(archivo)
        except json.JSONDecodeError as error:
            raise ValueError(f"El JSON tiene un formato invalido: {error}") from error
        except OSError as error:
            raise OSError(f"No se pudo leer el archivo JSON: {error}") from error

        objetivo: Optional[str] = None
        if isinstance(datos, dict):
            if "matrix" not in datos:
                raise ValueError("El JSON debe contener la clave 'matrix'.")
            if "objective" in datos:
                objetivo = str(datos["objective"]).strip().lower()
                if objetivo not in {"min", "max", "minimizar", "maximizar"}:
                    raise ValueError(
                        "El campo 'objective' del JSON debe ser 'min' o 'max'."
                    )
                objetivo = "max" if objetivo.startswith("max") else "min"
            datos = datos["matrix"]

        if not isinstance(datos, list):
            raise ValueError("La matriz del JSON debe ser una lista de listas.")

        # Validar que cada elemento sea una lista/arreglo de numeros.
        if not all(isinstance(fila, list) for fila in datos):
            raise ValueError("Cada fila de la matriz JSON debe ser una lista.")

        try:
            matriz = [[float(valor) for valor in fila] for fila in datos]
        except (TypeError, ValueError) as error:
            raise ValueError(
                "La matriz JSON contiene valores que no son numericos."
            ) from error

        cls.validate_matrix(matriz)
        return LoadedData(matrix=matriz, objective=objetivo, source="Archivo JSON")

    # ------------------------------------------------------------------
    # Utilidades de validacion
    # ------------------------------------------------------------------
    @staticmethod
    def validate_matrix(matrix: Sequence[Sequence[float]]) -> None:
        """Valida que la matriz no este vacia, sea rectangular y numerica."""
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
                if not isinstance(valor, (int, float)) or isinstance(valor, bool):
                    raise ValueError(
                        f"La fila {indice + 1} contiene un valor no numerico."
                    )
                if not math.isfinite(float(valor)):
                    raise ValueError(
                        f"La fila {indice + 1} contiene un valor no finito."
                    )

    @staticmethod
    def _row_is_numeric(row: Sequence[str]) -> bool:
        """Indica si todas las celdas de una fila pueden convertirse a numero."""
        for celda in row:
            try:
                float(celda.strip().replace(",", "."))
            except (TypeError, ValueError):
                return False
        return True

    @classmethod
    def _convert_rows(
        cls, filas: Sequence[Sequence[str]], origen: str
    ) -> List[List[float]]:
        """Convierte filas de texto a numeros aplicando validaciones."""
        matriz: List[List[float]] = []
        for i, fila in enumerate(filas):
            fila_convertida: List[float] = []
            for j, celda in enumerate(fila):
                texto = celda.strip().replace(",", ".")
                try:
                    fila_convertida.append(float(texto))
                except ValueError as error:
                    raise ValueError(
                        f"Valor no numerico en el {origen} (fila {i + 1}, "
                        f"columna {j + 1}): '{celda}'."
                    ) from error
            matriz.append(fila_convertida)
        return matriz
