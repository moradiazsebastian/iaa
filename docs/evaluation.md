# `evaluation/`: métricas, benchmark y Ground Truth de Boca

El paquete `foco_social.evaluation` implementa las **4 suites del entorno de evaluación y benchmark** más la generación de datasets etiquetados (tanto sintéticos como reales sobre partidos de Boca Juniors).

---

## 1. Suites de Métricas (`metrics.py`)

### Suite A: Relevancia y Filtrado de Ruido (`evaluate_relevance`)

Evalúa qué tan bien un filtro o agente distingue los mensajes que realmente pertenecen al evento/tema (`is_relevant = True`) del ruido colado en la búsqueda (`is_relevant = False`).

| Métrica | Qué mide | Rango |
|---|---|---|
| `precision`, `recall`, `f1`, `accuracy` | Desempeño de clasificación binaria sobre `is_relevant` | 0 a 1 |
| `noise_leakage_rate` | Proporción de mensajes irrelevantes reales que terminaron metidos en un tópico final | 0 (ideal) a 1 |
| `false_drop_rate` | Proporción de mensajes relevantes reales descartados por error (`1 - recall`) | 0 (ideal) a 1 |

### Suite B: Calidad de Partición y Modelos de Embeddings (`compare`, `evaluate`, `evaluate_intrinsic`)

#### Métricas Extrínsecas (contra Ground Truth `topic` / `subtopic`)

| Métrica | Qué mide | Rango |
|---|---|---|
| `ari` (Adjusted Rand Index) | Acuerdo de pares de mensajes corregido por azar | -1 a 1 (1 = idénticos) |
| `nmi` (Normalized Mutual Information) | Información mutua normalizada entre particiones | 0 a 1 |
| `homogeneity`, `completeness`, `v_measure` | Pureza de cada cluster, completitud de cada tópico real y su media armónica (fundamental cuando BERTopic elige $K$ automáticamente) | 0 a 1 |
| `matched_accuracy` | Proporción de aciertos emparejando 1 a 1 tópicos predichos y reales (algoritmo húngaro) | 0 a 1 |

#### Métricas Intrínsecas (sin etiquetas manuales, aplicables a cualquier partido)

| Métrica | Qué mide | Rango |
|---|---|---|
| `outlier_rate` | Proporción de mensajes que HDBSCAN dejó como `-1` antes de reasignar | 0 a 1 |
| `topic_diversity` | Proporción de palabras únicas entre las top-$N$ palabras c-TF-IDF de todos los tópicos | 0 a 1 (1 = sin redundancia) |
| `topic_coherence_npmi` | Coherencia semántica NPMI sobre co-ocurrencia documental de las palabras principales | -1 a 1 |
| `silhouette_cosine` | Separación geométrica de los clusters en el espacio de embeddings | -1 a 1 |

### Suite C: Valor Agregado del Agente / LLM (`evaluate_reassignment_delta`, `evaluate_label_quality`)

- **`evaluate_reassignment_delta(pre_pred, post_pred, gold)`**: Compara la partición inicial de BERTopic antes del paso de reasignación del LLM (`pre`) contra la partición final (`post`), reportando `delta_ari`, `delta_v_measure`, `delta_matched_accuracy` y `n_reassigned`.
- **`evaluate_label_quality(topics, texts_by_topic, llm=None)`**: Calcula indicadores estructurales sin costo (`label_distinctness`, `lexical_grounding`, `non_fallback_rate`) y, si se pasa un `LLM` activo, ejecuta **LLM-as-a-Judge** puntuando de 1 a 5 `judge_faithfulness`, `judge_specificity` y `judge_exclusivity`.

---

## 2. Ground Truth sobre Partidos de Boca (`boca.py`)

Convierte los CSVs crudos descargados de `twitterapi.io` (`Datasets/Boca/<partido>/*.csv`) al esquema de `StaticSource` y genera las etiquetas de referencia (`is_relevant`, `topic`, `subtopic`) para los 3 partidos principales del benchmark (**1.991 tweets únicos**: *Deportivo Riestra*, *River Plate* y *Cruzeiro*):

```bash
foco prepare-boca --boca-root ../tp/Datasets/Boca --out-dir data/benchmark
```

Genera en `data/benchmark/`:
- `riestra.csv`, `river_plate.csv`, `cruzeiro.csv` (con ruido real para evaluar **Suite A** y el flujo completo).
- `riestra_relevant.csv`, `river_plate_relevant.csv`, `cruzeiro_relevant.csv` (solo relevantes para evaluar **Suite B** y **Suite C**).
- `boca_benchmark_all.csv` y `summary.json`.

---

## 3. Orquestador de Benchmark (`benchmark.py` y `foco benchmark`)

```bash
foco benchmark --theme "Boca vs Deportivo Riestra" \
  --keywords boca,riestra,paredes,lollo,marchesin,zeballos,janson \
  --data data/benchmark/riestra.csv \
  --embedding-models tfidf,paraphrase-multilingual-MiniLM-L12-v2
```

Genera en `runs/<id>-benchmark-<tema>/`:
- `relevance_results.csv`: comparación de estrategias de filtrado de relevancia (Suite A).
- `embedding_results.csv`: comparación de modelos de embeddings y métodos (Suite B).
- `benchmark_report.md`: reporte consolidado en Markdown.
