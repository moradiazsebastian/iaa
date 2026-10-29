# `clustering.py`: vectorización y clustering

Funciones base de vectorización y clustering. Las usa [topic_models.py](topic_models.md):
el método `kmeans` se basa enteramente en ellas, y LDA y BERTopic usan algunas. `top_terms`
se usa con cualquier método para darle pistas al LLM.

## `embed(texts, method="tfidf", seed=42)`

Devuelve una matriz con una fila por mensaje, cada fila de norma 1, de modo que el producto
punto es la similitud coseno.

- **`tfidf`** (por defecto, liviano): TF-IDF de palabras y pares de palabras, sin acentos ni
  stopwords en español (`SPANISH_STOPWORDS`), conservando hashtags. Después reduce a ≤100
  dimensiones con `TruncatedSVD`.
- **`sentence-transformers`**: embeddings semánticos multilingües
  (`paraphrase-multilingual-MiniLM-L12-v2`). Captan sinónimos y paráfrasis, pero requieren
  `pip install -e ".[embeddings]"`, que descarga torch. El modelo se carga una sola vez
  (`_sentence_model`, con `lru_cache`), y los vectores se guardan en memoria por texto
  (`_embedding_cache`), así el nivel de subtópicos no recalcula los del nivel anterior.

El TF-IDF se ajusta de nuevo en cada llamada. Al buscar subtópicos solo se usan los mensajes
de ese tópico, y así ganan peso las palabras que los distinguen entre sí.

## `cluster(X, n_clusters=None, seed=42, max_k=8)`

KMeans con semilla fija, así que el resultado es determinístico.

- Con `n_clusters`, usa ese k.
- Con `None`, prueba k = 2...`max_k` y elige el de mayor **silhouette**, que mide qué tan
  separados quedan los grupos.
- k nunca supera la cantidad de puntos distintos: mensajes casi idénticos colapsan al
  mismo vector.

Devuelve `(labels, centroides)` con centroides normalizados.

## `assignment_margin(X, centroids)`

Para cada mensaje: similitud con el centroide más cercano menos similitud con el segundo.
Un margen bajo indica un mensaje a mitad de camino entre dos tópicos. Es la `confidence` de
KMeans y BERTopic (ver [topic_models.md](topic_models.md)).

## `top_terms(texts, labels, n_terms=5)`

Términos más característicos de cada cluster: une los mensajes de cada grupo en un documento
y aplica TF-IDF entre grupos (un c-TF-IDF simplificado). Se usan como pista para el LLM y
como nombre del tópico cuando no hay LLM.

## Limitación conocida

Con TF-IDF, los nombres propios frecuentes (candidatos) pesan mucho y pueden agrupar
mensajes por persona en lugar de por tema. Opciones: embeddings semánticos
(`EMBEDDINGS=sentence-transformers` o `TOPIC_MODEL=bertopic`), o agregar esos nombres a las
stopwords.
