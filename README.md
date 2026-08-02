# Social Debt API Model

API web diseñada para identificar y clasificar "Deuda Social" (Social Debt) en comunicaciones de ingeniería de software (ej. comentarios de GitHub), utilizando Procesamiento de Lenguaje Natural (NLP), Modelos de Lenguaje Grandes (LLM), y Emparejamiento Semántico. 

El modelo matemático detrás de esta API ha sido extraído y replicado exactamente a partir de los cuadernos de investigación (Jupyter Notebooks) originales del cliente, logrando una **similitud matemática del 99.2%**.

---

## 🏗 Arquitectura Híbrida

Para garantizar el mejor rendimiento, los menores costos y un determinismo preciso, la API utiliza una arquitectura híbrida probada:

1. **Limpieza de Ruido (RegEx):** Se detectan bots, tickets automáticos y ruido operativo usando las expresiones regulares exactas de la investigación original.
2. **Razonamiento Complejo (OpenAI LLM):** El modelo `gpt-4o-mini` de OpenAI se utiliza **única y exclusivamente** para analizar el contexto del texto limpio y clasificarlo en una de las 8 Macrocausas (Letras A a H).
3. **Emparejamiento Semántico Local (Sentence-Transformers):** En lugar de hacer costosas peticiones web para buscar causas específicas, la API cuenta con el modelo NLP local `paraphrase-multilingual-MiniLM-L12-v2` descargado en el servidor. Este modelo convierte el texto a vectores y busca las 5 Microcausas (ej. COG-009) más cercanas matemáticamente en tiempo récord.
4. **Índice de Deuda Social (SDI):** Un módulo matemático propio agrupa los comentarios y calcula métricas normalizadas de diversidad y puntajes de SDI agrupados por Issue (`MinMaxScaler`).

---

## 🚀 Endpoints Principales

* `GET /system/openai-limits`: Realiza un "ping" a la red de OpenAI y extrae de los encabezados (Headers) la cuota exacta de **Peticiones (Requests)** y **Tokens** disponibles en tiempo real. **Crucial antes de enviar lotes masivos para evitar errores 429.**
* `POST /classify/text`: Clasifica de manera síncrona un (1) solo comentario de texto crudo, arrojando macrocausas y microcausas.
* `POST /classify/batch`: Sube un archivo CSV de miles de comentarios. Los procesa de forma asíncrona en lotes de alta concurrencia respetando un Límite de Tokens dinámico (`TokenRateLimiter`). Retorna un `job_id`.
* `GET /classify/batch/{job_id}`: Consulta en tiempo real (Polling) el porcentaje de progreso del procesamiento por lotes. Cuando termina, entrega los resultados granulares y el Índice de Deuda Social (SDI).

---

## 🛠 Scripts y Pruebas Incluidas

Dentro del directorio `scripts/` encontrarás valiosas herramientas para ejecutar pruebas y comparar varianzas:

* **`run_performance_test.py`** (Ubicado en la raíz): Script interactivo en consola para pruebas de carga masivas (*End-to-End*). Incluye un "Pre-flight check" automático que valida tus límites de OpenAI llamando a `/system/openai-limits` antes de permitir la subida del archivo. Soporta entornos locales o remotos (Coolify).
* **`scripts/verify_e2e_openai_variance.py`**: Una poderosa herramienta de auditoría forense. Al ejecutarla, pasa el archivo CSV local de 1,000 comentarios simultáneamente por el algoritmo original en crudo y por el algoritmo refactorizado, exportando una comparación exhaustiva en un archivo `reporte_varianza_exhaustivo.json`. (Demostró una precisión del 97.21% en coincidencias de OpenAI).
* **`scripts/test_single_comment.py`**: Para pruebas rápidas a un solo string de texto.

---

## 📊 Reportes

Los reportes de resultados masivos y el JSON de auditoría forense (`reporte_varianza_exhaustivo.json`) se guardan automáticamente en la carpeta `reports/` para ser analizados posteriormente.

---

## ⚙️ Requisitos y Despliegue

* Python 3.10+
* **2GB de RAM Mínimo** (Requerido para montar el modelo PyTorch NLP en memoria).
* Archivo `.env` con: `OPENAI_API_KEY=tu_api_key_aqui`
* Diseñado para despliegue ininterrumpido en entornos como **Coolify / VPS**.