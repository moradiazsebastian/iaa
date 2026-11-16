import { BadgeCheck, CircleHelp, Target } from "lucide-react";
import type { ClusterMetrics, EvaluationMetrics } from "@/lib/types";
import { formatNumber, formatScore } from "@/lib/format";

interface MetricsPanelProps {
  metrics: EvaluationMetrics | null;
  hasLabels: boolean;
}

const metricLabels = [
  { key: "ari", label: "ARI", description: "Acuerdo entre grupos, de −1 a 1." },
  { key: "nmi", label: "NMI", description: "Información compartida, de 0 a 1." },
  { key: "matched_accuracy", label: "Coincidencia", description: "Mensajes en el mejor emparejamiento de temas." },
] as const;

export function MetricsPanel({ metrics, hasLabels }: MetricsPanelProps) {
  if (!metrics) {
    return (
      <div className="metrics-empty">
        <CircleHelp aria-hidden="true" />
        <div>
          <h3>{hasLabels ? "No se calcularon métricas" : "Sin etiquetas de referencia"}</h3>
          <p>
            {hasLabels
              ? "Activá la comparación al iniciar una corrida para medir el acuerdo con las etiquetas del dataset."
              : "Este dataset no tiene clasificación manual para comparar los resultados."}
          </p>
        </div>
      </div>
    );
  }

  const sections = [
    { key: "topics", title: "Temas principales", data: metrics.topics },
    { key: "subtopics", title: "Subtemas", data: metrics.subtopics },
  ].filter((section) => section.data);

  return (
    <div className="metrics-content">
      <div className="metrics-intro">
        <span className="metric-icon"><Target aria-hidden="true" /></span>
        <div>
          <h3>Calidad de la clasificación</h3>
          <p>Comparación contra las etiquetas manuales del dataset.</p>
        </div>
      </div>
      {sections.map((section) => (
        <MetricGroup key={section.key} title={section.title} data={section.data!} />
      ))}
      <p className="metrics-footnote">Un puntaje más alto indica mayor coincidencia. ARI puede ser negativo si el acuerdo es menor al azar.</p>
    </div>
  );
}

function MetricGroup({ title, data }: { title: string; data: ClusterMetrics }) {
  return (
    <section className="metric-group" aria-label={title}>
      <div className="metric-group-heading">
        <h4>{title}</h4>
        <span>{formatNumber(data.n)} mensajes comparados</span>
      </div>
      <div className="quality-grid">
        {metricLabels.map(({ key, label, description }) => {
          const value = data[key];
          if (value === undefined) return null;
          const percent = key === "ari" ? Math.max(0, Math.min(100, ((value + 1) / 2) * 100)) : Math.max(0, Math.min(100, value * 100));
          return (
            <article className="quality-card" key={key}>
              <div className="quality-card-top">
                <span>{label}</span>
                {key === "matched_accuracy" ? <BadgeCheck aria-hidden="true" /> : <Target aria-hidden="true" />}
              </div>
              <strong>{key === "matched_accuracy" ? `${Math.round(value * 100)}%` : formatScore(value)}</strong>
              <div className="quality-meter" role="progressbar" aria-label={`${label}: ${formatScore(value)}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(percent)}>
                <span style={{ width: `${percent}%` }} />
              </div>
              <p>{description}</p>
            </article>
          );
        })}
      </div>
      {data.matching && Object.keys(data.matching).length > 0 && (
        <details className="matching-details">
          <summary>Ver emparejamiento de etiquetas</summary>
          <ul>
            {Object.entries(data.matching).map(([predicted, expected]) => (
              <li key={predicted}><span>{predicted}</span><span aria-hidden="true">→</span><span>{expected}</span></li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
