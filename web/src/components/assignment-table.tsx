"use client";

import { useMemo, useState } from "react";
import { Download, Search, X } from "lucide-react";
import type { TweetAssignment } from "@/lib/types";
import { formatNumber } from "@/lib/format";

interface AssignmentTableProps {
  assignments: TweetAssignment[];
  selectedPath: string | null;
  onClearFilter: () => void;
}

const pageSize = 12;
const csvColumns = ["id", "topic_path", "topic", "subtopic", "text"] as const;

function escapeCsv(value: string): string {
  return `"${value.replaceAll('"', '""')}"`;
}

export function AssignmentTable({ assignments, selectedPath, onClearFilter }: AssignmentTableProps) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);

  const filteredAssignments = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("es");
    return assignments.filter((assignment) => {
      const matchesPath =
        !selectedPath ||
        assignment.topic_path === selectedPath ||
        assignment.topic_path.startsWith(`${selectedPath}.`);
      const matchesQuery =
        !normalizedQuery ||
        [assignment.id, assignment.topic, assignment.subtopic, assignment.text]
          .join(" ")
          .toLocaleLowerCase("es")
          .includes(normalizedQuery);
      return matchesPath && matchesQuery;
    });
  }, [assignments, query, selectedPath]);

  const pageCount = Math.max(1, Math.ceil(filteredAssignments.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const visibleAssignments = filteredAssignments.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  const firstRow = filteredAssignments.length ? currentPage * pageSize + 1 : 0;
  const lastRow = Math.min((currentPage + 1) * pageSize, filteredAssignments.length);

  function downloadCsv() {
    const header = csvColumns.join(",");
    const rows = filteredAssignments.map((assignment) =>
      csvColumns.map((column) => escapeCsv(assignment[column] ?? "")).join(","),
    );
    const blob = new Blob(["\uFEFF", [header, ...rows].join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "foco-social-mensajes.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="assignment-browser" aria-label="Mensajes clasificados">
      <div className="assignment-tools">
        <label className="search-field" htmlFor="assignment-search">
          <Search aria-hidden="true" />
          <input
            id="assignment-search"
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(0);
            }}
            placeholder="Buscar en mensajes y temas"
          />
        </label>
        <button className="secondary-button export-button" type="button" onClick={downloadCsv} disabled={!filteredAssignments.length}>
          <Download aria-hidden="true" />
          Descargar CSV
        </button>
      </div>

      {selectedPath && (
        <div className="filter-chip">
          <span>Filtro: tema {selectedPath}</span>
          <button type="button" onClick={onClearFilter} aria-label="Quitar filtro de tema"><X aria-hidden="true" /></button>
        </div>
      )}

      <div className="table-meta" aria-live="polite">
        <span>{formatNumber(filteredAssignments.length)} mensajes encontrados</span>
        <span>{firstRow}–{lastRow} de {formatNumber(filteredAssignments.length)}</span>
      </div>

      {visibleAssignments.length ? (
        <div className="table-scroll">
          <table className="assignment-table">
            <caption className="sr-only">Mensajes asignados a temas y subtemas</caption>
            <thead>
              <tr>
                <th scope="col">Mensaje</th>
                <th scope="col">Tema</th>
                <th scope="col">Subtema</th>
              </tr>
            </thead>
            <tbody>
              {visibleAssignments.map((assignment) => (
                <tr key={assignment.id}>
                  <td>
                    <p className="tweet-copy">{assignment.text}</p>
                    <span className="tweet-id">{assignment.id}</span>
                  </td>
                  <td><span className="table-topic">{assignment.topic}</span></td>
                  <td><span className="table-subtopic">{assignment.subtopic || "—"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="inline-empty">No hay mensajes que coincidan con la búsqueda.</div>
      )}

      {filteredAssignments.length > pageSize && (
        <div className="pagination-controls">
          <button type="button" className="secondary-button" onClick={() => setPage(Math.max(0, currentPage - 1))} disabled={currentPage === 0}>
            Anterior
          </button>
          <span>Página {currentPage + 1} de {pageCount}</span>
          <button type="button" className="secondary-button" onClick={() => setPage(Math.min(pageCount - 1, currentPage + 1))} disabled={currentPage >= pageCount - 1}>
            Siguiente
          </button>
        </div>
      )}
    </section>
  );
}
