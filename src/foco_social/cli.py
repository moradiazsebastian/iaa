"""Línea de comandos: foco run | eval | repro | compare | make-sample."""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from foco_social.config import Settings, get_settings
from foco_social.evaluation.metrics import compare, level
from foco_social.graph.nodes import plan_keywords
from foco_social.llm import LLM
from foco_social.runner import AnalysisResult, run_analysis, save_run
from foco_social.sources import StaticSource

log = logging.getLogger("foco_social")
METHODS = ["kmeans", "lda", "bertopic"]


def main(argv: list[str] | None = None) -> None:
    load_dotenv()  # exporta .env al entorno (API keys, LANGSMITH_*)
    parser = _build_parser()
    args = parser.parse_args(argv)
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="foco", description="Detección de tópicos con LLMs")
    sub = parser.add_subparsers(required=True)

    analysis = argparse.ArgumentParser(add_help=False)
    analysis.add_argument("--theme", required=True, help="Temática a analizar")
    analysis.add_argument(
        "--keywords", help="Keywords separadas por coma (si no, las propone el LLM)"
    )
    analysis.add_argument("--topics", type=int, help="Cantidad de tópicos (default: automática)")
    analysis.add_argument(
        "--subtopics", type=int, help="Subtópicos por tópico (default: automática)"
    )
    analysis.add_argument("--depth", type=int, default=2, help="1 = tópicos, 2 = + subtópicos")
    analysis.add_argument("--max-tweets", type=int, default=2000)
    analysis.add_argument("--since", type=datetime.fromisoformat)
    analysis.add_argument("--until", type=datetime.fromisoformat)
    analysis.add_argument("--data", type=Path, help="Dataset (pisa DATA_PATH)")
    analysis.add_argument("--provider", help="Proveedor de LLM (pisa LLM_PROVIDER)")
    analysis.add_argument("--model", help="Modelo (pisa LLM_MODEL)")

    single = argparse.ArgumentParser(add_help=False)
    single.add_argument("--method", choices=METHODS, help="Método de tópicos (pisa TOPIC_MODEL)")

    p = sub.add_parser(
        "run", parents=[analysis, single], help="Ejecuta el análisis y guarda el reporte"
    )
    p.set_defaults(func=cmd_run)

    p = sub.add_parser(
        "eval", parents=[analysis, single], help="Ejecuta y compara contra etiquetas manuales"
    )
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser(
        "repro", parents=[analysis, single], help="Ejecuta dos veces sin caché y compara"
    )
    p.set_defaults(func=cmd_repro)

    p = sub.add_parser(
        "compare",
        parents=[analysis],
        help="Evalúa cada método de tópicos con y sin LLM, sobre los mismos mensajes",
    )
    p.add_argument("--methods", default=",".join(METHODS), help="Métodos separados por coma")
    p.add_argument(
        "--llm", choices=["both", "on", "off"], default="both", help="Con LLM, sin LLM o ambos"
    )
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("make-sample", help="Genera el dataset sintético de ejemplo")
    p.add_argument("--out", type=Path, default=Path("data/sample/tweets.csv"))
    p.add_argument("--per-subtopic", type=int, default=40)
    p.add_argument("--seed", type=int, default=42)
    p.set_defaults(func=cmd_make_sample)
    return parser


# --- Comandos -------------------------------------------------------------------


def cmd_run(args) -> None:
    settings = _settings(args)
    run_dir = _start_run(settings, args.theme, "run")
    result = _analyze(args, settings)
    save_run(result, settings, run_dir)
    print((run_dir / "report.md").read_text(encoding="utf-8"))
    print(f"Resultados en {run_dir}")


def cmd_eval(args) -> None:
    settings = _settings(args)
    gold = StaticSource(settings.data_path).labels()
    if gold is None:
        sys.exit("El dataset no tiene columna 'topic': no hay etiquetas para evaluar.")
    run_dir = _start_run(settings, args.theme, "eval")
    result = _analyze(args, settings)
    save_run(result, settings, run_dir)
    metrics = _evaluate(result, gold, args.depth)
    (run_dir / "eval.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), "utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"Resultados en {run_dir}")


def cmd_repro(args) -> None:
    settings = _settings(args, llm_cache=False)
    run_dir = _start_run(settings, args.theme, "repro")
    runs = []
    for i in (1, 2):
        log.info("Corrida %d de 2", i)
        result = _analyze(args, settings)
        save_run(result, settings, run_dir / f"run{i}")
        runs.append(result.assignments_frame().set_index("id")["topic_path"])

    metrics = {
        "topics": compare(level(runs[0], 1), level(runs[1], 1)),
        "full": compare(runs[0], runs[1]),
        "same_tweets": set(runs[0].index) == set(runs[1].index),
    }
    (run_dir / "repro.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), "utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"Resultados en {run_dir}")


def cmd_compare(args) -> None:
    """Grilla método × (con / sin LLM). Todas las celdas usan las mismas keywords y mensajes."""
    base = _settings(args)
    gold = StaticSource(base.data_path).labels()
    if gold is None:
        sys.exit("El dataset no tiene columna 'topic': no hay etiquetas para evaluar.")
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    unknown = set(methods) - set(METHODS)
    if unknown:
        sys.exit(f"Métodos desconocidos: {', '.join(sorted(unknown))}")
    llm_modes = {"both": [False, True], "on": [True], "off": [False]}[args.llm]
    if True in llm_modes and base.llm_provider == "none":
        sys.exit("--llm on/both requiere un proveedor de LLM (LLM_PROVIDER o --provider)")

    run_dir = _start_run(base, args.theme, "compare")
    keywords = (
        [k.strip() for k in args.keywords.split(",")]
        if args.keywords
        else plan_keywords(args.theme, LLM(base))
    )
    log.info("Keywords compartidas por todas las celdas: %s", keywords)

    rows = []
    for method in methods:
        for use_llm in llm_modes:
            cell = f"{method}-{'llm' if use_llm else 'sin-llm'}"
            log.info("=== %s ===", cell)
            settings = base.model_copy(
                update={
                    "topic_model": method,
                    "llm_provider": base.llm_provider if use_llm else "none",
                }
            )
            row = {"método": method, "llm": settings.llm_model if use_llm else "-"}
            try:
                result = _analyze(args, settings, keywords=keywords)
            except ImportError as e:
                log.warning("%s omitido: %s", cell, e)
                rows.append({**row, "error": str(e)})
                continue
            save_run(result, settings, run_dir / cell)
            metrics = _evaluate(result, gold, args.depth)
            (run_dir / cell / "eval.json").write_text(
                json.dumps(metrics, indent=2, ensure_ascii=False), "utf-8"
            )
            row.update(
                {
                    "mensajes": result.stats["n_tweets"],
                    "tópicos": sum(t.level == 1 for t in result.topics),
                    "ARI": metrics["topics"]["ari"],
                    "NMI": metrics["topics"]["nmi"],
                    "acc": metrics["topics"]["matched_accuracy"],
                }
            )
            if "subtopics" in metrics:
                row.update(
                    {
                        "ARI sub": metrics["subtopics"]["ari"],
                        "NMI sub": metrics["subtopics"]["nmi"],
                        "acc sub": metrics["subtopics"]["matched_accuracy"],
                    }
                )
            row.update(
                {"segundos": result.stats["seconds"], "llamadas LLM": result.stats["llm_calls"]}
            )
            rows.append(row)

    table = pd.DataFrame(rows)
    table.to_csv(run_dir / "results.csv", index=False, encoding="utf-8")
    markdown = _markdown_table(table)
    (run_dir / "results.md").write_text(
        f"# Comparación: {args.theme}\n\nKeywords: {', '.join(keywords)}\n\n{markdown}\n", "utf-8"
    )
    print(markdown)
    print(f"Resultados en {run_dir}")


def cmd_make_sample(args) -> None:
    from foco_social.evaluation.synthetic import generate

    df = generate(per_subtopic=args.per_subtopic, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8")
    print(f"{len(df)} mensajes guardados en {args.out}")


# --- Auxiliares -----------------------------------------------------------------


def _settings(args, **overrides) -> Settings:
    return get_settings(
        data_path=args.data,
        llm_provider=args.provider,
        llm_model=args.model,
        topic_model=getattr(args, "method", None),
        **overrides,
    )


def _analyze(args, settings: Settings, keywords: list[str] | None = None) -> AnalysisResult:
    if keywords is None and args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]
    return run_analysis(
        settings,
        theme=args.theme,
        keywords=keywords,
        n_topics=args.topics,
        n_subtopics=args.subtopics,
        depth=args.depth,
        max_tweets=args.max_tweets,
        since=args.since,
        until=args.until,
    )


def _evaluate(result: AnalysisResult, gold: pd.DataFrame, depth: int) -> dict:
    """Métricas de tópicos (y subtópicos si corresponde) contra las etiquetas manuales."""
    pred = result.assignments_frame().set_index("id")["topic_path"]
    metrics = {"topics": compare(level(pred, 1), gold["topic"])}
    if gold["subtopic"].notna().any() and depth >= 2:
        gold_sub = gold["topic"] + " / " + gold["subtopic"].fillna("")
        metrics["subtopics"] = compare(level(pred, 2), gold_sub)
    names = result.topic_names()
    for m in metrics.values():
        m["matching"] = {f"{k} {names.get(k, '')}".strip(): v for k, v in m["matching"].items()}
    return metrics


def _markdown_table(df: pd.DataFrame) -> str:
    df = df.fillna("")
    lines = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def _start_run(settings: Settings, theme: str, kind: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", theme.lower()).strip("-")[:40]
    run_dir = settings.runs_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{kind}-{slug}"
    run_dir.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(level=logging.WARNING, format=fmt)
    log.setLevel(logging.INFO)
    handler = logging.FileHandler(run_dir / "run.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter(fmt))
    log.addHandler(handler)
    log.info(
        "Run %s · método=%s proveedor=%s modelo=%s",
        run_dir.name,
        settings.topic_model,
        settings.llm_provider,
        settings.llm_model,
    )
    return run_dir


if __name__ == "__main__":
    main()
