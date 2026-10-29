# Datos

## `sample/tweets.csv` (incluido en el repo)

Dataset **sintético** de 360 mensajes en español generado con `foco make-sample`
(ver `src/foco_social/evaluation/synthetic.py`). Tiene tópicos y subtópicos conocidos sobre
una elección ficticia, más mensajes de fútbol que no deberían aparecer al buscar por la temática.
Sirve para probar el pipeline y para la CI. No contiene datos reales.

## Datos reales (no se versionan)

Los datos de X/Twitter y las etiquetas manuales **no se suben al repositorio** (términos de
uso de X y privacidad de los usuarios). Cada integrante los guarda localmente en `data/`
(todo lo que esté ahí, salvo `sample/`, está ignorado por git) y apunta a ellos con
`DATA_PATH` en `.env`.

<!-- TODO: indicar de dónde se descargan los datos etiquetados y quién da acceso. -->

## Formato esperado

CSV o Parquet con una fila por mensaje:

| columna            | tipo     | obligatoria | descripción                                   |
|--------------------|----------|-------------|-----------------------------------------------|
| `id`               | texto    | sí          | identificador único del mensaje               |
| `created_at`       | fecha    | sí          | fecha y hora de publicación                   |
| `author`           | texto    | sí          | usuario que publicó                           |
| `author_followers` | entero   | sí          | seguidores del autor                          |
| `text`             | texto    | sí          | contenido del mensaje                         |
| `likes`            | entero   | sí          | cantidad de likes                             |
| `retweets`         | entero   | sí          | cantidad de retweets                          |
| `topic`            | texto    | no          | etiqueta manual de tópico (solo evaluación)   |
| `subtopic`         | texto    | no          | etiqueta manual de subtópico (solo evaluación)|
