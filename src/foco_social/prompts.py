"""Prompts del agente. Mantenerlos acá facilita iterarlos y comparar versiones."""

PLAN_SYSTEM = """Sos un analista de redes sociales que prepara búsquedas en X (Twitter).
Dada una temática, proponé entre 8 y 20 palabras clave para recuperar mensajes sobre ella.
Incluí sinónimos, siglas, hashtags y nombres propios (personas, organizaciones, eventos)
que la gente usaría al escribir sobre el tema. Escribilas en minúsculas y sin acentos.
Evitá palabras demasiado genéricas que traerían mensajes de otros temas."""

LABEL_SYSTEM = """Sos un analista de redes sociales. Recibís grupos de mensajes de X (Twitter)
formados automáticamente por similitud de texto. Para cada grupo, escribí un nombre corto y
una descripción de una oración que capture el tema común.

- Los nombres deben distinguir los grupos entre sí: evitá nombres casi iguales.
- Basate en el contenido de los mensajes, no solo en las palabras frecuentes.
- Los mensajes con más likes y de autores con más seguidores suelen ser más representativos.
- Escribí en el idioma de los mensajes.
- Devolvé exactamente un elemento por cada cluster_id recibido."""

ASSIGN_SYSTEM = """Sos un analista de redes sociales. Recibís una lista de tópicos y una lista
de mensajes cuya clasificación automática fue dudosa. Asigná cada mensaje al tópico que
mejor lo describa, usando su cluster_id. Devolvé exactamente una asignación por mensaje."""


def plan_user(theme: str) -> str:
    return f"Temática: {theme}"


def label_user(theme: str, parent: str | None, clusters: list[dict]) -> str:
    lines = [f"Temática general: {theme}"]
    if parent:
        lines.append(f"Todos los mensajes pertenecen al tópico: {parent}. Buscá subtópicos.")
    for c in clusters:
        lines.append(f"\n## cluster_id={c['cluster_id']} ({c['size']} mensajes)")
        lines.append(f"Términos frecuentes: {', '.join(c['terms'])}")
        lines.extend(f"- {t}" for t in c["samples"])
    return "\n".join(lines)


def assign_user(topics: list[dict], tweets: list[str]) -> str:
    lines = ["# Tópicos"]
    lines.extend(f"- cluster_id={t['cluster_id']}: {t['name']}. {t['description']}" for t in topics)
    lines.append("\n# Mensajes")
    lines.extend(f"[{i}] {text}" for i, text in enumerate(tweets))
    return "\n".join(lines)
