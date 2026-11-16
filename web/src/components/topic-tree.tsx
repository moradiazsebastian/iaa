import { ChevronRight, Layers3 } from "lucide-react";
import type { Topic } from "@/lib/types";
import { formatNumber, formatPercent } from "@/lib/format";

interface TopicNode extends Topic {
  children: TopicNode[];
}

interface TopicTreeProps {
  topics: Topic[];
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
}

function buildTopicTree(topics: Topic[]): TopicNode[] {
  const sorted = [...topics].sort((a, b) => a.path.localeCompare(b.path, "es", { numeric: true }));
  const nodes = new Map<string, TopicNode>();

  for (const topic of sorted) {
    nodes.set(topic.path, { ...topic, children: [] });
  }

  const roots: TopicNode[] = [];
  for (const topic of sorted) {
    const node = nodes.get(topic.path);
    if (!node) continue;
    const parentPath = topic.path.split(".").slice(0, -1).join(".");
    const parent = nodes.get(parentPath);
    if (parent) parent.children.push(node);
    else roots.push(node);
  }

  return roots;
}

export function TopicTree({ topics, selectedPath, onSelectPath }: TopicTreeProps) {
  const roots = buildTopicTree(topics);

  if (roots.length === 0) {
    return <div className="inline-empty">El análisis no devolvió temas para mostrar.</div>;
  }

  return (
    <div className="topic-tree">
      <div className="tree-caption">
        <span><Layers3 aria-hidden="true" /> Temas y subtemas</span>
        <span>Seleccioná uno para filtrar mensajes</span>
      </div>
      {roots.map((topic) => (
        <TopicRow key={topic.path} topic={topic} selectedPath={selectedPath} onSelectPath={onSelectPath} depth={0} />
      ))}
    </div>
  );
}

interface TopicRowProps {
  topic: TopicNode;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  depth: number;
}

function TopicRow({ topic, selectedPath, onSelectPath, depth }: TopicRowProps) {
  const share = Math.max(0, Math.min(1, topic.share_of_total));
  const isSelected = selectedPath === topic.path;

  return (
    <div className={`topic-node${depth > 0 ? " topic-node-child" : ""}`}>
      <button
        className={`topic-select${isSelected ? " is-selected" : ""}`}
        type="button"
        style={{ marginLeft: `${Math.min(depth, 3) * 18}px` }}
        onClick={() => onSelectPath(topic.path)}
        aria-pressed={isSelected}
        aria-label={`Filtrar mensajes por ${topic.name}, ${formatPercent(share)} del total`}
      >
        <span className={`topic-index${depth > 0 ? " is-child" : ""}`}>{topic.path}</span>
        <span className="topic-copy">
          <span className="topic-title">{topic.name}</span>
          <span className="topic-description">{topic.description}</span>
          <span className="topic-meter" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(share * 100)} aria-valuetext={`${formatPercent(share)} del total`}>
            <span style={{ width: `${share * 100}%` }} />
          </span>
        </span>
        <span className="topic-stat">
          <strong>{formatPercent(share)}</strong>
          <span>{formatNumber(topic.n_tweets)} mensajes</span>
        </span>
        {topic.children.length > 0 && <ChevronRight className="topic-chevron" aria-hidden="true" />}
      </button>
      {topic.children.length > 0 && (
        <div className="topic-children">
          {topic.children.map((child) => (
            <TopicRow key={child.path} topic={child} selectedPath={selectedPath} onSelectPath={onSelectPath} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
