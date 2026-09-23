# Social Debt API Model

API robusta y escalable diseñada para detectar, clasificar y medir la **Deuda Social** en repositorios de software a través de comentarios y discusiones. Utiliza técnicas avanzadas de Procesamiento de Lenguaje Natural (NLP), LLMs (OpenAI GPT-4o-mini) y emparejamiento semántico local (Sentence-Transformers).

## 🧠 Arquitectura y Funcionamiento

El modelo opera en un pipeline de múltiples etapas para procesar el texto:

1. **Limpieza de Ruido Operacional:** Utiliza heurísticas y expresiones regulares para limpiar bloques de código, URLs, menciones y firmas, aislando el texto puramente conversacional.
2. **Filtro de Ruido (Clasificación Causa H):** Determina si un comentario es ruido/conversación normal ("Causa H") o si contiene indicios de Deuda Social. Se apoya fuertemente en el LLM configurado con un prompt experto.
3. **Identificación de Macrocausas y Microcausas:** El texto que contiene Deuda Social se clasifica en una de las 7 Macrocausas principales (A-G). Posteriormente, utilizando un modelo NLP local (`all-MiniLM-L6-v2`), busca en un espacio vectorial las Microcausas más afines a nivel semántico.
4. **Integración Semántica:** Combina y enlaza las Microcausas con sus respectivos _Community Smells_, Riesgos, Estrategias Correctivas, Estrategias Preventivas, Indicadores y Métricas asociadas según una extensa Ontología precargada.
5. **Cálculo del Índice de Deuda Social (SDI):** Agrupa los resultados por Issue y calcula métricas de frecuencia, diversidad de causas, y un puntaje numérico unificado que representa el nivel de Deuda Social (Bajo, Medio, Alto) del Issue.

## 🚀 Despliegue y Requisitos

### Requisitos del Sistema
- Python 3.10+
- **2GB de RAM Mínimo** (Estrictamente necesario para montar el modelo PyTorch Sentence-Transformers local en memoria).
- Entorno de producción sugerido: Docker / VPS / Coolify.

### Variables de Entorno (`.env`)
Debes crear un archivo `.env` en la raíz del proyecto (basado en `.env.example`):
```env
OPENAI_API_KEY=sk-...
API_SECRET_KEY=tu_contraseña_secreta_aqui
```
> **Nota de Seguridad:** El `API_SECRET_KEY` actúa como autenticación maestra para todos los endpoints.

### Ejecución Local
1. Crea un entorno virtual e instala dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Inicia el servidor:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 📖 Documentación de la API (Endpoints)

> **⚠️ Importante:** Todos los endpoints requieren el header `X-API-Key`.

### 1. Validar Límites de OpenAI
`GET /system/openai-limits`
Realiza un ping a OpenAI para revisar la cuota disponible. Ideal antes de enviar lotes grandes para prevenir errores HTTP 429.

**Respuesta Exitosa:**
```json
{
  "status": "success",
  "limits": {
    "remaining_requests": "9999",
    "reset_requests": "14m30s"
  }
}
```

### 2. Clasificación Síncrona (Individual)
`POST /classify/text`
Analiza un único comentario y retorna el resultado en tiempo real.

**Request Body:**
```json
{
  "text": "This PR breaks the compilation on Windows machines because of the path separator."
}
```

**Respuesta Exitosa:**
```json
{
  "cleaned_text": "This PR breaks the compilation on Windows machines because of the path separator.",
  "is_noise": false,
  "noise_level": "none",
  "macro_cause_code": "C",
  "confidence": 0.85,
  "microcauses": [
    {
      "ontology_id": "COG-008_CompatibilityConstraints",
      "cause_type": "CongruenceCause",
      "cause_name": "Compatibility Constraints",
      "similarity": 0.65
    }
  ]
}
```

### 3. Procesamiento Asíncrono por Lotes (Batch)
`POST /classify/batch`
Sube un archivo `.csv` (Multipart) con miles de comentarios. El procesamiento se encola en segundo plano utilizando workers concurrentes que respetan automáticamente los límites de tasa dinámica (Rate Limits) de OpenAI.

**Form Data:**
- `file`: Archivo CSV. Debe contener mínimo la columna `body` (o `comment`). Opcionalmente `issue_number`, `comment_id`, `author`.

**Respuesta:**
```json
{
  "message": "Archivo aceptado. Procesamiento en segundo plano iniciado.",
  "job_id": "uuid-del-trabajo"
}
```

### 4. Consultar Estado de Trabajo Batch (Polling)
`GET /classify/batch/{job_id}`
Retorna el progreso actual o el resultado final del análisis de lote.

**Respuesta (Procesando):**
```json
{
  "status": "processing",
  "progress": "25 de 100 comentarios procesados (25%)"
}
```

**Respuesta (Completado):**
Cuando termina, retorna el análisis comentario por comentario, y si se proveyó el `issue_number`, también retorna el objeto `issues_metrics` con el SDI y las frecuencias dominantes calculadas por cada issue.
```json
{
  "status": "completed",
  "progress": "100 de 100 comentarios procesados (100%)",
  "result": {
    "comments": [ ... ],
    "issues_metrics": {
      "136207": {
        "social_debt_index": 0.645833,
        "social_debt_level": "Medium Social Debt",
        "dominant_community_smells": [
           ["['Missing Link']", 17],
           ["['Organizational Silo']", 5]
        ]
      }
    }
  }
}
```
> **Nota de Arquitectura Frontend:** La API *no* genera archivos `.xlsx` ni exportaciones binarias. El sistema espera que el frontend consuma este JSON maestro y construya localmente las tablas o dashboards necesarios, optimizando los costos computacionales y el ancho de banda del servidor.

### 5. Cancelar un Trabajo Batch
`POST /classify/batch/cancel`
Detiene instantáneamente un procesamiento en segundo plano.

**Request Body:**
```json
{
  "job_id": "uuid-del-trabajo"
}
```

---

## 📂 Estructura del Repositorio

El repositorio está organizado bajo los principios de **Clean Architecture**:

- `app/api/`: Definición de Rutas de FastAPI.
- `app/use_cases/`: Lógica de negocio (Pipeline de NLP, Clasificadores, Cálculo de SDI).
- `app/infrastructure/`: Servicios externos (Cliente de OpenAI, Cliente Ontológico, Manejo de Jobs en memoria).
- `app/domain/`: Modelos de datos de Pydantic.
- `data/samples/`: Datasets CSV de prueba y archivos de ejemplo.
- `scripts/`: Herramientas CLI para pruebas locales, auditorías, carga masiva interactiva y benchmarks de recursos.
- `reports/`: Histórico de auditorías técnicas (Ej. Varianza de modelos estocásticos).
- `Modelo_adaptativo_deuda_social_julio/`: Material base fundacional, proporcionado por el cliente, sobre el cual se basó la API.
