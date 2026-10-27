# Social Debt API Model

API desarrollada con FastAPI para la detección, clasificación y medición del **Índice de Deuda Social (SDI)** en discusiones y comentarios de repositorios de software. Implementa una arquitectura híbrida que combina preprocesamiento determinista, razonamiento con modelos de lenguaje (OpenAI GPT-4o-mini), similitud semántica vectorial local (Sentence-Transformers) e inferencia sobre ontologías sociotécnicas (RDF/OWL).

---

## 1. Pipeline de Procesamiento

El flujo de inferencia opera en cinco etapas secuenciales:

1. **Preprocesamiento y Normalización de Texto:**  
   Aislamiento de la evidencia conversacional mediante la remoción de ruido operacional (bloques de código, URLs, referencias de commit/hashes, menciones y metadatos de GitHub).
2. **Detección y Filtrado de Ruido (Macrocausa H):**  
   Diferenciación entre interacción puramente social/ruido operacional (Causa H) y discusiones con implicación sociotécnica.
3. **Clasificación de Macrocausas (A–G) y Microcausas:**  
   - **Macrocausas:** Inferencia con OpenAI (GPT-4o-mini) y ajuste mediante reglas de prioridad basadas en evidencia léxica.
   - **Microcausas:** Búsqueda y ponderación semántica en espacio vectorial mediante el modelo local `paraphrase-multilingual-MiniLM-L12-v2`, vinculando las microcausas más afines del catálogo.
4. **Enriquecimiento Ontológico:**  
   Carga del grafo OWL/RDF (`ontologyv4.rdf`) para asociar cada microcausa identificada con sus respectivos *Community Smells*, factores de riesgo, estrategias preventivas, estrategias correctivas, indicadores y métricas asociadas.
5. **Cálculo del Índice de Deuda Social (SDI):**  
   Agrupación analítica por Issue, evaluación de la entropía/diversidad de causas (Shannon), normalización mediante `MinMaxScaler` y asignación de nivel de riesgo (Bajo, Medio, Alto).

---

## 2. Requisitos y Configuración

### Requisitos del Sistema
- **Python:** 3.11 o superior.
- **Memoria RAM:** 2 GB mínimo recomendado (para mantener el modelo local de Sentence-Transformers y el grafo ontológico en memoria).
- **Entorno de ejecución:** Docker, Nixpacks o servidor VPS/Cloud.

### Variables de Entorno (`.env`)
Copie la plantilla de variables de entorno y configure los secretos correspondientes:
```bash
cp .env.example .env
```

Estructura de variables en `.env`:
```dotenv
PROJECT_NAME="Social Debt API Model"
API_V1_STR="/api/v1"

# Seguridad (Cabecera obligatoria: X-API-Key)
API_SECRET_KEY="super_secret_social_debt_key"

# Proveedor LLM
OPENAI_API_KEY="sk-proj-..."

# Parámetros de despliegue PaaS (Coolify / Railway / Nixpacks)
PYTHON_VERSION=3.11
NIXPACKS_NODE_VERSION=22
```

---

## 3. Instalación y Ejecución Local

### Opción A: Entorno Virtual Python
```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Opción B: Contenedor Docker
```bash
docker build -t social-debt-api .
docker run -d -p 8000:8000 --env-file .env social-debt-api
```

---

## 4. Endpoints Principales (API REST)

Todos los endpoints bajo `/api/v1` requieren la cabecera de autenticación `X-API-Key`.

### 1. Inferencia Individual
- **Método:** `POST /api/v1/classify/text`
- **Descripción:** Procesa un único comentario en tiempo real.
- **Cuerpo (JSON):**
  ```json
  {
    "text": "This PR breaks compatibility on Windows due to the path separator."
  }
  ```

### 2. Procesamiento Asíncrono por Lotes (Batch)
- **Método:** `POST /api/v1/classify/batch`
- **Descripción:** Recibe un archivo tabular (CSV o XLSX) vía `multipart/form-data` e inicia el procesamiento en segundo plano con control de cuota y limitador de tokens.
- **Form-Data:**
  - `file`: Archivo tabular con comentarios (columnas mínimas: `comment` o `body`, y opcionalmente `issue_number`, `comment_id`, `author`).
  - `instructions` (opcional): Configuración en JSON de mapeo de columnas y manejo de comentarios huérfanos.

### 3. Sondeo de Estado y Resultados
- **Método:** `GET /api/v1/classify/batch/{job_id}`
- **Descripción:** Consulta el porcentaje de avance, tiempo estimado de finalización y resultados estructurados con métricas por issue (SDI).

### 4. Cancelación de Tarea por Lotes
- **Método:** `POST /api/v1/classify/batch/cancel`
- **Descripción:** Cancela limpiamente la ejecución de un trabajo activo.

### 5. Monitoreo de Cuotas y Límites LLM
- **Método:** `GET /api/v1/system/openai-limits`
- **Descripción:** Diagnostica las cabeceras de límite de tasa (RPM / TPM) de OpenAI en tiempo real.

---

## 5. Scripts de Utilidad y Benchmarking

En el directorio `scripts/` se proporcionan utilidades CLI independientes para mantenimiento, pruebas y validaciones técnicas:

- `python scripts/generate_frontend_dictionary.py`: Parsea el archivo `ontologyv4.rdf` y genera el diccionario JSON estructurado en `data/frontend_ontology_dictionary.json`.
- `python scripts/check_openai_limits.py`: Diagnostica la cuota y límites de peticiones (RPM/TPM) de la API key de OpenAI.
- `python scripts/debug_single_comment.py`: Evalúa el pipeline de inferencia completo para un comentario unitario desde la terminal.
- `python scripts/run_metrics_benchmark.py`: Ejecuta una prueba de agrupación de issues y cálculo del SDI con telemetría de CPU y memoria.
- `python scripts/run_interactive_load_test.py`: Prueba interactiva de carga masiva con sondeo de progreso y estimaciones de tiempo.
- `python scripts/audit_openai_variance.py`: Auditoría de varianza y consistencia estocástica en clasificación sobre 1.000 comentarios.
- `python scripts/auditoria_completa.py`: Comparativa de paridad técnica por etapas frente a los cuadernos de investigación.

---

## 6. Estructura del Repositorio

El proyecto implementa una arquitectura orientada al dominio y Clean Architecture:

```text
social-debt-api-model/
├── app/
│   ├── api/                    # Endpoints FastAPI y ciclo de tareas en segundo plano
│   │   └── routes.py
│   ├── core/                   # Configuración y variables de entorno (Pydantic Settings)
│   │   └── config.py
│   ├── domain/                 # Esquemas Pydantic y modelos de transferencia
│   │   └── schemas.py
│   ├── infrastructure/         # Clientes de servicios externos y persistencia
│   │   ├── llm_client.py       # Cliente OpenAI con TokenRateLimiter
│   │   ├── ontology_client.py  # Parser y enriquecedor de ontología RDF
│   │   └── ontologyv4.rdf      # Ontología de deuda social
│   ├── use_cases/              # Lógica de negocio y etapas del pipeline
│   │   ├── classification/     # Inferencia LLM y reglas de prioridad
│   │   ├── metrics/            # Cálculo del Índice de Deuda Social (SDI)
│   │   ├── preprocessing/      # Limpieza y filtrado determinista de ruido
│   │   └── semantic/           # Similitud semántica de microcausas (Top-K)
│   └── main.py                 # Inicialización de la aplicación FastAPI y middlewares
├── data/
│   ├── frontend_ontology_dictionary.json  # Diccionario ontológico estructurado
│   └── samples/                # Datasets de prueba para clientes y testing (CSV/XLSX)
├── docs/
│   ├── audit/                  # Reporte técnico y datos de paridad (notebook vs API)
│   └── research/
│       └── baseline_notebooks/ # Cuadernos y datasets originales de experimentación
├── scripts/                    # Scripts CLI de benchmarking, pruebas y auditoría
├── Dockerfile                  # Empaquetado de producción con PyTorch CPU optimizado
├── requirements.txt            # Dependencias fijadas del entorno de producción
├── .env.example                # Plantilla documentada de variables de entorno
└── README.md                   # Documentación general del proyecto
```
