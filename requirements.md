# Proyecto Fase II: Optimización de Asignación de Recursos mediante el Método Húngaro con Soporte Dinámico y Análisis de IA

## Descripción General
Continuando con la modernización del sistema de distribución logística para la empresa "Rutas y Suministros C.A.", la directiva ahora enfrenta un problema de asignación. Se ha adquirido una nueva flota de vehículos especializados y se necesita asignar a los conductores de manera óptima para cubrir las rutas express. 

El objetivo de esta segunda fase es desarrollar un módulo que asigne exactamente un agente (conductor) a una tarea (ruta/vehículo) garantizando la máxima eficiencia o el menor costo, ampliando las capacidades técnicas del software desarrollado en la fase anterior.

Como parte del equipo de ingeniería de software, debes desarrollar este nuevo sistema incorporando el Método Húngaro, pero añadiendo nuevas funcionalidades de ingesta de datos, manejo de casos especiales (desbalance y maximización) y una integración más profunda con Inteligencia Artificial.

---

## Módulo A: Motor Algorítmico Avanzado (Desde Cero) 
Debe programar la lógica del Método Húngaro **sin utilizar librerías de optimización preexistentes** para la resolución matemática. Todo el manejo de matrices y cruce de líneas debe ser implementado con estructuras de datos nativas.

*   **Nueva Funcionalidad - Auto-Balanceo:** A diferencia del sistema anterior, este módulo debe detectar automáticamente si la matriz de entrada no es cuadrada (Agentes ≠ Tareas) y agregar filas o columnas ficticias con penalizaciones/costos igual a cero para balancear el problema antes de resolverlo.
*   **Nueva Funcionalidad - Flexibilidad de Objetivo (Min/Max):** El sistema debe permitir al usuario seleccionar mediante un comando o menú si el problema introducido es de Minimización (ej. tiempos de entrega, costos operativos) o de Maximización (ej. calificación de desempeño, ganancias). Si es maximización, el algoritmo debe transformar la matriz correctamente antes de aplicar los pasos estándar del Método Húngaro.

---

## Módulo B: Ingesta de Datos Dinámica (Nueva Funcionalidad) 
Para hacer el sistema más robusto para un entorno de producción, ya no se dependerá exclusivamente de datos cargados en el código.

*   El sistema debe permitir la carga dinámica de la matriz de costos/beneficios a través de la lectura de un archivo externo (por ejemplo, `.csv` o `.json`).
*   Debe seguir incluyendo una matriz por defecto cargada en memoria como prueba de contingencia en caso de que el archivo externo falle o el usuario decida omitir la carga.

---

## Módulo C: Representación en Grafo Bipartito 
Una vez obtenida la asignación óptima, el sistema debe generar una representación visual del resultado.

*   **Nodos:** Agentes (Columna Izquierda) y Tareas (Columna Derecha).
*   **Aristas:** Deben conectar únicamente las asignaciones finales óptimas (relación 1 a 1).
*   **Nueva Funcionalidad Visual:** Si el problema original era desbalanceado, las aristas que conecten a un nodo ficticio (recurso inactivo o tarea no cubierta) deben graficarse en un color diferente (ej. rojo o línea punteada) para alertar visualmente a la gerencia.
*   *Nota:* Está permitido el uso de librerías de graficación como NetworkX y Matplotlib.

---

## Módulo D: Integración con API de IA - Agente de Recursos Humanos 
El sistema debe conectarse mediante peticiones REST a una API de Inteligencia Artificial (Gemini, OpenAI o Claude).

*   **El Prompt:** El código debe construir dinámicamente un prompt enviando: la matriz original, el objetivo (Min/Max), la matriz de asignación final y las tareas/agentes que quedaron inactivos (si hubo variables ficticias).
*   **El Objetivo:** La IA asumirá el rol de "Gerente de Operaciones y Recursos Humanos". Debe devolver un análisis ejecutivo (máximo 2 párrafos) evaluando el impacto de la asignación.
*   **Nueva Funcionalidad Analítica:** Se le debe exigir a la IA que proponga una recomendación de negocio específica sobre qué hacer con los recursos inactivos o tareas huérfanas (los asignados a nodos ficticios), dándole un valor agregado a la salida del software.
*   La respuesta debe imprimirse en la pantalla final de resultados.

---

## Entregables Esperados y Pautas de Evaluación 

3.  **Interfaz:** Usar interfaz gráfica.
4.  **Pautas Clave:**
    *   Usar paradigma de **programación orientada a objetos**.
    *   Realizar validaciones de datos introducidos por el usuario (manejo de excepciones al leer los archivos `.csv`/`.json` y en las opciones de menú).
    *   Se evaluará la legibilidad del código (nombres de variables coherentes, código comentado) y el funcionamiento libre de errores.
   