# `sources/`: fuentes de datos

El agente no sabe de dónde vienen los mensajes: solo usa un objeto con el método `search`.
Así se puede cambiar el dataset estático por la API de X sin tocar el grafo.

## `base.py`: la interfaz

**`TweetSource`** (un `Protocol`): cualquier clase con este método sirve como fuente.

```python
def search(self, keywords, since=None, until=None, limit=1000) -> list[Tweet]
```

Devuelve mensajes que contienen **al menos una** de las keywords.

## `static.py`: dataset estático

**`StaticSource(path)`**: abre un CSV o Parquet con DuckDB como una vista SQL `tweets`. No
carga el archivo entero en memoria.

- **`search(...)`**: busca en el texto sin distinguir mayúsculas ni acentos
  (`strip_accents(lower(text)) LIKE '%keyword%'`), filtra por fechas y ordena por
  interacción (`likes + retweets`) y luego por `id`. El orden es siempre el mismo, así que
  `limit` siempre devuelve los mismos mensajes.
- **`sql(query)`**: consulta SQL libre sobre `tweets`, solo `SELECT` / `WITH`. Útil para
  explorar los datos o para darle al agente una herramienta SQL más adelante.
- **`labels()`**: devuelve las columnas `topic` / `subtopic` indexadas por `id`, o `None` si
  el dataset no tiene etiquetas. Las usa `foco eval`.
- **`normalize(text)`**: pasa a minúsculas y quita acentos en Python, igual que lo hace la
  consulta, para que las keywords se comparen igual que el texto.
- **`TWEET_COLUMNS`**: las columnas obligatorias del dataset (ver `data/README.md`).

## `replay.py`: tiempo real simulado

**`ReplaySource(path, start=None)`**: igual que `StaticSource`, pero con un reloj interno
`now`. Solo devuelve mensajes publicados hasta `now`; `advance(timedelta)` adelanta el reloj
y hace aparecer mensajes nuevos.

Es el entorno de pruebas para el modo tiempo real: permite probar un agente que vuelve a
buscar periódicamente sin depender de la API de X. Por defecto el reloj arranca en el
mensaje más antiguo.

```python
source = ReplaySource("data/sample/tweets.csv")
source.advance(timedelta(days=2))
source.search(["debate"])  # solo mensajes de los dos primeros días
```

## Para agregar una fuente (p. ej. la API de X)

1. Crear `sources/x_api.py` con una clase que tenga `search(keywords, since, until, limit)` y
   devuelva `list[Tweet]`.
2. Exportarla en `sources/__init__.py`.
3. Pasarla a `run_analysis(..., source=MiFuente())` o elegirla desde la configuración.
