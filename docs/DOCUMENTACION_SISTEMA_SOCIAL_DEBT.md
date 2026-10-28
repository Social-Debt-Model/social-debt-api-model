# DOCUMENTACIÓN TÉCNICA Y ARQUITECTURA DE SOFTWARE DEL SISTEMA DE IDENTIFICACIÓN Y CUANTIFICACIÓN DE DEUDA SOCIAL (SOCIAL DEBT MODEL)

---

## 1. ARQUITECTURA GENERAL DEL SISTEMA Y TOPOLOGÍA DE DESPLIEGUE

### 1.1. Visión Holística del Ecosistema Desacoplado
El sistema **Social Debt Model** está estructurado bajo una **arquitectura desacoplada en tres capas** (Cliente / Servidor / Servicios de Inteligencia Artificial), orientada a optimizar el rendimiento, garantizar la reproducibilidad científica y desacoplar la capa de visualización interactiva del motor de cómputo intensivo.

```
+-----------------------------------------------------------------------------------+
|                            CAPA DE PRESENTACIÓN (CLIENTE)                         |
|  - Entorno: Vercel Edge Serverless Network (Next.js 16.3.2 / React 19.2.8)        |
|  - Interfaz reactiva: Validación de datos, previsualización, dashboards analíticos |
|  - Persistencia de sesión: IndexedDB local (idb-keyval)                           |
+-----------------------------------------------------------------------------------+
                                      │  ▲
             Server Actions (BFF)     │  │  Polling asíncrono / JSON Payload
        (X-API-Key seguro, HTTPS)     ▼  │  (Resultados y métricas agregadas)
+-----------------------------------------------------------------------------------+
|                        CAPA DE CÓMPUTO Y MODELADO (BACKEND)                       |
|  - Entorno: Contabo Cloud VPS 4 (4 vCPU, 8 GB RAM, 100 GB NVMe, Linux x86_64)     |
|  - Orquestador: Coolify (Docker Containerizado, Caddy/Nginx SSL Reverso)         |
|  - Framework: FastAPI 0.111.0 / Uvicorn ASGI en Python 3.11                       |
|  - Motores: SentenceTransformers MiniLM, RDFLib Ontología, Scikit-learn SDI       |
+-----------------------------------------------------------------------------------+
                                      │  ▲
              Llamadas asíncronas     │  │  Inferencia estructurada (JSON)
            (Control de concurrencia) ▼  │  (Telemetría de cuota y rate-limits)
+-----------------------------------------------------------------------------------+
|                         SERVICIOS EXTERNOS DE INFERENCIA                          |
|  - Proveedor: OpenAI API (Modelo gpt-4o-mini con temperatura determinista)        |
+-----------------------------------------------------------------------------------+
```

#### Flujo de Comunicación y Patrón BFF (Backend-for-Frontend)
1. **Navegador del Usuario**: Interactúa con la interfaz gráfica construida en Next.js. El usuario carga archivos de comentarios (CSV o XLSX) o somete textos individuales.
2. **Proxy Seguro (Next.js Server Actions)**: Las peticiones no exponen la clave de autenticación del backend (`API_SECRET_KEY`) en el navegador. En su lugar, se ejecutan Server Actions en el runtime perimetral de Vercel que inyectan de forma segura la cabecera HTTP `X-API-Key` y canalizan el tráfico hacia la API REST del backend.
3. **Motor de Cómputo (FastAPI en Coolify)**: Recibe el dataset, valida los límites de cuota vigentes de OpenAI y delega la ejecución a un proceso en segundo plano (`BackgroundTasks`) protegido por un semáforo de concurrencia (`asyncio.Lock`).
4. **Almacenamiento Desacoplado**: El backend persiste el estado de procesamiento en disco en formato JSON (`app/jobs/{job_id}.json`), permitiendo que el cliente consulte periódicamente (*polling*) el progreso sin mantener conexiones de socket abiertas que saturen el servidor. Una vez finalizado el cálculo, los resultados se transmiten al cliente y se almacenan en el navegador mediante **IndexedDB**, garantizando que el servidor permanezca sin estado (*stateless*).

---

### 1.2. Infraestructura y Entornos de Ejecución

#### A. Entorno de Presentación (Frontend en Vercel)
* **Plataforma:** Vercel Edge Serverless Platform.
* **Mecanismo de Despliegue:** Integración continua y entrega continua (CI/CD) vinculada al repositorio GitHub (`social-debt-frontend-model`), con construcción automática ante cambios en ramas de producción y despliegues preliminares (*preview environments*).
* **Distribución:** Red de entrega de contenido (CDN) perimetral distribuida globalmente, con caché inmutable para activos estáticos (CSS, chunks compilados de JavaScript y fuentes tipográficas).
* **Aislamiento de Secretos:** Configuración de variables de entorno protegidas (`NEXT_PUBLIC_API_URL`, `API_SECRET_KEY`), garantizando que las credenciales criptográficas nunca se compilen en los paquetes cliente.

#### B. Entorno de Servidor y Cómputo (Backend en Coolify sobre VPS Contabo)
El motor de cómputo y modelado se ejecuta en una infraestructura dedicada de alto rendimiento, cuyas especificaciones físicas y lógicas se detallan a continuación:

* **Proveedor de Infraestructura:** Contabo GmbH.
* **Modelo / Plan de Servidor:** Contabo Cloud VPS 4 (Generación 2026).
* **Capacidad de Cómputo (CPU):** 4 núcleos virtuales (vCPU) dedicados basados en arquitectura x86_64.
* **Memoria de Acceso Aleatorio (RAM):** 8.00 GB de memoria física asignada.
* **Almacenamiento Secundario:** 100 GB de disco en estado sólido NVMe (Non-Volatile Memory Express), asegurando tasas de lectura/escritura superiores a 2,000 MB/s para la serialización de modelos y caché de embeddings.
* **Sistema Operativo Anfitrión:** Linux (Debian/Ubuntu 64-bit con kernel optimizado para virtualización KVM).
* **Conectividad de Red:** Dirección IPv4 pública fija (`169.58.105.173`), interfaz IPv6 (`2a02:c207:2347:8342::1/64`) ubicada físicamente en el centro de datos de la Unión Europea (Región EU).
* **Plataforma de Orquestación:** **Coolify** (PaaS autoalojada y de código abierto para orquestación de contenedores Docker).
* **Gestión de Red y Proxy Inverso:** Enrutador Caddy/Nginx gestionado automáticamente por Coolify, responsable de la terminación segura de certificados SSL/TLS (Let's Encrypt con renovación autónoma), compresión gzip/brotli y redirección obligatoria de tráfico HTTP a HTTPS.
* **Contenerización Docker:**
  * **Imagen Base:** `python:3.11-slim`.
  * **Optimización de Capas:** Aislamiento de capas de dependencias para acelerar el despliegue.
  * **Instalación Optimizada de PyTorch:** Se utiliza la compilación explícita para CPU (`--index-url https://download.pytorch.org/whl/cpu`), reduciendo el tamaño de la imagen Docker de ~7.2 GB (con controladores CUDA/NVIDIA innecesarios en VPS) a solo ~1.4 GB, lo que minimiza el consumo de memoria RAM y el tiempo de arranque.
  * **Exposición y Control:** El contenedor expone internamente el puerto TCP 8000 hacia la red interna de Docker creada por Coolify, sin exponer puertos de base de datos o APIs sin cifrar al internet público.

---

## 2. PILA TECNOLÓGICA Y JUSTIFICACIÓN METODOLÓGICA

### 2.1. Tecnologías de la Interfaz y Lógica Cliente (Frontend)

* **Next.js 16.3.2 (con React 19.2.8 & React Compiler):**
  * *Justificación:* Proporciona un entorno híbrido con Server Actions para actuar como proxy seguro entre el navegador y el backend. La inclusión del React Compiler (`babel-plugin-react-compiler`) optimiza automáticamente la reactividad del árbol de componentes sin necesidad de sobrecargar el código con hooks manuales de memorización (`useMemo`, `useCallback`).
* **TypeScript 5.x:**
  * *Justificación:* Ofrece tipado estático estricto para los contratos de datos analíticos (`BatchResultData`, `MetricsData`, `ClassifyTextResponse`), evitando errores de inconsistencia en tiempo de ejecución al manipular grandes volúmenes de comentarios estructurados.
* **Tailwind CSS v4:**
  * *Justificación:* Motor de utilidades CSS moderno de última generación compilado a través de `@tailwindcss/postcss`, permitiendo un diseño responsivo con temática de paneles vidriados (*glassmorphism*) y aceleración de hardware para transiciones visuales.
* **Ecosistema de Visualización Analítica:**
  * **@nivo/core & @nivo/heatmap (v0.99.0):** Implementación de mapas de calor para analizar la densidad de correlación entre categorías sociotécnicas, dimensiones ontológicas y gravedad de incidencias.
  * **recharts (v3.10.1):** Generación reactiva de diagramas de radar, barras categóricas y series de distribución acumulada del Índice de Deuda Social (SDI).
* **Gestión de Persistencia en Cliente:**
  * **idb-keyval (v6.3.0):** Envoltura asíncrona de alto rendimiento para **IndexedDB**. Permite persistir colecciones completas de análisis de miles de registros (superando el límite restrictivo de 5 MB de `localStorage`) directamente en el navegador del usuario, garantizando privacidad de datos y navegación sin conexión por lotes históricos.
* **Procesamiento y Exportación Tabular:**
  * **papaparse (v5.6.0):** Analizador sintáctico de archivos CSV en el cliente con detección automática de delimitadores (comas, punto y coma) y streaming de datos.
  * **xlsx (v0.18.5) & exceljs (v4.4.0) & file-saver (v2.0.5):** Generación de libros de cálculo multi-pestaña enriquecidos con formato visual, encabezados bloqueados, trazabilidad de heurísticas aplicadas y fórmulas precalculadas.

---

### 2.2. Tecnologías del Motor Analítico de Backend (API Engine)

* **Python 3.11:**
  * *Justificación:* Lenguaje estándar en computación científica y procesamiento de lenguaje natural (PLN), combinando una sintaxis clara con mejoras de velocidad de hasta un 25% respecto a versiones anteriores.
* **FastAPI 0.111.0 & Uvicorn 0.30.1:**
  * *Justificación:* Framework web de alto rendimiento basado en los estándares OpenAPI y JSON Schema. Su arquitectura asíncrona nativa sobre ASGI (`asyncio`) permite despachar cientos de consultas concurrentes a modelos de lenguaje sin bloquear el bucle de eventos del servidor.
* **Pydantic 2.7.4 & Pydantic-Settings 2.3.4:**
  * *Justificación:* Validación estricta y coercitiva de tipos basada en el motor compilado en Rust (`pydantic-core`), proporcionando validaciones hasta 20 veces más rápidas al serializar peticiones y respuestas complejas de inferencia.
* **SentenceTransformers 3.0.1 (Modelo `paraphrase-multilingual-MiniLM-L12-v2`):**
  * *Justificación:* Red neuronal siamesa multilingüe basada en arquitectura Transformer, optimizada para proyectar textos y conceptos ontológicos en un espacio vectorial denso de 384 dimensiones. Permite calcular similitudes semánticas en español e inglés sin requerir traducción previa.
* **PyTorch (Versión CPU):**
  * *Justificación:* Plataforma de tensores matemáticos utilizada para operar las matrices de embeddings y calcular la similitud coseno mediante precisión de doble coma flotante (`torch.float64`), asegurando estabilidad numérica determinista.
* **RDFLib 7.0.0:**
  * *Justificación:* Motor de grafos de conocimiento semántico conforme a las especificaciones W3C (RDF/OWL). Parsea de forma nativa la ontología formal (`ontologyv4.rdf`) bajo el espacio de nombres `http://www.example.org/ontosocialdebt#`, permitiendo recorrer relaciones complejas entre causas, efectos, estrategias de mitigación, riesgos e indicadores métricos.
* **Scikit-Learn 1.5.0:**
  * *Justificación:* Provee transformaciones estadísticas robustas, específicamente `MinMaxScaler`, para normalizar el espacio multidimensional de métricas de deuda social en el intervalo estándar $[0, 1]$.
* **Pandas 2.2.2 & OpenPyXL 3.1.2:**
  * *Justificación:* Motor de estructuras tabulares para manipulación matricial de datos vectorizados, agregación por agrupamientos (`groupby`) de incidencias y generación de resúmenes estadísticos.
* **OpenAI SDK (>= 1.40.0) & Tiktoken (>= 0.7.0):**
  * *Justificación:* Cliente asíncrono oficial para comunicación con la API de OpenAI (`gpt-4o-mini`). Utiliza `tiktoken` para la presupuestación exacta de tokens y captura en tiempo real las cabeceras HTTP `x-ratelimit-remaining-requests` y `x-ratelimit-reset-requests` para evitar denegaciones de servicio por cuota.

---

### 2.3. Matriz Consolidada de Tecnologías y Versiones

| Componente | Categoría | Versión | Entorno | Rol Metodológico en el Sistema |
| :--- | :--- | :--- | :--- | :--- |
| **Next.js** | Framework Frontend | 16.3.2 | Vercel Edge | Arquitectura SPA/SSR, renderizado reactivo y Server Actions BFF. |
| **React** | Biblioteca UI | 19.2.8 | Cliente | Construcción declarativa de la interfaz basada en componentes. |
| **React Compiler** | Optimización | 1.0.0 | Build | Memorización automática de componentes y reducción de re-renders. |
| **TypeScript** | Lenguaje | 5.x | Build | Tipado estático y garantía de contratos de esquemas analíticos. |
| **Tailwind CSS** | Motor de Estilos | 4.0.0 | Cliente | Diseño responsivo, paleta cromática sobria y glassmorphism. |
| **Nivo Heatmap** | Visualización | 0.99.0 | Cliente | Representación matricial de correlaciones ontológicas. |
| **Recharts** | Visualización | 3.10.1 | Cliente | Gráficos de barras, dispersión y perfiles radiales de SDI. |
| **idb-keyval** | Base de Datos Cliente | 6.3.0 | IndexedDB | Almacenamiento local persistente de lotes procesados e historial. |
| **ExcelJS / XLSX** | Exportación | 4.4.0 / 0.18.5 | Cliente | Generación de cuadernos de cálculo de auditoría multi-hoja. |
| **Python** | Runtime Backend | 3.11 | Contenedor | Entorno de cómputo para algoritmos de IA y análisis cuantitativo. |
| **FastAPI** | Framework API | 0.111.0 | Uvicorn ASGI | API REST asíncrona de alto rendimiento con validación OpenAPI. |
| **Pydantic** | Validación | 2.7.4 | Backend | Validación de esquemas de datos estructurados compilada en Rust. |
| **SentenceTransformers** | Embeddings PLN | 3.0.1 | Backend | Representaciones vectoriales con `paraphrase-multilingual-MiniLM`. |
| **PyTorch (CPU)** | Tensores Cómputo | 2.3+ (CPU) | Backend | Inferencia matricial y cálculo de similitud coseno optimizado. |
| **RDFLib** | Web Semántica | 7.0.0 | Backend | Parseo y recorrido del grafo de la ontología formal (`ontologyv4.rdf`). |
| **Scikit-Learn** | Machine Learning | 1.5.0 | Backend | Normalización multivariada (`MinMaxScaler`) de variables del SDI. |
| **Pandas** | Análisis de Datos | 2.2.2 | Backend | Agregación estadística por ticket/issue y cómputo de cuartiles. |
| **OpenAI Client** | Inferencia LLM | >= 1.40.0 | Backend | Clasificación zero/few-shot estructurada con `gpt-4o-mini`. |
| **Docker** | Contenerización | 24+ / 26+ | VPS Contabo | Empaquetamiento reproducible de dependencias y servicios. |
| **Coolify** | Orquestador PaaS | v4.x | VPS Contabo | Gestión de despliegue continuo, proxy inverso y certificados SSL. |

---

## 3. TAXONOMÍA DEL SISTEMA: DISTINCIÓN ENTRE LA INTERFAZ VISIBLE Y LOS MECANISMOS INTERNOS

Para los propósitos de evaluación y trazabilidad científica, es fundamental distinguir conceptualmente qué componentes constituyen la **interfaz visible** (con la que interactúa el usuario o investigador) y qué elementos corresponden a los **mecanismos internos** (los algoritmos, heurísticas y modelos matemáticos que operan de forma automatizada).

```
+-----------------------------------------------------------------------------------+
|                        CAPA VISIBLE (INTERFAZ DE USUARIO)                         |
|  [1. Consola Texto]  [2. Checklist Validación]  [3. Monitor Progreso Lote con ETA]|
|  [4. Dashboard EDA]  [5. Dashboard por Incidencia]  [6. Auditoría y Excel Multi-hoja]|
|  [7. Historial Persistente en IndexedDB]                                          |
+-----------------------------------------------------------------------------------+
                                      │
                     Invocación e intercambio de datos
                                      ▼
+-----------------------------------------------------------------------------------+
|                   CAPA INVISIBLE (MECANISMOS INTERNOS Y MOTOR)                    |
|  [Paso 1: Normalización regex, sanitización de trazas y depuración de ruido]       |
|  [Paso 2: Inferencia LLM gpt-4o-mini + Motor de Reglas de Prioridad Sintáctica]   |
|  [Paso 3: Embeddings semánticos MiniLM + Enriquecimiento en Grafo RDF/OWL]        |
|  [Paso 4: Formulación Matemática del Índice de Deuda Social (SDI) y Cuartiles]     |
|  [Paso 5: Orquestador asíncrono con asyncio.Lock y telemetría de rate-limits]     |
+-----------------------------------------------------------------------------------+
```

---

### 3.1. La Interfaz Visible (Capa de Presentación y Experiencia de Usuario)

La interfaz gráfica de usuario está estructurada en siete módulos principales orientados al análisis interactivo y la toma de decisiones:

#### 1. Consola de Diagnóstico Individual e Ingesta Inmediata
* **Ubicación:** Componentes `ChatLayout.tsx`, `ChatInput.tsx` y `TextResultCard.tsx`.
* **Función:** Permite al analista ingresar manualmente comentarios técnicos en lenguaje natural para obtener una clasificación inmediata en tiempo real.
* **Elementos Visibles:** Caja de texto con soporte multilinea, botón de envío interactivo, tarjetas de visualización con insignias de colores (*badges*) para la macro-causa asignada, puntuación de confianza porcentual, regla de prioridad activada y desglose desplegable de micro-causas ontológicas con sus estrategias de mitigación.

#### 2. Sistema de Ingesta Masiva y Pre-validación de Esquemas
* **Ubicación:** Componentes `ValidationChecklistModal.tsx` y `useFileValidation.ts`.
* **Función:** Actúa como una compuerta de aseguramiento de calidad antes de procesar lotes de datos.
* **Elementos Visibles:**
  * Modal interactivo que evalúa automáticamente la estructura del archivo subido (CSV o Excel).
  * Lista de verificación de cabeceras requeridas (detección de columnas para cuerpo del comentario, identificador de incidencia e ID de autor).
  * Selector interactivo para la resolución de **"comentarios huérfanos"** (aquellos que no tienen asociado un número de incidencia): permite al usuario elegir entre agruparlos en un contenedor sintético (`UNGROUPED-COMMENTS`), procesarlos individualmente o descartarlos del análisis cuantitativo.
  * Widget de cuota en vivo (`OpenAILimitsBadge.tsx`) que consulta las peticiones restantes permitidas por OpenAI, bloqueando la carga si el dataset excede la capacidad disponible.

#### 3. Monitor de Progreso Asíncrono de Lotes
* **Ubicación:** Componente `BatchProgressCard.tsx`.
* **Función:** Proporciona retroalimentación visual continua durante el procesamiento de datasets voluminosos.
* **Elementos Visibles:** Barra de progreso porcentual, conteo de comentarios procesados respecto al total ($N_{proc} / N_{total}$), cálculo dinámico de tiempo estimado de finalización (ETA en minutos o segundos) y botón para abortar o cancelar el trabajo en ejecución (`cancel_batch`).

#### 4. Panel de Análisis Exploratorio Global (Global EDA Dashboard)
* **Ubicación:** Componente `GlobalEdaDashboard.tsx` dentro de `BatchDashboard.tsx`.
* **Función:** Sintetiza los patrones macroestructurales del conjunto de datos analizado.
* **Elementos Visibles:**
  * Tarjetas de resumen cuantitativo: total de comentarios, total de incidencias, porcentaje de ruido depurado vs. contenido útil, y distribución de macro-causas sociotécnicas (categorías A a H).
  * Gráfico de distribución de *Community Smells* detectados (e.g., *Organizational Silo*, *Radio Silence*, *Black-Cloud Effect*).
  * Tabla de prevalencia de riesgos técnicos y organizacionales identificados a partir del grafo ontológico.

#### 5. Tablero de Análisis por Incidencia (Issue-Level Dashboard)
* **Ubicación:** Componente `IssueLevelDashboard.tsx`.
* **Función:** Permite profundizar en el diagnóstico individual de cada ticket o *pull request*.
* **Elementos Visibles:**
  * Selector desplegable y buscador reactivo de incidencias.
  * Tarjeta de puntuación del **Índice de Deuda Social (SDI)** de la incidencia, acompañada de su nivel categórico (**Low**, **Medium**, **High Social Debt**) representado mediante códigos cromáticos (verde, amarillo y rojo).
  * Gráfico radial (*radar chart*) que mapea la gravedad de la incidencia en múltiples dimensiones: diversidad de causas, frecuencia de repetición, impacto de olores comunitarios y severidad de riesgos.
  * Lista jerárquica de factores dominantes y medidas correctivas recomendadas.

#### 6. Registro de Auditoría y Trazabilidad Algorítmica (Algorithm Audit Trail)
* **Ubicación:** Componentes `AlgorithmAuditTrail.tsx` y `excelExportService.ts`.
* **Función:** Garantiza la transparencia total del método analítico y la reproducibilidad científica.
* **Elementos Visibles:**
  * Tabla granular que expone cada comentario individual junto con su texto original, texto limpio post-normalización, nivel de ruido catalogado (*hard noise*, *soft noise* o *useful*), código de macro-causa resultante, modelo emisor (LLM vs. Regla Heurística) y top-3 de micro-causas emparejadas con sus coeficientes de similitud.
  * Botón de descarga de reporte maestro: genera un archivo de Microsoft Excel (`.xlsx`) multi-pestaña estructurado profesionalmente (*Resumen Ejecutivo*, *Métricas por Issue*, *Auditoría Comentario por Comentario* y *Diccionario Ontológico*).

#### 7. Gestor de Historial y Sesiones Locales
* **Ubicación:** Componente `HistorySidebar.tsx` conectado a `historyDB.ts`.
* **Función:** Permite al investigador alternar entre múltiples experimentos y datasets analizados previamente sin necesidad de re-procesar los archivos ni consumir cuotas de API adicionales.

---

### 3.2. Los Mecanismos Internos (Capa de Cómputo, Procesamiento y Modelado)

Los mecanismos internos constituyen el núcleo algorítmico del backend (`social-debt-api-model`), ejecutándose en un **pipeline secuencial de 5 fases estandarizadas**:

```
[Texto Crudo]
      │
      ▼
┌────────────────────────────────────────────────────────┐
│ FASE 1: Limpieza Regex, Sanitización y Filtro de Ruido │
│  - /inline_code, /code_block, /error_trace             │
│  - Hard Noise vs. Soft Noise vs. Useful                │
└────────────────────────────────────────────────────────┘
      │
      ▼ (Si es texto útil)
┌────────────────────────────────────────────────────────┐
│ FASE 2: Clasificación Heurística y Basada en LLM       │
│  - gpt-4o-mini con temperatura determinista            │
│  - Priority Rules Engine (Salvaguarda léxica)          │
│  - Catálogo de 8 Macro-Causas (A - H)                  │
└────────────────────────────────────────────────────────┘
      │
      ▼ (Si la causa != H)
┌────────────────────────────────────────────────────────┐
│ FASE 3: Emparejamiento Semántico y Grafo Ontológico    │
│  - SentenceTransformers paraphrase-multilingual-MiniLM │
│  - Score Híbrido: Similitud Coseno + Overlap Léxico    │
│  - Consulta RDFLib sobre ontologyv4.rdf (Smells/Risks) │
└────────────────────────────────────────────────────────┘
      │
      ▼
┌────────────────────────────────────────────────────────┐
│ FASE 4: Formulación Matemática del SDI por Incidencia  │
│  - Agregación por issue de 9 variables sociotécnicas   │
│  - Normalización MinMaxScaler multivariada             │
│  - Cómputo del SDI medio y categorización en terciles   │
└────────────────────────────────────────────────────────┘
      │
      ▼
┌────────────────────────────────────────────────────────┐
│ FASE 5: Consolidación y Despacho Asíncrono de Lotes    │
│  - asyncio.Lock y estimación predictiva de tiempo ETA  │
│  - Serialización estructurada de jobs en disco         │
└────────────────────────────────────────────────────────┘
```

#### Fase 1: Normalización Determinista y Depuración de Ruido (`cleaning.py`, `noise_filtering.py`)
1. **Sanitización de Fragmentos de Código y Trazas:**
   * Sustitución de bloques de código delimitados por triple acento grave (```...```) por el token sintáctico `/code_block` o `/error_trace` si contienen firmas de error (*Traceback*, *exit code*, *panic*).
   * Sustitución de código en línea (`...`) por el token `/inline_code`.
   * Enmascaramiento de menciones de usuarios de GitHub (`@usuario`) por la cadena canónica `a github user is mentioned`.
   * Enmascaramiento de enlaces web por el token `url_reference`.
   * Normalización de emojis a representaciones semánticas textuales (e.g., 👍 $ightarrow$ `:thumbsup:`).
2. **Filtrado de Ruido en Dos Niveles:**
   * **Ruido Severo (*Hard Noise*):** Cadenas que contienen únicamente referencias de commit, bloques HTML vacíos o cadenas irrelevantes (descartadas inmediatamente de la inferencia semántica).
   * **Ruido Leve (*Soft Noise*):** Mensajes puramente procedimentales emitidos por bots de integración continua (e.g., `needs rebase`, `awaiting triage`, `lgtm`, `pull request has been approved`).

#### Fase 2: Clasificación Heurística y Basada en Modelos de Lenguaje (`llm_classifier.py`, `priority_rules.py`)
Los comentarios catalogados como útiles se someten a una clasificación estructurada dentro de un catálogo cerrado de **8 macro-causas sociotécnicas**:
* **A:** *Communication and shared understanding breakdowns* (Fallas de comunicación y comprensión compartida).
* **B:** *Coordination and workflow misalignment* (Desalineación en la coordinación del flujo de trabajo).
* **C:** *Technical complexity, compatibility, and system constraints* (Complejidad técnica, compatibilidad y restricciones del sistema).
* **D:** *Organizational and procedural workflow constraints* (Restricciones organizacionales y procedimientos formales).
* **E:** *Collaboration and interpersonal tensions* (Tensiones interpersonales y fricciones colaborativas).
* **F:** *Knowledge, documentation, and standards deficiencies* (Deficiencias de conocimiento, estándares y documentación).
* **G:** *Resource, tooling, access, and validation dependencies* (Dependencias de recursos, herramientas, accesos y validación).
* **H:** *No identifiable sociotechnical cause* (Sin causa sociotécnica identificable / Contenido neutro).

* **Interacción con el LLM:** Se envía un prompt de sistema riguroso al modelo `gpt-4o-mini` a través de la API de OpenAI, solicitando la predicción del código macro y una estimación de confianza numérica.
* **Motor de Reglas de Prioridad Sintáctica (*Priority Rules Engine*):** Actúa como un mecanismo de salvaguarda (*failsafe*). Evalúa expresiones regulares que detectan evidencia explícita e inequívoca en el texto (e.g., términos técnicos específicos de pruebas para G, expresiones de disculpa o confusión para A, discusiones de ramificación y releases para D). Si la confianza del LLM es inferior a **0.70** o si el LLM clasificó erróneamente como causa neutral H un comentario que presenta evidencia léxica fuerte, la regla determinista anula la predicción (*override*), garantizando estabilidad analítica.

#### Fase 3: Emparejamiento Semántico y Enriquecimiento Ontológico (`ontology_matcher.py`, `ontology_client.py`)
Para los comentarios asignados a causas sociotécnicas activas (códigos A a G), se procede a identificar las **micro-causas específicas** dentro de la ontología formal del proyecto:
1. **Filtrado Ontológico Previo:** La macro-causa predicha restringe el espacio de búsqueda exclusivamente a los conceptos hijos permitidos en el grafo ontológico (`MACRO_TO_CANDIDATE_INDIVIDUALS`).
2. **Cómputo Vectorial y Puntuación Híbrida:** Se calcula el vector denso del comentario utilizando `SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")` y se compara contra las descripciones vectorizadas de cada micro-causa mediante similitud coseno. Dicho valor se combina linealmente con una métrica de solapamiento léxico de tokens:
   $$	ext{Score}_{	ext{híbrido}} = (1 - alpha) cdot 	ext{Sim}_{	ext{coseno}} + alpha cdot 	ext{Overlap}_{	ext{léxico}}$$
   donde $alpha = 0.10$ y el peso de similitud léxica pondera términos clave ontológicos.
3. **Selección Top-K:** Se seleccionan los 3 candidatos con mayor puntuación ($k=3$), siempre que superen el umbral mínimo de corte ($ge 0.28$) y se encuentren dentro de una ventana de tolerancia máxima ($le 0.18$) respecto al mejor candidato.
4. **Travesía del Grafo de Conocimiento (RDF/OWL):** Utilizando `RDFLib`, el sistema consulta el grafo `ontologyv4.rdf` y extrae automáticamente las propiedades conceptuales vinculadas a la micro-causa:
   * *Community Smells* asociados (`hasRelatedCommunitySmell`).
   * Riesgos que genera o a los que conduce (`leadsToRisk`, `generatesRisk`).
   * Estrategias preventivas (`hasAdministrativePreventiveStrategy`, `hasCommunicationStrategy`, etc.).
   * Estrategias correctivas (`hasCorrectiveStrategy`, `hasTechnicalStrategy`, etc.).
   * Indicadores de monitoreo (`isMonitoredByIndicator`) y Métricas de medición (`isMeasuredByMetric`).

#### Fase 4: Formulación Matemática del Índice de Deuda Social (SDI) (`social_debt_index.py`)
El cálculo del **Índice de Deuda Social (SDI)** se formula a nivel de incidencia o ticket aglutinador ($i$), integrando la distribución agregada de sus comentarios:

1. **Extracción del Vector de Características por Incidencia:**
   Para cada ticket $i$, se derivan 9 variables sociotécnicas fundamentales:
   * $C_{clean, i}$: Cantidad de comentarios útiles no clasificados como ruido.
   * $D_{macro, i}$: Diversidad de macro-causas distintas identificadas.
   * $D_{micro, i}$: Diversidad de micro-causas distintas detectadas.
   * $D_{smell, i}$: Diversidad de olores comunitarios presentes.
   * $D_{risk, i}$: Diversidad de factores de riesgo vinculados.
   * $F_{macro, i}$: Frecuencia de aparición de la macro-causa dominante.
   * $S_{micro, i}$: Puntuación máxima de similitud acumulada de la micro-causa dominante.
   * $F_{smell, i}$: Frecuencia del olor comunitario más recurrente.
   * $F_{risk, i}$: Frecuencia del riesgo más recurrente.

2. **Normalización Multivariada:**
   Las variables se normalizan en el rango $[0, 1]$ mediante la transformación lineal Min-Max calculada sobre el lote completo analizado:
   $$X_{	ext{norm}} = rac{X - min(X)}{max(X) - min(X)}$$

3. **Ecuación del Índice Compuesto (SDI):**
   El valor del Índice de Deuda Social de la incidencia $i$ se define matemáticamente como la media aritmética de las 6 variables normativas primarias de intensidad sociotécnica:
   $$SDI_i = rac{1}{6} left( C_{clean, i}^{	ext{norm}} + D_{macro, i}^{	ext{norm}} + F_{macro, i}^{	ext{norm}} + S_{micro, i}^{	ext{norm}} + F_{smell, i}^{	ext{norm}} + F_{risk, i}^{	ext{norm}} ight)$$

4. **Estratificación Categórica por Terciles Empíricos:**
   Para clasificar el nivel de severidad de forma relativa y adaptada al proyecto analizado, se computan los terciles de la distribución empírica del SDI ($q_1 = 33%$ y $q_2 = 66%$):
   * **Low Social Debt (Deuda Social Baja):** $SDI_i le q_1$
   * **Medium Social Debt (Deuda Social Media):** $q_1 < SDI_i le q_2$
   * **High Social Debt (Deuda Social Alta):** $SDI_i > q_2$

#### Fase 5: Orquestador de Procesamiento Asíncrono y Gestión de Lotes (`routes.py`)
* **Control de Concurrencia:** Empleo de `asyncio.Lock()` para impedir la sobrecarga de la memoria RAM del VPS provocada por ejecuciones simultáneas de transformers.
* **Estimación Adaptativa de Tiempo (ETA):** El motor calcula continuamente la velocidad media de procesamiento (establecida nominalmente en $sim 0.30$ segundos por comentario bajo inferencia concurrente) y proyecta el tiempo restante dinámicamente en minutos y segundos.
* **Manejo de Errores y Tolerancia a Fallos:** Si una consulta al LLM sufre desconexión o rebote de red, el sistema captura la excepción, reintenta la operación y, en caso de fallo crítico, aplica una clasificación de contingencia heurística conservadora sin truncar el procesamiento del archivo.

---

## 4. ORGANIZACIÓN Y ESTRUCTURA DE LOS REPOSITORIOS DE CÓDIGO

### 4.1. Repositorio de Frontend (`social-debt-frontend-model`)
El repositorio de la interfaz está organizado bajo el patrón arquitectónico **Feature-Driven Architecture** (Arquitectura Basada en Funcionalidades), lo que aísla la lógica de estado, los componentes visuales y los servicios por dominio temático:

```
social-debt-frontend-model/
├── src/
│   ├── app/                                 # Rutas y envolventes de Next.js App Router
│   │   ├── layout.tsx                       # Plantilla principal y fuentes tipográficas
│   │   ├── page.tsx                         # Orquestador del estado global y vistas
│   │   └── globals.css                      # Estilos base y tokens de Tailwind CSS v4
│   ├── features/                            # Módulos desacoplados por funcionalidad
│   │   ├── analytics-dashboard/             # Visualización y tableros analíticos
│   │   │   ├── BatchDashboard.tsx           # Pestañas unificadas (Global, Issue, Audit)
│   │   │   ├── global-view/                 # Tablero exploratorio global (EDA)
│   │   │   │   ├── GlobalEdaDashboard.tsx   # Métricas agregadas y distribuciones
│   │   │   │   └── edaUtils.ts              # Pre-cálculo estadístico vectorizado
│   │   │   ├── issue-view/                  # Tablero por incidencia/ticket individual
│   │   │   │   ├── IssueLevelDashboard.tsx  # Gráficos radiales y métricas de ticket
│   │   │   │   └── issueMetricsUtils.ts     # Helpers de métricas y formateo
│   │   │   └── traceability-view/           # Auditoría algorítmica y exportador
│   │   │       ├── AlgorithmAuditTrail.tsx  # Tabla detallada fila por fila
│   │   │       └── excelExportService.ts    # Generación de reportes Excel multi-pestaña
│   │   ├── dataset-inspection/              # Aseguramiento de calidad de datasets
│   │   │   ├── ValidationChecklistModal.tsx # Modal de validación previa de columnas
│   │   │   └── useFileValidation.ts         # Hook de análisis y resolución de huérfanos
│   │   ├── history/                         # Gestión de persistencia local
│   │   │   ├── HistorySidebar.tsx           # Barra lateral de historial de análisis
│   │   │   └── historyDB.ts                 # Operaciones asíncronas sobre IndexedDB
│   │   ├── ontology-catalog/                # Catálogo ontológico sincronizado
│   │   │   ├── frontend_ontology_dictionary.json # Diccionario JSON de la ontología
│   │   │   └── useOntology.ts               # Hook de consulta rápida de términos
│   │   └── social-debt-engine/              # Conectores y controladores de inferencia
│   │       ├── batch-actions.ts             # Server Actions (Proxy BFF hacia el backend)
│   │       ├── text-actions.ts              # Server Actions para clasificación individual
│   │       └── components/                  # Componentes visuales de progreso y cuotas
│   │           ├── BatchProgressCard.tsx    # Tarjeta de progreso y cálculo de ETA
│   │           ├── BatchResultSummaryCard.tsx # Tarjeta de resumen de finalización
│   │           ├── OpenAILimitsBadge.tsx    # Widget en vivo de cuota de OpenAI
│   │           └── TextResultCard.tsx       # Tarjeta de resultado para texto único
│   └── shared/                              # Componentes genéricos reutilizables
│       ├── ChatInput.tsx                    # Caja de entrada de comentarios/archivos
│       └── ChatLayout.tsx                   # Estructura visual de paneles
├── .env.example                             # Plantilla de variables de entorno (Vercel)
├── package.json                             # Dependencias y scripts de construcción
└── tsconfig.json                            # Configuración estricta del compilador TS
```

---

### 4.2. Repositorio de Backend (`social-debt-api-model`)
El repositorio del motor de cómputo adopta los principios de **Clean Architecture** (Arquitectura Limpia en Capas), separando el núcleo de dominio de los detalles de infraestructura, frameworks y casos de uso:

```
social-debt-api-model/
├── app/
│   ├── main.py                              # Entrada ASGI, Middlewares CORS y seguridad
│   ├── api/                                 # Capa de transporte y controladores HTTP
│   │   └── routes.py                        # Definición de endpoints REST y jobs asíncronos
│   ├── core/                                # Configuración y variables del sistema
│   │   └── config.py                        # Configuración Pydantic Settings (.env)
│   ├── domain/                              # Modelos de dominio y contratos abstractos
│   │   └── schemas.py                       # Esquemas Pydantic v2 (Input/Output DTOs)
│   ├── infrastructure/                      # Conectores externos y adaptadores
│   │   ├── llm_client.py                    # Cliente asíncrono para la API de OpenAI
│   │   ├── ontology_client.py               # Cargador y buscador de grafos con RDFLib
│   │   └── ontologyv4.rdf                   # Archivo formal de la ontología en XML/RDF
│   └── use_cases/                           # Lógica de negocio y pipeline científico
│       ├── preprocessing/                   # Fase 1: Limpieza determinista y ruido
│       │   ├── cleaning.py                  # Sanitización regex, código, trazas y emojis
│       │   └── noise_filtering.py           # Filtros booleanos de hard noise y soft noise
│       ├── classification/                  # Fase 2: Clasificación de macro-causas
│       │   ├── llm_classifier.py            # Orquestador del prompt y llamada a gpt-4o-mini
│       │   └── priority_rules.py            # Motor de reglas sintácticas prioritarias
│       ├── semantic/                        # Fase 3: Emparejamiento ontológico
│       │   └── ontology_matcher.py          # Embeddings multilingües y similitud híbrida
│       └── metrics/                         # Fase 4: Modelo matemático de Deuda Social
│           └── social_debt_index.py         # Cálculo del SDI, normalización y cuartiles
├── docs/                                    # Documentación técnica y trazabilidad
│   ├── audit/                               # Reportes de auditoría de varianza algorítmica
│   │   ├── latest_variance_audit_summary.md # Síntesis ejecutiva de estabilidad del LLM
│   │   └── reporte_varianza_exhaustivo.json # Resultados cuantitativos de varianza
│   └── research/                            # Cuadernos Jupyter y baseline científico
│       └── baseline_notebooks/              # Cuadernos originales de investigación
├── scripts/                                 # Catálogo de scripts de utilidad y pruebas
│   ├── auditoria_completa.py                # Auditoría integral end-to-end del pipeline
│   ├── audit_openai_variance.py             # Prueba empírica de variabilidad de inferencia
│   ├── run_metrics_benchmark.py             # Pruebas de rendimiento y latencia en ms
│   ├── run_interactive_load_test.py         # Pruebas de estrés y carga concurrente
│   ├── check_openai_limits.py               # Monitoreo de cabeceras de cuota de OpenAI
│   ├── generate_frontend_dictionary.py      # Extractor de ontología RDF hacia JSON
│   └── debug_single_comment.py              # Script de depuración para casos borde
├── Dockerfile                               # Especificación de construcción en Coolify
├── requirements.txt                         # Dependencias fijadas para Python 3.11
├── .env.example                             # Plantilla de variables de entorno protegidas
└── README.md                                # Manual técnico y de despliegue en servidor
```

---

### 4.3. Catálogo de Scripts de Utilidad Científica y Benchmarking (`scripts/`)
El backend cuenta con un conjunto de herramientas ejecutables diseñadas para garantizar la rigurosidad científica, auditoría y mantenimiento continuo del sistema:

1. **`auditoria_completa.py`:** Ejecuta una validación integral del pipeline de cinco fases sobre un conjunto de comentarios de control, verificando que la normalización textual, la inferencia del modelo, la aplicación de reglas y el enriquecimiento ontológico produzcan resultados consistentes.
2. **`audit_openai_variance.py`:** Evalúa empíricamente la tasa de varianza o discrepancia en las respuestas del LLM (`gpt-4o-mini`) al someter repetidamente los mismos comentarios a inferencia con temperatura controlada, documentando la tasa de consistencia de las macro-causas.
3. **`run_metrics_benchmark.py`:** Mide la latencia de cómputo en milisegundos para cada una de las fases del pipeline (limpieza, inferencia semántica, cálculo vectorial y agregación del SDI), identificando posibles cuellos de botella en el procesamiento.
4. **`run_interactive_load_test.py`:** Realiza pruebas de estrés mediante concurrencia simulada contra la API REST, validando el comportamiento del semáforo de bloqueo asíncrono y la estabilidad de la memoria RAM del servidor VPS.
5. **`check_openai_limits.py`:** Consulta e imprime en consola los límites operativos vigentes de la cuenta de OpenAI (`remaining requests`, `limit requests`, `reset tokens`), facilitando diagnósticos rápidos antes de iniciar experimentos masivos.
6. **`generate_frontend_dictionary.py`:** Script de sincronización que parsea el grafo `ontologyv4.rdf` y regenera de forma determinista el archivo JSON consumido por el frontend (`frontend_ontology_dictionary.json`), garantizando que la interfaz y el backend utilicen exactamente la misma taxonomía ontológica.
7. **`debug_single_comment.py`:** Permite aislar y depurar paso a paso un comentario específico en consola, imprimiendo el texto normalizado, los tokens reemplazados, la regla sintáctica aplicada y los candidatos ontológicos emparejados.

---

### 4.4. Trazabilidad Académica y Baseline Científico (`docs/research/baseline_notebooks/`)
Para salvaguardar la reproducibilidad experimental y respaldar el marco metodológico de la tesis académica, el repositorio preserva íntegramente la secuencia histórica de cuadernos Jupyter que dieron origen al modelo:
* **Fase 1 (Limpieza):** Procedimientos iniciales de normalización de cadenas de texto y remoción de caracteres de control.
* **Fase 2 (Eliminación de Ruido):** Experimentación empírica para la separación de *hard noise* y *soft noise*.
* **Fase 3 (Identificación Semántica):** Pruebas iniciales de emparejamiento con el catálogo ontológico.
* **Fase 4 (Integración del Modelo):** Primeras formulaciones de ensamblaje entre reglas heurísticas y modelos de lenguaje.
* **Fase 5 (Modelos y Evaluación):** Comparación empírica de arquitecturas y ajuste de hiperparámetros.
* **Fase 6 (Análisis Exploratorio de Datos - EDA):** Generación de distribuciones estadísticas basales sobre los conjuntos de datos originales.

---
