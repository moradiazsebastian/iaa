# `topic_models.py`: métodos de detección de tópicos

Permite cambiar el algoritmo que agrupa los mensajes sin tocar el resto del agente. Se elige
con `TOPIC_MODEL` en `.env` o con `--method` en la línea de comandos.

## La interfaz común: `TopicFit`

Todos los métodos devuelven lo mismo, que es lo único que necesita `split_topic`:

| Campo | Contenido |
|---|---|
| `labels` | tópico de cada mensaje, numerado 0..k-1. No hay outliers: ya se asignaron |
| `confidence` | qué tan segura es cada asignación: diferencia entre el mejor tópico y el segundo. Los outliers tienen 0 |
| `sublabels` | subtópicos ya calculados (solo BERTopic; si no, `None`) |

`confidence` decide qué mensajes revisa el LLM: el 15% menos seguro, más todos los que
tengan confianza 0, hasta `MAX_LLM_REASSIGN` por nivel.

## Funciones públicas

- **`fit_topics(texts, n_topics, settings)`**: agrupa con el método de `settings.topic_model`.
  `n_topics=None` elige la cantidad automáticamente, hasta `MAX_AUTO_TOPICS` (8).
- **`fit_presplit(texts, sublabels, n_topics, settings)`**: para el segundo nivel de BERTopic.
  Usa los subtópicos que ya se calcularon en el nivel 1 en lugar de volver a ajustar el modelo.

## Los métodos

### `kmeans` (`_fit_kmeans`)
Usa `embed` + `cluster` de [clustering.md](clustering.md). La confianza es el margen entre los
dos centroides más cercanos. Es el más rápido, y con TF-IDF no necesita dependencias extra.

### `lda` (`_fit_lda`)
Latent Dirichlet Allocation de scikit-learn sobre conteos de palabras (sin acentos ni
stopwords, conservando hashtags).

- LDA da a cada mensaje una **mezcla** de tópicos (`theta`). El tópico asignado es el de
  mayor peso, y la confianza es la diferencia entre los dos pesos mayores. Un mensaje que
  habla de dos temas queda con confianza baja y lo revisa el LLM.
- Sin `n_topics`, prueba k = 2...8 y elige el de mayor silhouette sobre `theta`.
- Es el modelo de tópicos clásico de la literatura, útil como línea de base. Rinde mal en
  textos cortos como tweets: hay pocas palabras por mensaje para estimar la mezcla.

### `bertopic` (`_fit_bertopic`)
Requiere `pip install -e ".[bertopic]"`.

1. Embeddings multilingües (`sentence-transformers`).
2. BERTopic: reduce dimensión con UMAP (`random_state` fijo, para que sea reproducible) y
   agrupa con HDBSCAN (`min_cluster_size = max(5, n/40)`). HDBSCAN decide cuántos tópicos
   hay y marca como **outliers** (-1) los mensajes que no encajan en ninguno.
3. Los outliers se asignan al tópico más cercano con confianza 0, así que son los primeros
   que revisa el LLM.
4. Suele encontrar muchos tópicos finos (24 en el dataset de ejemplo). Se unen con clustering
   aglomerativo sobre sus centroides en `n_topics` tópicos de nivel 1, o en la cantidad con
   mejor silhouette si es automático. Es la misma idea que `BERTopic.hierarchical_topics`.
5. Los tópicos finos quedan en `sublabels`. En el nivel 2, `fit_presplit` los usa como
   subtópicos y, si hay más de `n_subtopics`, une los más parecidos.

Si HDBSCAN encuentra menos de 2 tópicos (pasa con pocos mensajes), recurre a KMeans sobre los
mismos embeddings.

Como UMAP funciona mal con grupos chicos, `fit_presplit` no vuelve a correr BERTopic: trabaja
sobre la jerarquía ya calculada. Los subtópicos con menos de 3 mensajes (típicamente mensajes
que el LLM movió desde otro tópico) se reasignan al subtópico más cercano.

## Auxiliares

- `_contiguous`: renumera etiquetas como 0..k-1, sin tocar los -1.
- `_centroids`: centroide normalizado de cada tópico.
- `_confidence`: margen entre los dos centroides más cercanos, con 0 para outliers.
- `_assign_outliers`: manda los -1 al centroide más cercano.
- `_merge` / `_best_merge`: unen tópicos con clustering aglomerativo (distancia coseno) y
  eligen cuántos grupos dejar.

## Comparar métodos

`foco compare` (ver [cli.md](cli.md)) corre cada método con y sin LLM sobre los mismos
mensajes y arma una tabla de métricas.

## Para agregar un método

1. Escribir `_fit_<método>(texts, n_topics, ...) -> TopicFit`.
2. Agregar el caso en `fit_topics`.
3. Agregar el nombre al `Literal` de `topic_model` en `config.py` y a `METHODS` en `cli.py`.
4. Agregar un caso en `tests/test_topic_models.py`.
