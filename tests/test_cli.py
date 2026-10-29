import pandas as pd

from foco_social.cli import main


def test_compare_writes_one_row_per_method(sample_csv, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # runs/ se crea en una carpeta temporal
    monkeypatch.setenv("LLM_PROVIDER", "none")
    main(
        [
            "compare",
            "--theme", "elecciones",
            "--keywords", "debate,encuesta,fraude,voto,inflacion",
            "--methods", "kmeans,lda",
            "--llm", "off",
            "--topics", "3",
            "--data", str(sample_csv),
        ]
    )  # fmt: skip
    [run_dir] = (tmp_path / "runs").iterdir()
    results = pd.read_csv(run_dir / "results.csv")
    assert results["método"].tolist() == ["kmeans", "lda"]
    assert results["ARI"].between(-1, 1).all()
    assert (run_dir / "kmeans-sin-llm" / "eval.json").exists()
