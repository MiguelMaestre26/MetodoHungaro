"""Integracion con la API REST de Google Gemini (agente de RRHH)."""

import os
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv

from .models import AssignmentResult

# Se carga el .env ubicado en la raiz del proyecto, sin importar el directorio
# desde el cual se ejecute la aplicacion.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

# Algunos modelos dejan de estar disponibles para cuentas nuevas. Si el modelo
# configurado falla, se intentan estos respaldos en orden.
MODELOS_RESPALDO = [
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.8-flash",
]


class AIAgentError(Exception):
    """Error controlado al comunicarse con la API de IA."""


class GeminiAgent:
    """Construye el prompt y consulta a Gemini como Gerente de Operaciones/RRHH."""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        timeout: int = 45,
    ) -> None:
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.model = (model or os.getenv("GEMINI_MODEL", "")).strip() or "gemini-3.5-flash"
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        """Indica si existe una clave de API disponible."""
        return bool(self.api_key)

    # ------------------------------------------------------------------
    # Construccion del prompt
    # ------------------------------------------------------------------
    def build_prompt(self, result: AssignmentResult) -> str:
        """Construye dinamicamente el prompt con todos los datos del problema."""
        matriz_original = self._format_matrix(result.original_matrix)
        asignaciones = self._format_assignments(result)
        objetivo = (
            "Maximizacion (beneficios o calificaciones de desempeno)"
            if result.objective == "max"
            else "Minimizacion (costos operativos o tiempos de entrega)"
        )
        inactivos = ", ".join(result.inactive_agents) or "Ninguno"
        huerfanas = ", ".join(result.orphan_tasks) or "Ninguna"
        balanceo = "Si (se usaron nodos ficticios)" if result.was_balanced else "No"

        return (
            "Actua como Gerente de Operaciones y Recursos Humanos de la empresa "
            '"Rutas y Suministros C.A." Una nueva flota de vehiculos especializados '
            "debe asignarse a conductores para cubrir rutas express.\n\n"
            "Datos del problema resuelto con el Metodo Hungaro:\n"
            f"- Objetivo: {objetivo}.\n"
            f"- Dimensiones originales: {result.num_agents} agentes x "
            f"{result.num_tasks} tareas.\n"
            f"- Auto-balanceo aplicado: {balanceo}.\n"
            f"- Matriz original (filas = agentes, columnas = tareas):\n{matriz_original}\n\n"
            f"- Asignaciones optimas finales (agente -> tarea: valor):\n{asignaciones}\n"
            f"- Valor total de la asignacion: {self._format_number(result.total_value)}\n"
            f"- Recursos inactivos (agentes asignados a tareas ficticias): {inactivos}\n"
            f"- Tareas huerfanas (sin agente real): {huerfanas}\n\n"
            "Entrega un analisis ejecutivo en un maximo de DOS parrafos. En el "
            "primero evalua el impacto operativo y economico de la asignacion. En "
            "el segundo incluye obligatoriamente una recomendacion de negocio "
            "concreta sobre que hacer con los recursos inactivos o las tareas "
            "huerfanas. No uses listas ni encabezados; escribe solo los dos parrafos."
        )

    # ------------------------------------------------------------------
    # Llamada a la API
    # ------------------------------------------------------------------
    def analyze(self, result: AssignmentResult) -> str:
        """Envia el prompt a Gemini y devuelve el analisis ejecutivo.

        Si el modelo configurado ya no esta disponible o esta saturado, se
        reintenta automaticamente con los modelos de respaldo.
        """
        if not self.is_configured:
            raise AIAgentError(
                "No se encontro GEMINI_API_KEY. Agrega tu clave en el archivo .env."
            )

        prompt = self.build_prompt(result)
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        errores: List[str] = []

        for modelo in self._candidate_models():
            url = GEMINI_ENDPOINT.format(model=modelo)
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": self._generation_config(modelo),
            }
            try:
                respuesta = requests.post(
                    url, headers=headers, json=payload, timeout=self.timeout
                )
            except requests.Timeout:
                errores.append(f"{modelo}: tiempo de espera agotado.")
                continue
            except requests.RequestException as error:
                raise AIAgentError(
                    f"No se pudo conectar con la API de Gemini: {error}"
                ) from error

            if respuesta.status_code == 200:
                try:
                    datos = respuesta.json()
                except ValueError as error:
                    raise AIAgentError(
                        "Gemini devolvio una respuesta que no es JSON valido."
                    ) from error
                return self._extract_text(datos)

            mensaje = self._extract_api_error(respuesta)
            errores.append(mensaje)
            # Solo se prueba otro modelo si el problema es de disponibilidad,
            # cuota o saturacion; otros errores se reportan de inmediato.
            if respuesta.status_code not in {404, 429, 503}:
                raise AIAgentError(mensaje)

        detalle = "\n".join(f"- {error}" for error in errores)
        raise AIAgentError(
            "No se pudo obtener respuesta de los modelos de Gemini:\n"
            f"{detalle}\n\n"
            "Verifique el valor de GEMINI_MODEL en el archivo .env."
        )

    def _candidate_models(self) -> List[str]:
        """Lista de modelos a intentar, comenzando por el configurado."""
        candidatos = [self.model]
        for modelo in MODELOS_RESPALDO:
            if modelo not in candidatos:
                candidatos.append(modelo)
        return candidatos

    @staticmethod
    def _generation_config(modelo: str) -> dict:
        """Configuracion de generacion adaptada al modelo.

        Los modelos Gemini 3 usan razonamiento interno; con 'thinkingLevel' bajo
        se evita que el presupuesto de salida se consuma en ese razonamiento.
        """
        config = {"temperature": 0.4, "maxOutputTokens": 4096}
        if modelo.startswith("gemini-3"):
            config["thinkingConfig"] = {"thinkingLevel": "low"}
        return config

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_text(datos: dict) -> str:
        """Extrae el texto del analisis desde la estructura de Gemini."""
        candidatos = datos.get("candidates") or []
        if not candidatos:
            motivo = datos.get("promptFeedback", {}).get("blockReason")
            if motivo:
                raise AIAgentError(
                    f"Gemini bloqueo la solicitud por seguridad ({motivo})."
                )
            raise AIAgentError("Gemini no devolvio ningun candidato de respuesta.")

        partes = candidatos[0].get("content", {}).get("parts", [])
        texto = "".join(parte.get("text", "") for parte in partes).strip()
        if not texto:
            raise AIAgentError("La respuesta de Gemini esta vacia.")
        return texto

    @staticmethod
    def _extract_api_error(respuesta: requests.Response) -> str:
        """Obtiene un mensaje legible del error devuelto por la API."""
        try:
            detalle = respuesta.json().get("error", {})
            mensaje = detalle.get("message", "")
        except ValueError:
            mensaje = respuesta.text[:200]
        if not mensaje:
            mensaje = "Error desconocido de la API."
        return f"Error de Gemini ({respuesta.status_code}): {mensaje}"

    @staticmethod
    def _format_number(valor: float) -> str:
        """Formatea un numero de forma compacta."""
        if abs(valor - round(valor)) < 1e-9:
            return str(int(round(valor)))
        return f"{valor:.2f}"

    @classmethod
    def _format_matrix(cls, matrix: List[List[float]]) -> str:
        """Convierte la matriz en texto tabulado para el prompt."""
        lineas = []
        for indice, fila in enumerate(matrix):
            valores = " | ".join(cls._format_number(valor) for valor in fila)
            lineas.append(f"  A{indice + 1}: {valores}")
        return "\n".join(lineas)

    @classmethod
    def _format_assignments(cls, result: AssignmentResult) -> str:
        """Convierte las asignaciones reales en texto para el prompt."""
        if not result.real_assignments:
            return "  (sin asignaciones reales)"
        lineas = []
        for agente, tarea, valor in result.real_assignments:
            lineas.append(f"  {agente} -> {tarea}: {cls._format_number(valor)}")
        return "\n".join(lineas)
