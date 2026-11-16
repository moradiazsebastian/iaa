"use client";

import { useState, type FormEvent } from "react";
import { ArrowRight, ChevronDown, Sparkles } from "lucide-react";
import type { AnalysisOptions, AnalysisRequest } from "@/lib/types";

interface AnalysisFormProps {
  options?: AnalysisOptions;
  isRunning: boolean;
  onSubmit: (request: AnalysisRequest) => Promise<void>;
}

const fallbackMethods = ["kmeans", "lda"];

export function AnalysisForm({ options, isRunning, onSubmit }: AnalysisFormProps) {
  const [theme, setTheme] = useState("Elecciones presidenciales");
  const [keywords, setKeywords] = useState("debate, encuesta, fraude, voto, inflacion, candidato");
  const [method, setMethod] = useState("kmeans");
  const [nTopics, setNTopics] = useState("4");
  const [nSubtopics, setNSubtopics] = useState("2");
  const [depth, setDepth] = useState("2");
  const [maxTweets, setMaxTweets] = useState("2000");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [useLlm, setUseLlm] = useState(false);
  const [evaluate, setEvaluate] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);

  const methods = options?.methods.length ? options.methods : fallbackMethods;
  const canUseLlm = options?.llm_available === true;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isRunning) return;
    setFormError(null);

    const normalizedTheme = theme.trim();
    const keywordList = keywords
      .split(/[\n,]/)
      .map((keyword) => keyword.trim())
      .filter(Boolean);

    if (normalizedTheme.length < 2) {
      setFormError("La temática debe tener al menos 2 caracteres.");
      return;
    }

    if (since && until && since > until) {
      setFormError("La fecha de inicio no puede ser posterior a la fecha de cierre.");
      return;
    }

    if (!useLlm && keywordList.length === 0) {
      setFormError("Agregá al menos una palabra clave para analizar sin IA.");
      return;
    }

    await onSubmit({
      theme: normalizedTheme,
      keywords: keywordList.length ? keywordList : null,
      method,
      n_topics: nTopics ? Number(nTopics) : null,
      n_subtopics: nSubtopics ? Number(nSubtopics) : null,
      depth: Number(depth),
      max_tweets: Number(maxTweets),
      since: since || null,
      until: until || null,
      use_llm: useLlm,
      evaluate,
    });
  }

  return (
    <section className="config-card" id="nuevo-analisis" aria-labelledby="config-title">
      <div className="card-heading">
        <div>
          <p className="section-kicker">01 / CONFIGURACIÓN</p>
          <h2 id="config-title">Definí la escucha</h2>
        </div>
        <span className="config-icon" aria-hidden="true">
          <Sparkles />
        </span>
      </div>

      <form className="analysis-form" onSubmit={handleSubmit}>
        <div className="field-block">
          <label htmlFor="theme">Temática</label>
          <input
            id="theme"
            name="theme"
            type="text"
            autoComplete="off"
            maxLength={200}
            minLength={2}
            required
            value={theme}
            onChange={(event) => setTheme(event.target.value)}
            placeholder="Ej. transporte público en Buenos Aires"
          />
          <p className="field-hint">¿Qué conversación querés entender?</p>
        </div>

        <div className="field-block">
          <label htmlFor="keywords">Palabras clave</label>
          <textarea
            id="keywords"
            name="keywords"
            rows={3}
            value={keywords}
            onChange={(event) => setKeywords(event.target.value)}
            placeholder="Separadas por coma: debate, encuesta, voto"
            aria-describedby="keywords-hint"
          />
          <p className="field-hint" id="keywords-hint">
            Separalas con coma. La IA también puede sugerirlas.
          </p>
        </div>

        <label className={`llm-choice${canUseLlm ? "" : " is-disabled"}`}>
          <span className="toggle-wrap">
            <input
              type="checkbox"
              checked={useLlm}
              onChange={(event) => setUseLlm(event.target.checked)}
              disabled={!canUseLlm || isRunning}
              aria-label="Usar IA para nombrar y refinar los temas"
            />
            <span className="toggle-track" aria-hidden="true" />
          </span>
          <span className="llm-copy">
            <strong>Refinar con IA</strong>
            <span>
              {canUseLlm
                ? `${options?.llm_provider} · ${options?.llm_model}`
                : "No hay un proveedor de IA disponible"}
            </span>
          </span>
          <Sparkles className="llm-sparkle" aria-hidden="true" />
        </label>

        <details className="advanced-options">
          <summary>
            <span>Parámetros avanzados</span>
            <ChevronDown aria-hidden="true" />
          </summary>
          <div className="advanced-grid">
            <div className="field-block">
              <label htmlFor="method">Método de agrupamiento</label>
              <select id="method" value={method} onChange={(event) => setMethod(event.target.value)}>
                {methods.map((value) => (
                  <option key={value} value={value}>
                    {value === "kmeans" ? "K-means" : value === "lda" ? "LDA" : "BERTopic"}
                  </option>
                ))}
              </select>
            </div>

            <div className="field-block">
              <label htmlFor="depth">Profundidad</label>
              <select id="depth" value={depth} onChange={(event) => setDepth(event.target.value)}>
                <option value="1">1 nivel · temas</option>
                <option value="2">2 niveles · temas y subtemas</option>
                <option value="3">3 niveles · más detalle</option>
              </select>
            </div>

            <div className="field-block">
              <label htmlFor="n-topics">Cantidad de temas</label>
              <input
                id="n-topics"
                type="number"
                min={2}
                max={15}
                value={nTopics}
                onChange={(event) => setNTopics(event.target.value)}
                placeholder="Automático"
              />
            </div>

            <div className="field-block">
              <label htmlFor="n-subtopics">Subtemas por tema</label>
              <input
                id="n-subtopics"
                type="number"
                min={2}
                max={10}
                value={nSubtopics}
                onChange={(event) => setNSubtopics(event.target.value)}
                placeholder="Automático"
                disabled={depth === "1"}
              />
            </div>

            <div className="field-block range-field">
              <label htmlFor="max-tweets">
                Mensajes a considerar <output htmlFor="max-tweets">{Number(maxTweets).toLocaleString("es-AR")}</output>
              </label>
              <input
                id="max-tweets"
                type="range"
                min={100}
                max={5000}
                step={100}
                value={maxTweets}
                onChange={(event) => setMaxTweets(event.target.value)}
              />
              <div className="range-labels" aria-hidden="true"><span>100</span><span>5.000</span></div>
            </div>

            <div className="date-range">
              <div className="field-block">
                <label htmlFor="since">Desde</label>
                <input id="since" type="date" value={since} onChange={(event) => setSince(event.target.value)} />
              </div>
              <div className="field-block">
                <label htmlFor="until">Hasta</label>
                <input id="until" type="date" value={until} onChange={(event) => setUntil(event.target.value)} />
              </div>
            </div>
          </div>
        </details>

        <label className="evaluate-choice">
          <input
            type="checkbox"
            checked={evaluate}
            onChange={(event) => setEvaluate(event.target.checked)}
            disabled={!options?.dataset_has_labels}
          />
          <span>Comparar con etiquetas de referencia</span>
          {!options?.dataset_has_labels && <span className="muted-note">No disponible</span>}
        </label>

        {formError && <p className="form-error" role="alert">{formError}</p>}

        <button className="primary-button" type="submit" disabled={isRunning}>
          <span>{isRunning ? "Analizando conversación…" : "Iniciar análisis"}</span>
          {isRunning ? <span className="button-spinner" aria-hidden="true" /> : <ArrowRight aria-hidden="true" />}
        </button>
        <p className="privacy-note">Los resultados se mantienen en esta sesión; no se guarda un historial.</p>
      </form>
    </section>
  );
}
