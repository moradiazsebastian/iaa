"use client";

import { useState } from "react";
import useSWR from "swr";
import { Activity, ArrowDownRight, CircleAlert, RotateCw } from "lucide-react";
import { AnalysisForm } from "@/components/analysis-form";
import { ResultsPanel, type ResultsView } from "@/components/results-panel";
import { createAnalysis, errorMessage, fetchAnalysisOptions } from "@/lib/api";
import type { AnalysisRequest, AnalysisResult } from "@/lib/types";

export function AnalysisWorkspace() {
  const { data: options, error: optionsError, isLoading: isLoadingOptions, mutate: refreshOptions } = useSWR(
    "/api/options",
    fetchAnalysisOptions,
    { revalidateOnFocus: false, shouldRetryOnError: false },
  );
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<ResultsView>("topics");

  async function handleAnalysis(request: AnalysisRequest) {
    setIsRunning(true);
    setRunError(null);
    setSelectedPath(null);

    try {
      const nextResult = await createAnalysis(request);
      setResult(nextResult);
      setActiveView("topics");
    } catch (error) {
      setRunError(errorMessage(error));
    } finally {
      setIsRunning(false);
    }
  }

  const statusLabel = isLoadingOptions
    ? "Conectando con la API"
    : options
      ? `API activa · ${options.dataset}`
      : "API sin conexión";

  return (
    <div className="app-shell">
      <aside className="side-rail" aria-label="Navegación principal">
        <a className="brand" href="#inicio" aria-label="Foco Social, inicio">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span><strong>foco</strong><small>social listening</small></span>
        </a>

        <div className="rail-label">WORKSPACE</div>
        <nav className="side-nav">
          <a className="nav-link is-active" href="#nuevo-analisis"><span className="nav-mark" aria-hidden="true" />Nuevo análisis</a>
          <a className="nav-link" href="#resultados"><Activity aria-hidden="true" />Resultados</a>
          <a className="nav-link" href="#metodologia"><ArrowDownRight aria-hidden="true" />Cómo funciona</a>
        </nav>

        <div className="rail-bottom">
          <div className="dataset-card">
            <span className="dataset-indicator" aria-hidden="true" />
            <div>
              <span className="rail-label">FUENTE ACTUAL</span>
              <strong>{options?.dataset ?? "Dataset de muestra"}</strong>
              <small>{options?.dataset_has_labels ? "Con etiquetas de referencia" : "Mensajes disponibles para análisis"}</small>
            </div>
          </div>
          <span className="version-label">FOCO SOCIAL <span>·</span> 0.1</span>
        </div>
      </aside>

      <main className="dashboard" id="inicio">
        <header className="topbar">
          <div className="breadcrumbs"><span>Foco Social</span><span aria-hidden="true">/</span><strong>Espacio de análisis</strong></div>
          <div className="topbar-actions">
            <div className={`connection-status${options ? " is-connected" : optionsError ? " is-disconnected" : ""}`} role="status" aria-live="polite">
              <span className="connection-dot" aria-hidden="true" />{statusLabel}
            </div>
            {optionsError && (
              <button className="icon-button" type="button" onClick={() => void refreshOptions()} aria-label="Reintentar conexión con la API">
                <RotateCw aria-hidden="true" />
              </button>
            )}
          </div>
        </header>

        <div className="dashboard-content">
          <section className="hero-copy">
            <div className="hero-kicker"><span /> LABORATORIO DE CONVERSACIÓN</div>
            <h1>Encontrá las historias<br className="desktop-break" /> detrás del <em>ruido.</em></h1>
            <p>Explorá mensajes, descubrí temas y entendé qué conversaciones están marcando el pulso.</p>
          </section>

          {optionsError && (
            <div className="connection-alert" role="alert">
              <CircleAlert aria-hidden="true" />
              <div><strong>No pudimos conectar con la API.</strong><span>El formulario está listo; los resultados aparecerán cuando el servicio vuelva a responder.</span></div>
              <button type="button" onClick={() => void refreshOptions()}>Reintentar</button>
            </div>
          )}

          {runError && (
            <div className="run-alert" role="alert">
              <CircleAlert aria-hidden="true" />
              <span>{runError}</span>
              <button className="icon-button" type="button" onClick={() => setRunError(null)} aria-label="Cerrar mensaje"><span aria-hidden="true">×</span></button>
            </div>
          )}

          <div className="workspace-grid">
            <AnalysisForm options={options} isRunning={isRunning} onSubmit={handleAnalysis} />
            <ResultsPanel
              result={result}
              isRunning={isRunning}
              selectedPath={selectedPath}
              activeView={activeView}
              datasetHasLabels={options?.dataset_has_labels ?? false}
              onSelectPath={(path) => {
                setSelectedPath((current) => current === path ? null : path);
                setActiveView("messages");
              }}
              onChangeView={setActiveView}
              onClearFilter={() => setSelectedPath(null)}
            />
          </div>

          <section className="methodology-strip" id="metodologia" aria-labelledby="methodology-title">
            <div className="methodology-icon" aria-hidden="true"><Activity /></div>
            <div>
              <p className="section-kicker">MÉTODO</p>
              <h2 id="methodology-title">De una pregunta a un mapa de conversación.</h2>
              <p>Foco Social recupera mensajes del dataset, los agrupa en temas y subtemas, y estima cuánto representa cada conversación.</p>
            </div>
            <div className="method-steps" aria-label="Pasos del análisis">
              <span><b>01</b> Buscar</span><span><b>02</b> Agrupar</span><span><b>03</b> Interpretar</span>
            </div>
          </section>

          <footer className="page-footer">
            <span>FOCO SOCIAL · HERRAMIENTA DE INVESTIGACIÓN</span>
            <span>Los análisis se ejecutan sobre la fuente configurada en el servidor.</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
