"""Normalización y generación de Ground Truth sobre el dataset real de partidos de Boca Juniors.

Convierte los CSVs crudos descargados de twitterapi.io (`Datasets/Boca/<partido>/*.csv`) al
esquema requerido por `StaticSource` (`id`, `created_at`, `author`, `author_followers`, `text`,
`likes`, `retweets`) y etiqueta cada mensaje con:
- `is_relevant` (bool): True si habla del partido/Boca, False si es ruido colado en la captura.
- `topic` (str): Tópico de nivel 1 (5 tópicos por partido, o '(ruido)' si es irrelevante).
- `subtopic` (str): Subtópico de nivel 2 (2 por tópico relevante + 4 categorías de ruido).
"""

import ast
import json
import re
from pathlib import Path

import pandas as pd

BENCHMARK_MATCHES = [
    "2026-01-25-Deportivo Riestra",
    "2026-04-19-River Plate",
    "2026-05-19-Cruzeiro",
]

MATCH_SLUGS = {
    "2026-01-25-Deportivo Riestra": "riestra",
    "2026-04-19-River Plate": "river_plate",
    "2026-05-19-Cruzeiro": "cruzeiro",
}

MATCH_THEMES = {
    "2026-01-25-Deportivo Riestra": "Boca vs Deportivo Riestra Torneo Apertura",
    "2026-04-19-River Plate": "Superclásico River vs Boca en el Monumental",
    "2026-05-19-Cruzeiro": "Boca vs Cruzeiro Copa Libertadores",
}

OTHER_SPORTS_PATTERNS = [
    "super bowl",
    "new england",
    "foxborough",
    "wnba",
    "breanna stewart",
    "warriors",
    "timberwolves",
    "x games",
    "annika morgan",
    "celtics",
    "sixers",
    "thunder",
    "wrestle",
    "wwe",
    "knicks",
    "brunson",
    "donovan mitchell",
    "msg for game",
    "rally sudamericano",
    "vuelco fatal",
    "colisión del vehículo",
]

OTHER_FOOTBALL_PATTERNS = [
    "estrasburgo",
    "panichelli",
    "enciso",
    "ligue 1",
    "ligue1",
    "endrick",
    "parque de los príncipes",
    "lyon",
    "psg",
    "roma",
    "milan",
    "seriea",
    "juventus",
    "bologna",
    "thuram",
    "manninger",
    "betis",
    "pellegrini",
    "chimy ávila",
    "lucas boyé",
    "alavés",
    "chelsea",
    "anselmino",
    "enzo fernández",
    "lisandro martínez",
    "manchester united",
    "arsenal",
    "mosquera",
    "heinze",
    "emirates stadium",
    "donnarumma",
    "manchester city",
    "dibu martínez",
    "aston villa",
    "sunderland",
    "senesi",
    "guardiola",
    "neymar",
    "santos",
    "rodrygo",
    "real madrid",
    "mundial femenino",
    "mundial sub 17",
    "empleados de afa",
    "predio de ezeiza",
    "baliño",
    "lautaro martínez limpiando",
    "pastor maravilla",
    "lomónaco",
    "colegiales",
    "temperley",
    "aldosivi",
    "zaracho",
    "felipe anso",
    "costas",
    "zuculini",
    "milito entró al vestuario",
    "uno por uno de racing",
    "marco ruben",
    "rosario central",
    "universidad central",
    "canalla",
    "di maría",
    "cantizano",
    "facundo mallo",
    "independiente santa fe",
    "calamar",
    "augusto lotti",
    "rodallega",
    "scarpeta",
    "audax italiano",
    "barracas",
    "ahumada",
    "bruera",
    "montevideo city torque",
    "city torque",
    "salomón rodríguez",
    "goitía",
    "independiente rivadavia",
    "fluminense",
    "bolívar",
    "john kennedy",
    "always ready",
    "mirassol",
    "millonarios",
    "san pablo",
    "sao paulo",
    "deportivo cuenca",
    "recoleta",
    "américa de cali",
    "luifa artime",
    "cuti romero",
    "zelarayan",
    "jonathan spiff",
    "bragantino",
    "flamengo",
    "estudiantes de río cuarto",
    "sarmiento",
    "paternal",
    "passarella",
    "nacho fernández",
    "vaso de cerveza",
    "campeonato mineiro",
    "atlético mineiro",
    "olimpia",
    "guaraní",
    "cerro porteño",
    "defensores del chaco",
    "repechaje para el mundial",
    "santa cruz de la sierra",
    "christian gonzález",
]


def parse_author(raw: object) -> tuple[str, int]:
    """Extrae `(userName, followers)` del campo `author` serializado de twitterapi.io."""
    if not isinstance(raw, str):
        return ("unknown", 0)
    try:
        data = ast.literal_eval(raw)
        if isinstance(data, dict):
            user = str(data.get("userName") or data.get("name") or "unknown")
            followers = int(data.get("followers") or 0)
            return (user, followers)
    except (ValueError, SyntaxError, TypeError):
        pass
    return (raw if raw else "unknown", 0)


def check_relevance(text: str, author: str, match_name: str) -> tuple[bool, str]:
    """Determina si el mensaje pertenece al partido de Boca o es ruido colado en la captura."""
    clean = re.sub(r"https?://\S+", "", str(text or "")).strip()
    if not clean:
        return False, "Sin texto (solo link)"
    t = clean.lower()

    if author in {"DIRECTVLA", "radiofueguina"}:
        return False, "Noticias generales / soporte"
    if author == "espn":
        return False, "Otros deportes (NBA/NFL/etc.)"
    if author == "FlavioAzzaro":
        return False, "Otros partidos de fútbol"

    if any(p in t for p in OTHER_SPORTS_PATTERNS):
        return False, "Otros deportes (NBA/NFL/etc.)"
    if any(p in t for p in OTHER_FOOTBALL_PATTERNS):
        return False, "Otros partidos de fútbol"

    m_low = match_name.lower()
    if "riestra" in m_low:
        if ("audio del var" in t or "audio var" in t) and "river" in t:
            return False, "Otros partidos de fútbol"
        if "refuerzos a la par en san lorenzo" in t:
            return False, "Otros partidos de fútbol"
    elif "cruzeiro" in m_low:
        if any(w in t for w in ["riestra", "malevo", "platense", "tigre"]):
            return False, "Otros partidos de fútbol"
        if any(
            w in t
            for w in [
                "convocados de river",
                "lista de river",
                "jugadores citados de river",
                "exmediocampista del pirata",
            ]
        ):
            return False, "Otros partidos de fútbol"
        if "resultados, posiciones" in t and "boca" not in t:
            return False, "Otros partidos de fútbol"

    return True, ""


def classify_riestra(text: str) -> tuple[str, str]:
    """Taxonomía Ground Truth para Boca 1 - 0 Deportivo Riestra (2026-01-25)."""
    t = text.lower()
    if any(
        w in t
        for w in [
            "di lollo",
            "dilollo",
            "lollo",
            "goooo",
            "gol de boca",
            "1-0",
            "1 a 0",
            "abrió el marcador",
            "cabeza",
            "cabezazo",
        ]
    ):
        if any(
            w in t
            for w in ["paredes", "centro", "tiro libre", "fórmula", "pelota parada", "asistencia"]
        ):
            return ("Gol de Di Lollo y pelota parada", "Centro de Paredes y cabezazo de Di Lollo")
        return ("Gol de Di Lollo y pelota parada", "Festejo y repercusiones del 1-0 de Di Lollo")
    if "paredes" in t and any(
        w in t for w in ["centro", "tiro libre", "córner", "corner", "pegada", "remate"]
    ):
        return ("Gol de Di Lollo y pelota parada", "Centro de Paredes y cabezazo de Di Lollo")

    if any(
        w in t
        for w in [
            "anulado",
            "no vale",
            "no sumó",
            "mano",
            "var",
            "árbitro",
            "arbitro",
            "zunino",
            "amarilla",
            "amonestado",
            "falta",
            "infracción",
            "watson",
            "embistió",
            "chocar",
        ]
    ):
        if any(
            w in t
            for w in ["zeballos", "chango", "changuito", "anulado", "no vale", "no sumó", "mano"]
        ):
            return ("Polémicas, faltas y arbitraje", "Gol anulado a Zeballos por mano")
        return (
            "Polémicas, faltas y arbitraje",
            "Amonestados, faltas a Paredes y arbitraje de Zunino",
        )

    if any(
        w in t
        for w in [
            "janson",
            "zufiaurre",
            "delgado",
            "zenón",
            "zenon",
            "cambio",
            "cambios",
            "ingresó",
            "ingreso",
            "reemplazó",
            "afuera",
            "entra ",
            "sale ",
            "delantero",
            "sin 9",
            "nueve",
            "striker",
            "reforzar",
            "refuerzo",
            "mercado",
            "suplentes",
            "banco",
        ]
    ):
        if any(
            w in t
            for w in [
                "janson",
                "zufiaurre",
                "aplausos",
                "aplaudido",
                "ovación",
                "ovacionado",
                "pibe",
            ]
        ):
            return (
                "Cambios, delantera y armado del equipo",
                "Salida de Janson, aplausos y debut de Zufiaurre",
            )
        return (
            "Cambios, delantera y armado del equipo",
            "Variantes tácticas y reclamo por falta de delantero 9",
        )

    if any(
        w in t
        for w in [
            "marchesín",
            "marchesin",
            "arce",
            "atajad",
            "tapad",
            "arquero",
            "bracamonte",
            "belmonte",
            "toto",
            "velasco",
            "zeballos",
            "chango",
            "changuito",
            "blanco",
            "herrera",
            "úbeda",
            "ubeda",
            "sifonazo",
        ]
    ):
        if any(
            w in t
            for w in [
                "marchesín",
                "marchesin",
                "arce",
                "atajad",
                "tapad",
                "arquero",
                "bracamonte",
                "sifonazo",
            ]
        ):
            return ("Rendimiento individual y arqueros", "Atajadas clave de Marchesín y Nacho Arce")
        return (
            "Rendimiento individual y arqueros",
            "Nivel de Belmonte, Velasco, Zeballos y Blanco",
        )

    if any(
        w in t
        for w in [
            "ganó",
            "gano",
            "victoria",
            "triunfo",
            "final",
            "terminó",
            "termino",
            "arranque",
            "pie derecho",
            "tres puntos",
            "3 puntos",
            "win",
        ]
    ):
        return ("Cobertura y desarrollo del partido", "Cierre con victoria y análisis post-partido")
    return ("Cobertura y desarrollo del partido", "Previa, transmisión y minuto a minuto")


def classify_river(text: str) -> tuple[str, str]:
    """Taxonomía Ground Truth para River Plate 0 - 1 Boca Juniors (2026-04-19)."""
    t = text.lower()
    if any(
        w in t
        for w in [
            "topo gigio",
            "topogigio",
            "gigiazo",
            "riquelme",
            "festejo",
            "penal",
            "goooo",
            "gol de #boca",
            "gol de boca",
            "45+5",
            "ángulo",
            "angulo",
        ]
    ):
        if any(
            w in t
            for w in ["topo gigio", "topogigio", "gigiazo", "riquelme", "festejo", "silenciosa"]
        ):
            return (
                "Gol de Paredes y festejo Topo Gigio",
                "Festejo Topo Gigio de Paredes y Bareiro en el Monumental",
            )
        return ("Gol de Paredes y festejo Topo Gigio", "Ejecución de penal de Paredes para el 1-0")

    if any(
        w in t
        for w in [
            "herrera",
            "rivero",
            "amarilla",
            "amonestado",
            "expuls",
            "roja",
            "mano",
            "var",
            "árbitro",
            "arbitro",
            "acuña",
            "acuna",
            "simular",
            "agarrones",
            "doble castigo",
        ]
    ):
        if any(
            w in t for w in ["rivero", "mano", "segunda amarilla", "roja", "echa", "doble castigo"]
        ):
            return (
                "Polémicas arbitrales y tarjetas",
                "Mano de Rivero y reclamo de expulsión a Darío Herrera",
            )
        return ("Polémicas arbitrales y tarjetas", "Amonestados, cruces y protestas al arbitraje")

    if any(
        w in t
        for w in [
            "molestia",
            "lesión",
            "lesion",
            "isquiotibial",
            "driussi",
            "salas",
            "merentiel",
            "bestia",
            "zeballos",
            "chango",
            "beltrán",
            "beltran",
            "brey",
            "martínez quarta",
            "quarta",
            "aranda",
            "belmonte",
            "ander",
            "cambio",
            "cambios",
            "reemplazado",
            "di lollo",
            "ascacíbar",
            "ascacibar",
        ]
    ):
        if any(
            w in t
            for w in [
                "molestia",
                "lesión",
                "lesion",
                "isquiotibial",
                "driussi",
                "reemplazado",
                "pidió el cambio",
            ]
        ):
            return (
                "Lesiones, variantes y jugadas claras",
                "Salidas por lesión de Paredes y Driussi",
            )
        return (
            "Lesiones, variantes y jugadas claras",
            "Ocasiones de Merentiel, Salas, Zeballos y cambios",
        )

    if any(
        w in t
        for w in [
            "fuego",
            "incendio",
            "tribuna",
            "26/6",
            "2011",
            "chango más",
            "chango mas",
            "playa",
            "gallina",
            "hijos",
            "paternidad",
            "silbatina",
            "silbidos",
            "muda",
            "amarga",
            "papelitos",
            "bandera",
            "beto alonso",
            "barovero",
            "weigandt",
        ]
    ):
        if any(
            w in t
            for w in [
                "fuego",
                "incendio",
                "tribuna",
                "26/6",
                "2011",
                "silbatina",
                "silbidos",
                "bandera",
                "papelitos",
            ]
        ):
            return (
                "Clima en el Monumental y folclore",
                "Foco de fuego en la tribuna, recibimiento y silbidos",
            )
        return ("Clima en el Monumental y folclore", "Chicanas, festejos xeneizes y paternidad")

    if any(
        w in t
        for w in [
            "ganó",
            "gano",
            "ganooo",
            "victoria",
            "triunfo",
            "final",
            "terminó",
            "1-0",
            "0-1",
            "puntero",
            "coudet",
            "úbeda",
            "ubeda",
        ]
    ):
        return (
            "Cobertura y balance del Superclásico",
            "Triunfo xeneize 1-0 y repercusiones finales",
        )
    return ("Cobertura y balance del Superclásico", "Previa, formaciones y transmisión en vivo")


def classify_cruzeiro(text: str) -> tuple[str, str]:
    """Taxonomía Ground Truth para Boca Juniors 1 - 1 Cruzeiro (2026-05-19)."""
    t = text.lower()
    if any(
        w in t
        for w in [
            "anulado",
            "anuló",
            "anulo",
            "delgado",
            "delgaod",
            "valenzuela",
            "var",
            "mano",
            "gerson",
            "expulsado",
            "roja",
            "amarilla",
            "amonestado",
            "árbitro",
            "arbitro",
            "venezolano",
            "robo",
            "insólito gol",
        ]
    ):
        if any(
            w in t
            for w in [
                "anulado",
                "anuló",
                "anulo",
                "delgado",
                "delgaod",
                "mano",
                "agónico",
                "agonico",
                "2-1",
            ]
        ):
            return (
                "Polémica VAR y arbitraje de Valenzuela",
                "Gol agónico de Merentiel anulado por mano de Delgado",
            )
        return (
            "Polémica VAR y arbitraje de Valenzuela",
            "Expulsión de Gerson, tarjetas y críticas al VAR",
        )

    if any(
        w in t
        for w in [
            "merentiel",
            "bestia",
            "goooo",
            "gol de #boca",
            "gol de boca",
            "1-0",
            "1 a 0",
            "kung fu",
            "centro de paredes",
            "centrazo",
            "fagner",
            "fágner",
            "empate",
            "empató",
            "1-1",
            "gol de cruzeiro",
        ]
    ):
        if any(
            w in t
            for w in ["fagner", "fágner", "empate", "empató", "1-1", "gol de cruzeiro", "lo ganaba"]
        ):
            return (
                "Goles del partido (1-1)",
                "Gol de Fagner y empate de Cruzeiro en el segundo tiempo",
            )
        return ("Goles del partido (1-1)", "Gol de Merentiel tras centro de Paredes para el 1-0")

    if any(
        w in t
        for w in [
            "brey",
            "kaio jorge",
            "mano a mano",
            "otávio",
            "otavio",
            "zeballos",
            "chango",
            "belmonte",
            "giménez",
            "gimenez",
            "romero",
            "aranda",
            "hidratación",
            "rehidratación",
            "cambio",
            "cambios",
            "pereira",
            "lateral",
        ]
    ):
        if any(
            w in t
            for w in ["brey", "kaio jorge", "mano a mano", "otávio", "otavio", "arquero", "aranda"]
        ):
            return (
                "Desarrollo del juego, arqueros y variantes",
                "Atajada de Brey a Kaio Jorge y llegadas claras",
            )
        return (
            "Desarrollo del juego, arqueros y variantes",
            "Modificaciones tácticas, ingresos y pausa de hidratación",
        )

    if any(
        w in t
        for w in [
            "torreira",
            "padre de paredes",
            "seguirá en boca",
            "católica",
            "catolica",
            "clasificación",
            "clasificacion",
            "ayrton costa",
            "bombonera",
            "noche de copa",
        ]
    ):
        if any(
            w in t
            for w in [
                "torreira",
                "padre de paredes",
                "seguirá en boca",
                "bombonera",
                "noche de copa",
            ]
        ):
            return (
                "Clima de Copa, figuras y clasificación",
                "Visita de Torreira, familia Paredes y noche de Bombonera",
            )
        return (
            "Clima de Copa, figuras y clasificación",
            "Panorama de clasificación ante Universidad Católica",
        )

    if any(
        w in t
        for w in [
            "formación",
            "formacion",
            "once",
            "titulares",
            "suplentes",
            "previa",
            "arrancó",
            "ya juegan",
        ]
    ):
        return ("Cobertura y transmisión de Copa", "Previa y formaciones confirmadas")
    return ("Cobertura y transmisión de Copa", "Relato minuto a minuto y cierre de transmisión")


def classify_generic_boca(text: str) -> tuple[str, str]:
    """Clasificador de respaldo para otros partidos de Boca fuera de los 3 principales."""
    t = text.lower()
    if any(w in t for w in ["goooo", "gol de", "penal", "1-0", "2-0", "1-1", "2-1"]):
        return ("Goles y definiciones", "Goles y festejos del partido")
    if any(
        w in t
        for w in [
            "var",
            "árbitro",
            "arbitro",
            "amarilla",
            "roja",
            "amonestado",
            "expulsado",
            "mano",
            "falta",
        ]
    ):
        return ("Arbitraje y tarjetas", "Polémicas, faltas y amonestados")
    if any(
        w in t
        for w in ["cambio", "ingresó", "reemplazó", "lesión", "molestia", "suplentes", "formación"]
    ):
        return ("Formación y cambios", "Alineación, variantes y estado físico")
    if any(w in t for w in ["atajad", "tapad", "arquero", "figura", "partidazo", "jugó"]):
        return ("Rendimiento individual", "Actuación de jugadores y arqueros")
    return ("Cobertura y minuto a minuto", "Transmisión, previa y resultado final")


CLASSIFIERS = {
    "2026-01-25-Deportivo Riestra": classify_riestra,
    "2026-04-19-River Plate": classify_river,
    "2026-05-19-Cruzeiro": classify_cruzeiro,
}


def normalize_boca_folder(folder_path: str | Path, label_ground_truth: bool = True) -> pd.DataFrame:
    """Lee y normaliza todos los CSVs de una carpeta de partido de Boca."""
    folder = Path(folder_path)
    csv_files = sorted(folder.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No se encontraron archivos CSV en {folder}")

    raw_df = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
    raw_df["id"] = raw_df["id"].astype(str)
    raw_df = raw_df.drop_duplicates(subset=["id"]).reset_index(drop=True)

    authors_parsed = raw_df["author"].apply(parse_author)
    created_at = pd.to_datetime(
        raw_df["createdAt"],
        format="%a %b %d %H:%M:%S %z %Y",
        utc=True,
        errors="coerce",
    )
    # Fallback en caso de otro formato de fecha
    if created_at.isna().any():
        created_at = created_at.fillna(
            pd.to_datetime(raw_df["createdAt"], utc=True, errors="coerce")
        )

    df = pd.DataFrame(
        {
            "id": raw_df["id"],
            "created_at": created_at.dt.strftime("%Y-%m-%d %H:%M:%S"),
            "author": [a[0] for a in authors_parsed],
            "author_followers": [a[1] for a in authors_parsed],
            "text": raw_df["text"].fillna("").astype(str),
            "likes": raw_df["likeCount"].fillna(0).astype(int),
            "retweets": raw_df["retweetCount"].fillna(0).astype(int),
            "lang": raw_df["lang"].fillna("und").astype(str) if "lang" in raw_df else "und",
            "match": folder.name,
        }
    )

    if label_ground_truth:
        classifier = CLASSIFIERS.get(folder.name, classify_generic_boca)
        is_rel_list, topics, subtopics = [], [], []
        for row in df.itertuples(index=False):
            is_rel, noise_sub = check_relevance(row.text, row.author, folder.name)
            is_rel_list.append(is_rel)
            if not is_rel:
                topics.append("(ruido)")
                subtopics.append(noise_sub)
            else:
                top, sub = classifier(row.text)
                topics.append(top)
                subtopics.append(sub)
        df["is_relevant"] = is_rel_list
        df["topic"] = topics
        df["subtopic"] = subtopics

    return df.sort_values(["created_at", "id"], kind="stable").reset_index(drop=True)


def build_boca_benchmark(
    boca_root: str | Path,
    out_dir: str | Path = Path("data/benchmark"),
    matches: list[str] | None = None,
) -> dict[str, Path]:
    """Construye los datasets normalizados y etiquetados para el Benchmark.

    Genera por cada partido:
    - `<slug>.csv`: todos los mensajes (relevantes + ruido) para evaluar Suite A (Relevancia) y E2E.
    - `<slug>_relevant.csv`: solo los mensajes con `is_relevant=True` para evaluar Suite B y C.
    Y un archivo consolidado `boca_benchmark_all.csv` + `summary.json`.
    """
    boca_root = Path(boca_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    matches = matches or BENCHMARK_MATCHES

    paths: dict[str, Path] = {}
    frames: list[pd.DataFrame] = []
    summary: dict[str, dict] = {}

    for match_name in matches:
        folder = boca_root / match_name
        df = normalize_boca_folder(folder, label_ground_truth=True)
        slug = MATCH_SLUGS.get(
            match_name, re.sub(r"[^a-z0-9]+", "_", match_name.lower()).strip("_")
        )

        full_path = out_dir / f"{slug}.csv"
        rel_path = out_dir / f"{slug}_relevant.csv"
        df.to_csv(full_path, index=False, encoding="utf-8")
        df_rel = df[df["is_relevant"]].reset_index(drop=True)
        df_rel.to_csv(rel_path, index=False, encoding="utf-8")

        paths[slug] = full_path
        paths[f"{slug}_relevant"] = rel_path
        frames.append(df)

        summary[match_name] = {
            "slug": slug,
            "theme": MATCH_THEMES.get(match_name, f"Boca {match_name}"),
            "total_tweets": len(df),
            "relevant_tweets": int(df["is_relevant"].sum()),
            "noise_tweets": int((~df["is_relevant"]).sum()),
            "noise_ratio": round(float((~df["is_relevant"]).mean()), 4),
            "n_topics": int(df_rel["topic"].nunique()),
            "n_subtopics": int((df_rel["topic"] + " / " + df_rel["subtopic"]).nunique()),
            "topics": df_rel["topic"].value_counts().to_dict(),
            "noise_breakdown": df[~df["is_relevant"]]["subtopic"].value_counts().to_dict(),
        }

    all_df = pd.concat(frames, ignore_index=True)
    all_path = out_dir / "boca_benchmark_all.csv"
    all_df.to_csv(all_path, index=False, encoding="utf-8")
    paths["all"] = all_path

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    paths["summary"] = summary_path
    return paths
