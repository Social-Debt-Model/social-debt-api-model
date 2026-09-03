# Social Debt API Model

API web diseñada para identificar y clasificar "Deuda Social" (Social Debt) en comunicaciones de ingeniería de software (ej. comentarios de GitHub), utilizando Procesamiento de Lenguaje Natural (NLP), Modelos de Lenguaje Grandes (LLM), y Emparejamiento Semántico. 

El modelo matemático detrás de esta API ha sido extraído y replicado exactamente a partir de los cuadernos de investigación (Jupyter Notebooks) originales del cliente, logrando una **similitud matemática del 99.2%**.

---

## 🏗 Arquitectura Híbrida

Para garantizar el mejor rendimiento, los menores costos y un determinismo preciso, la API utiliza una arquitectura híbrida probada:

1. **Limpieza de Ruido (RegEx):** Se detectan bots, tickets automáticos y ruido operativo usando las expresiones regulares exactas de la investigación original.
2. **Razonamiento Complejo (OpenAI LLM):** El modelo `gpt-4o-mini` de OpenAI se utiliza **única y exclusivamente** para analizar el contexto del texto limpio y clasificarlo en una de las 8 Macrocausas (Letras A a H).
3. **Emparejamiento Semántico Local (Sentence-Transformers):** En lugar de hacer costosas peticiones web para buscar causas específicas, la API cuenta con el modelo NLP local `all-MiniLM-L6-v2` integrado. Este modelo convierte el texto a vectores y busca las 5 Microcausas más cercanas matemáticamente en tiempo récord basándose en una ontología predefinida.
4. **Índice de Deuda Social (SDI):** Un módulo matemático propio agrupa los comentarios y calcula métricas normalizadas de diversidad y puntajes de SDI agrupados por Issue.

---

## 🚀 Guía de Consumo para el Frontend

Esta sección detalla cómo integrar y consumir la API desde cualquier aplicación Frontend.

### Seguridad y Autenticación
Todos los endpoints están asegurados. Tu aplicación Frontend debe enviar obligatoriamente el Header HTTP `X-API-Key` en **todas** las peticiones.
```http
X-API-Key: <TU_API_SECRET_KEY>
```

### Optimización de Ancho de Banda (Diccionario Frontend)
Para reducir el tamaño de las respuestas JSON y ahorrar ancho de banda, la API **no devuelve los textos largos de las descripciones de ontología**. 
En su lugar, la API devuelve códigos cortos (Ej. Macrocausa `"A"`, Microcausa `"COG-011_SystemConfigurationConstraints"`).
El Frontend debe cargar el archivo estático ubicado en `data/frontend_ontology_dictionary.json` para mapear estos códigos a sus títulos descriptivos legibles por el usuario en la interfaz.

---

### Endpoints Principales

#### 1. Validar Límites de OpenAI
`GET /system/openai-limits`
Realiza un "ping" a la red de OpenAI y extrae la cuota exacta de peticiones disponibles. **Llamar siempre antes de enviar lotes masivos para evitar errores 429.**
- **Respuesta Exitosa:**
```json
{
  "status": "success",
  "limits": {
    "remaining_requests": "9999",
    "reset_requests": "14m30s"
  }
}
```

#### 2. Clasificación Síncrona (Un solo comentario)
`POST /classify/text`
- **Body:**
```json
{
  "text": "This PR breaks the compilation on Windows machines because of the path separator."
}
```
- **Respuesta:**
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

#### 3. Clasificación Asíncrona (Lotes Masivos)
`POST /classify/batch`
Sube un archivo `.csv` (Multipart/form-data). La API procesará los comentarios en segundo plano con alta concurrencia respetando los Rate Limits dinámicos.
- **Form Data:** Key `file` con el archivo CSV adjunto.
- **Respuesta:** Retorna casi instantáneamente un `job_id`.
```json
{
  "message": "Archivo aceptado. Procesamiento en segundo plano iniciado.",
  "job_id": "A1B2C3"
}
```

#### 4. Polling de Resultados Masivos
`GET /classify/batch/{job_id}`
El Frontend debe consultar este endpoint cada 2-3 segundos para actualizar la barra de progreso.
- **Estado `processing`:**
```json
{
  "status": "processing",
  "progress": "25 de 100 comentarios procesados (25%)"
}
```
- **Estado `completed`:**
Retorna el JSON completo con todos los comentarios analizados y las **Métricas SDI** por Issue (Solo si el CSV original incluía la columna `issue_number`).
```json
{
  "status": "completed",
  "progress": "100 de 100 comentarios procesados (100%)",
  "result": {
    "comments": [ ... ],
    "issues_metrics": {
      "135664": {
        "social_debt_index": 0.8542,
        "social_debt_level": "High Social Debt",
        "comment_count": 32,
        "macro_diversity": 5,
        "micro_diversity": 3,
        "dominant_macrocauses": [["C", 10], ["A", 5]],
        "dominant_microcause_types": [["CongruenceCause", 10], ["AdministrativeCause", 5]]
      }
    },
    "exports": {
      "step1_b64": "UEsDBBQAAAAIA...",
      "step2_b64": "UEsDBBQAAAAIA...",
      "step3_b64": "UEsDBBQAAAAIA...",
      "final_excel_b64": "UEsDBBQAAAAIA..."
    }
  }
}
```

> [!TIP]
> **Trazabilidad Autonóma (Frontend)**
> El nodo `exports` contiene los archivos **Excel (.xlsx)** codificados en Base64 de cada paso lógico del modelo (ideal para que un juez audite el proceso). Para descargarlos directamente desde el navegador sin hacer peticiones adicionales al servidor, puedes usar este fragmento de JavaScript:
> ```javascript
> function downloadBase64Excel(base64String, fileName) {
>   const byteCharacters = atob(base64String);
>   const byteNumbers = new Array(byteCharacters.length);
>   for (let i = 0; i < byteCharacters.length; i++) {
>     byteNumbers[i] = byteCharacters.charCodeAt(i);
>   }
>   const byteArray = new Uint8Array(byteNumbers);
>   const blob = new Blob([byteArray], {type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"});
>   
>   const link = document.createElement('a');
>   link.href = window.URL.createObjectURL(blob);
>   link.download = fileName;
>   link.click();
> }
> 
> // Ejemplo de uso:
> // downloadBase64Excel(response.result.exports.final_excel_b64, "Reporte_Final.xlsx");
> ```

#### 5. Cancelar un Trabajo (Batch Cancel)
`POST /classify/batch/cancel`
Si enviaste un lote gigantesco por error y quieres abortarlo para no agotar tu cuota de OpenAI, puedes cancelarlo.
- **Body:**
```json
{
  "job_id": "A1B2C3"
}
```
- **Respuesta Exitosa:**
```json
{
  "message": "Job cancelled successfully"
}
```
El trabajo cambiará su estado a `cancelled` y detendrá instantáneamente las llamadas a la API de OpenAI en segundo plano.

---

## 🛠 Scripts Locales de Prueba

Dentro del directorio `scripts/` encontrarás valiosas herramientas interactivas de consola:

* **`scripts/run_interactive_load_test.py`**: Script de pruebas de carga *End-to-End*. Permite seleccionar entre distintos tamaños de dataset (100, 1000, 2593 comentarios), elegir si golpear el servidor local o el VPS remoto, hace validaciones previas de límites de OpenAI, realiza el polling asíncrono y guarda el resultado automáticamente en un archivo `resultado_api_X.json` en la misma carpeta.
* **`scripts/audit_openai_variance.py`**: Herramienta de auditoría forense que compara los resultados de esta API directamente contra la versión en crudo del código fuente original del cliente para garantizar la paridad matemática.
* **`scripts/debug_single_comment.py`**: Script ultra rápido para probar el ciclo de vida síncrono de un único comentario de texto por consola.
* **`scripts/run_metrics_benchmark.py`**: Valida exclusivamente la estabilidad del servidor midiendo consumo de RAM y CPU durante simulaciones de carga.

---

## ⚙️ Requisitos y Despliegue

* Python 3.10+
* **2GB de RAM Mínimo** en el servidor (Requerido para montar el modelo PyTorch local en memoria).
* Archivo `.env` en la raíz con: 
  - `OPENAI_API_KEY=sk-...`
  - `API_SECRET_KEY=tu_contraseña_secreta_aqui`
* Diseñado y optimizado para despliegue ininterrumpido en entornos como **Coolify / VPS / Docker**.