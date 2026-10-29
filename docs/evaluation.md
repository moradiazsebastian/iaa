# `evaluation/`: métricas y datos sintéticos

## `metrics.py`

### `compare(pred, gold) -> dict`

Compara dos formas de agrupar los mismos mensajes. Recibe dos `Series` indexadas por id de
mensaje y solo usa los ids que están en ambas. `foco eval` la usa contra las etiquetas
manuales y `foco repro` entre dos corridas.

| Métrica | Qué mide | Rango |
|---|---|---|
| `ari` (Adjusted Rand Index) | si los pares de mensajes que están juntos en uno también lo están en el otro, corregido por azar | 0 = azar, 1 = idénticos |
| `nmi` (Normalized Mutual Information) | cuánta información comparten las dos particiones | 0 a 1 |
| `matched_accuracy` | empareja tópicos predichos y reales 1 a 1 (algoritmo húngaro) y cuenta qué proporción de mensajes cae en su par | 0 a 1 |
| `matching` | el emparejamiento: `{tópico predicho: tópico real}` | |
| `n`, `n_pred`, `n_gold` | mensajes comparados y cantidad de tópicos de cada lado | |

Ninguna depende de los nombres: el tópico `"2"` puede corresponder a `"Encuestas"`.

**Ojo:** solo se evalúan los mensajes que el agente recuperó. Si la búsqueda deja afuera un
tópico entero, las métricas no lo reflejan.

### `level(paths, depth)`

Recorta paths jerárquicos a una profundidad: `"2.1.3"` → `"2.1"` con `depth=2`. Los mensajes
sin tópico quedan como `"(sin tópico)"`.

## `synthetic.py`

### `generate(per_subtopic=40, seed=42) -> DataFrame`

Genera mensajes en español con tópicos y subtópicos conocidos. Con el default son 360
mensajes. Lo usa `foco make-sample` y los tests.

- **`TEMPLATES`**: `{(temática, tópico, subtópico): [plantillas]}`. Las plantillas tienen
  huecos (`{cand}`, `{poll}`, `{prov}`, ...) que se completan al azar con `CANDIDATES`,
  `PARTIES`, `POLLSTERS`, `PROVINCES` y `TEAMS`.
- Hay 8 subtópicos de política (debate, encuestas, fraude, economía) y uno de fútbol, que
  hace de ruido: no debería aparecer al buscar por la temática política.
- Likes, retweets y seguidores siguen distribuciones de cola larga, como en redes reales.
- Las columnas `theme`, `topic` y `subtopic` son las etiquetas para evaluar.
- Con la misma semilla genera siempre el mismo dataset.

Para probar casos más difíciles, agregar plantillas o subtópicos en `TEMPLATES`. Por
ejemplo, mensajes que mezclan dos temas o usan ironía.
