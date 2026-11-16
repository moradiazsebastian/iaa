"use client";

import { Activity, ArrowUpRight, Clock3, MessageSquareText, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import type { AnalysisResult } from "@/lib/types";
import { formatNumber, formatSeconds } from "@/lib/format";
import { AssignmentTable } from "@/components/assignment-table";
import { MetricsPanel } from "@/components/metrics-panel";
import { TopicTree } from "@/components/topic-tree";

export type ResultsView = "topics" | "messages" | "quality";

interface ResultsPanelProps {
  result: AnalysisResult | null;
  isRunning: boolean;
  selectedPath: string | null;
  activeView: ResultsView;
  datasetHasLabels: boolean;
  onSelectPath: (path: string) => void;
  onChangeView: (view: ResultsView) => void;
  onClearFilter: () => void;
}

export function ResultsPanel({
  result,
  isRunning,
  selectedPath,
  activeView,
  datasetHasLabels,
  onSelectPath,
  onChangeView,
  onClearFilter,
}: ResultsPanelProps) {
  return (
    <section className="results-card" id="resultados" aria-labelledby="results-title">
      <div className="results-heading">
        <div>
          <p className="section-kicker">02 / HALLAZGOS</p>
          <h2 id="results-title">Resultados</h2>
        </div>
        {result && (
          <a className="text-link" href="#nuevo-analisis">
            Nuevo análisis <ArrowUpRight className="link-arrow" aria-hidden="true" />
          </a>
        )}
      </div>

      {isRunning ? (
        <div className="running-state" role="status" aria-live="polite">
          <div className="signal-visual" aria-hidden="true">
            <span /><span /><span /><span /><span />
          </div>
          <div>
            <p className="section-kicker">TRABAJANDO</p>
            <h3>Buscando patrones en la conversación</h3>
            <p>El agente está agrupando mensajes y preparando los temas. Puede tardar unos minutos.</p>
          </div>
          <span className="button-spinner" aria-hidden="true" />
        </div>
      ) : !result ? (
        <div className="empty-results">
          <div className="empty-art" aria-hidden="true">
            <div className="empty-orbit"><Activity /></div>
            <span className="empty-dot dot-one" /><span className="empty-dot dot-two" /><span className="empty-dot dot-three" />
            <div className="empty-bars"><i /><i /><i /><i /><i /></div>
          </div>
          <p className="section-kicker">EL ESPACIO ESTÁ LISTO</p>
          <h3>Convertí ruido en señales.</h3>
          <p>Elegí una temática y ejecutá el primer análisis para ver qué historias están creciendo.</p>
          <a className="text-link" href="#nuevo-analisis">Configurar análisis <span aria-hidden="true">↗</span></a>
        </div>
      ) : (
        <>
          <div className="result-title-row">
            <div>
              <span className="result-chip"><span className="status-dot" /> ANÁLISIS COMPLETADO</span>
              <h3>{result.theme}</h3>
              <p className="result-meta">{result.method === "kmeans" ? "K-means" : result.method.toUpperCase()} · {result.llm ? `Refinado con ${result.llm}` : "Etiquetas por términos frecuentes"}</p>
            </div>
            <div className="result-stat-icon" aria-hidden="true"><Sparkles /></div>
          </div>

          <div className="stats-grid" aria-label="Resumen del análisis">
            <StatCard icon={<MessageSquareText aria-hidden="true" />} label="Mensajes" value={formatNumber(result.stats.n_tweets)} />
            <StatCard icon={<Activity aria-hidden="true" />} label="Temas" value={formatNumber(result.topics.filter((topic) => topic.level === 1).length)} />
            <StatCard icon={<Clock3 aria-hidden="true" />} label="Tiempo" value={formatSeconds(result.stats.seconds)} />
          </div>

          {result.keywords.length > 0 && (
            <div className="keyword-row">
              <span>ESCUCHA</span>
              <div>{result.keywords.map((keyword) => <span className="keyword-pill" key={keyword}>{keyword}</span>)}</div>
            </div>
          )}

          <div className="result-tabs" role="tablist" aria-label="Secciones de resultados">
            <button type="button" role="tab" aria-selected={activeView === "topics"} aria-controls="result-view" onClick={() => onChangeView("topics")}>Temas</button>
            <button type="button" role="tab" aria-selected={activeView === "messages"} aria-controls="result-view" onClick={() => onChangeView("messages")}>Mensajes <span>{formatNumber(result.assignments.length)}</span></button>
            <button type="button" role="tab" aria-selected={activeView === "quality"} aria-controls="result-view" onClick={() => onChangeView("quality")}>Calidad</button>
          </div>

          <div id="result-view" role="tabpanel" tabIndex={0} className="result-view">
            {activeView === "topics" && (
              <TopicTree topics={result.topics} selectedPath={selectedPath} onSelectPath={onSelectPath} />
            )}
            {activeView === "messages" && (
              <AssignmentTable assignments={result.assignments} selectedPath={selectedPath} onClearFilter={onClearFilter} />
            )}
            {activeView === "quality" && (
              <MetricsPanel metrics={result.metrics} hasLabels={datasetHasLabels} />
            )}
          </div>
        </>
      )}
    </section>
  );
}

function StatCard({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="stat-card">
      <span className="stat-icon">{icon}</span>
      <span className="stat-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
