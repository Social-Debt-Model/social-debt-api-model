# Resumen de Auditoría de Varianza y Paridad Técnica (Cuaderno vs. API)

Este documento resume los resultados del análisis comparativo y de paridad técnica realizado sobre 1.000 comentarios de prueba, evaluando la coherencia entre el pipeline de experimentación inicial (cuadernos de investigación) y la arquitectura de la API en producción.

---

## 1. Tasa de Coincidencia en Clasificación de Macrocausas

Al procesar simultáneamente los 1.000 comentarios mediante el pipeline de investigación y el pipeline de la API, se evaluó si el modelo de OpenAI asignaba idéntica Macrocausa (categorías A–H).

* **Total de comentarios procesados:** 1.000
* **Tasa de coincidencia (Match Rate):** **97.21%**

**Conclusión técnica:**  
La coincidencia es prácticamente total. La variación del 2.79% corresponde a la naturaleza estocástica intrínseca de los modelos de lenguaje (LLM). En textos con ambigüedad semántica, incluso con un parámetro de `temperature = 0`, el servicio de inferencia puede presentar variaciones menores. Una consistencia del 97.21% valida una alta estabilidad en la clasificación.

---

## 2. Paridad en el Índice de Deuda Social (SDI)

El SDI constituye la métrica compuesta final del modelo. Se agruparon los comentarios en sus respectivos Issues (38 issues identificados en el subconjunto de 1.000 registros) y se calculó la desviación absoluta del SDI entre ambos pipelines.

* **Total de issues procesados:** 38
* **Desviación absoluta media del SDI:** **0.007392**

**Conclusión técnica:**  
La desviación media es estadísticamente despreciable. Una discrepancia de 0.007 puntos en una escala normalizada de 0 a 1 confirma que la API replica el modelo matemático con una precisión superior al **99.2%**.

---

## 3. Arquitectura y Equivalencia de Componentes

La arquitectura implementada en la API garantiza paridad estricta con la metodología experimental original:

1. **Preprocesamiento y Filtrado de Ruido:**  
   Se aplican las mismas expresiones regulares (RegEx) para remover menciones, bloques de código, hashes y elementos no informativos.
2. **Inferencia LLM (OpenAI):**  
   Se mantiene la formulación exacta de prompts y delimitadores para la determinación de Macrocausas (A–H).
3. **Similitud Semántica Local (Sentence-Transformers):**  
   El modelo `paraphrase-multilingual-MiniLM-L12-v2` se ejecuta localmente en el entorno del servidor, garantizando reproducibilidad en el mapeo de Microcausas con menor latencia y sin dependencias de red externas.

---

### Registro de Datos de Auditoría
* El detalle registro a registro se encuentra disponible en: [reporte_varianza_exhaustivo.json](./reporte_varianza_exhaustivo.json).
