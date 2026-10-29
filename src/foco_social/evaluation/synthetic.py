"""Generador de un dataset sintético con tópicos y subtópicos conocidos.

Sirve para probar el pipeline sin datos reales y para evaluar etapas por separado.
Incluye mensajes de una temática distinta (fútbol) para que la búsqueda por keywords importe.
"""

import random
from datetime import datetime, timedelta

import pandas as pd

CANDIDATES = ["Martina Ríos", "Julián Paredes", "Carlos Benítez"]
PARTIES = ["Frente Renovador Federal", "Alianza Ciudadana", "Partido del Progreso"]
POLLSTERS = ["Opina Datos", "Consultora Federal", "Tendencias SA"]
PROVINCES = ["Córdoba", "Mendoza", "Santa Fe", "Salta", "Buenos Aires"]
TEAMS = ["Racing", "Independiente", "Talleres", "Lanús"]

TEMPLATES: dict[tuple[str, str, str], list[str]] = {
    ("politica", "Debate presidencial", "Desempeño de los candidatos"): [
        "Qué nervioso se lo vio a {cand} en el debate de anoche, no respondió nada",
        "{cand} ganó el debate presidencial, clarísimo. Los demás no tuvieron argumentos",
        "En el debate {cand} se la pasó atacando y no propuso nada #DebatePresidencial",
        "El cierre de {cand} en el debate fue lo mejor de la noche",
        "Terrible el papelón de {cand} en el debate, se olvidó lo que tenía que decir",
        "¿Alguien entendió qué quiso decir {cand} en el debate? Muy flojo el candidato",
    ],
    ("politica", "Debate presidencial", "Propuestas económicas en el debate"): [
        "En el debate {cand} prometió bajar impuestos pero no dijo cómo lo va a financiar",
        "La propuesta de dolarización de {cand} en el debate no cierra por ningún lado",
        "Lo único concreto del debate fue el plan fiscal de {cand} #DebatePresidencial",
        "Ningún candidato explicó en el debate cómo van a bajar el déficit",
        "{cand} habló de reforma tributaria en el debate, habrá que ver los números",
        "Las propuestas económicas del debate fueron puro humo, ningún plan serio",
    ],
    ("politica", "Encuestas", "Resultados de encuestas"): [
        "Nueva encuesta de {poll}: {cand} lidera con {pct}% de intención de voto",
        "Según {poll}, {cand} sube {small} puntos y se acerca al balotaje",
        "La encuesta de {poll} en {prov} da empate técnico entre {cand} y {cand2}",
        "Última encuesta antes de la veda: {cand} {pct}%, {cand2} {pct2}%",
        "{poll} muestra a {cand} primero en {prov} con {pct}% de los votos",
        "Encuesta: el {pct}% de los indecisos todavía no sabe a quién votar",
    ],
    ("politica", "Encuestas", "Críticas a encuestadoras"): [
        "Las encuestas otra vez le pifian, {poll} trabaja para el {party}",
        "No crean en las encuestas, en 2023 erraron por diez puntos",
        "¿Quién paga la encuesta de {poll}? Siempre favorece a {cand}",
        "Las encuestadoras como {poll} deberían publicar su metodología",
        "Encuestas truchas para instalar a {cand}, todos lo sabemos",
        "Muestra de 500 casos y quieren predecir una elección nacional. Encuestas berretas",
    ],
    ("politica", "Fraude y transparencia electoral", "Denuncias de fraude"): [
        "Denuncian fraude en mesas de {prov}: faltaban boletas del {party}",
        "Fiscales del {party} reportan irregularidades en el conteo de votos en {prov}",
        "Si pierde {cand} van a decir que hubo fraude, ya lo están instalando",
        "Videos de urnas abiertas en {prov}, la justicia electoral tiene que investigar el fraude",
        "El {party} presentó una denuncia por fraude ante la Cámara Electoral",
        "Hablar de fraude sin pruebas daña la democracia, {cand} debería saberlo",
    ],
    ("politica", "Fraude y transparencia electoral", "Voto electrónico"): [
        "El voto electrónico en {prov} funcionó sin problemas, filas cortas y rápido",
        "No confío en el voto electrónico, cualquier sistema se puede hackear",
        "Expertos en seguridad piden auditar el software del voto electrónico",
        "En {prov} hubo máquinas de voto electrónico que no arrancaban",
        "La boleta única en papel es más segura que el voto electrónico",
        "Primera vez con voto electrónico en {prov} y la verdad fue muy fácil votar",
    ],
    ("politica", "Economía en campaña", "Inflación"): [
        "Con esta inflación ningún candidato tiene un plan creíble para la campaña",
        "La inflación de {small}% mensual es el tema central de la campaña de {cand}",
        "{cand} promete inflación de un dígito en un año. Ya lo escuchamos antes",
        "Los precios del supermercado suben todas las semanas y la campaña habla de otra cosa",
        "El dato de inflación sale justo antes de las elecciones, impacto directo en el voto",
        "Inflación, inflación, inflación. Es lo único que le importa al votante",
    ],
    ("politica", "Economía en campaña", "Empleo y salarios"): [
        "{cand} propone una reforma laboral en la campaña, los sindicatos ya dicen que no",
        "Salarios por el piso y los candidatos discutiendo boludeces",
        "El desempleo en {prov} es del {small}%, que alguno de los candidatos lo mencione",
        "La campaña de {cand} promete un millón de empleos, ¿de dónde?",
        "Jubilados y salarios: el gran ausente en los spots de campaña",
        "Los trabajadores informales no aparecen en ninguna propuesta de los candidatos",
    ],
    ("futbol", "Fútbol", "Liga local"): [
        "Qué partido jugó {team}, golazo en el último minuto",
        "{team} no puede ganar de local hace cinco fechas, que se vaya el técnico",
        "El clásico entre {team} y {team2} fue durísimo, muchas amarillas",
        "Vamos {team}!!! A seguir sumando en la tabla",
        "El arbitraje en el partido de {team} fue un desastre, penal clarísimo no cobrado",
        "Mercado de pases: {team} busca un nueve para el próximo torneo",
    ],
}


def _fill(template: str, rng: random.Random) -> str:
    cand, cand2 = rng.sample(CANDIDATES, 2)
    team, team2 = rng.sample(TEAMS, 2)
    return template.format(
        cand=cand,
        cand2=cand2,
        party=rng.choice(PARTIES),
        poll=rng.choice(POLLSTERS),
        prov=rng.choice(PROVINCES),
        team=team,
        team2=team2,
        pct=rng.randint(25, 45),
        pct2=rng.randint(20, 40),
        small=rng.randint(2, 9),
    )


def generate(per_subtopic: int = 40, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    start = datetime(2026, 10, 1)
    authors = [f"usuario_{i:03d}" for i in range(150)]
    followers = {a: int(rng.lognormvariate(6, 1.6)) for a in authors}
    rows = []
    for (theme, topic, subtopic), templates in TEMPLATES.items():
        for _ in range(per_subtopic):
            text = _fill(rng.choice(templates), rng)
            if rng.random() < 0.3:
                text += rng.choice([" 🤦", " 👏", " 😡", " !!", " ...", " jaja"])
            author = rng.choice(authors)
            rows.append(
                {
                    "created_at": start + timedelta(minutes=rng.randint(0, 7 * 24 * 60)),
                    "author": author,
                    "author_followers": followers[author],
                    "text": text,
                    "likes": min(int(rng.paretovariate(1.2)) - 1, 20_000),
                    "retweets": min(int(rng.paretovariate(1.5)) - 1, 5_000),
                    "theme": theme,
                    "topic": topic,
                    "subtopic": subtopic,
                }
            )
    rng.shuffle(rows)
    df = pd.DataFrame(rows).sort_values("created_at", kind="stable").reset_index(drop=True)
    df.insert(0, "id", [f"t{i:05d}" for i in range(len(df))])
    return df
