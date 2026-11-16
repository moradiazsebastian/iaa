import type { AnalysisOptions, AnalysisRequest, AnalysisResult } from "@/lib/types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String(payload.detail)
        : "No se pudo completar la solicitud.";
    throw new ApiError(detail, response.status);
  }

  return payload as T;
}

export const fetchAnalysisOptions = (path: string) => requestJson<AnalysisOptions>(path);

export const createAnalysis = (request: AnalysisRequest) =>
  requestJson<AnalysisResult>("/api/runs", {
    method: "POST",
    body: JSON.stringify(request),
  });

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 400) return "Ese método no está disponible en este entorno.";
    if (error.status === 404) return "No encontramos mensajes para esa temática y esas palabras clave.";
    if (error.status === 422) return "Revisá los valores: alguno está fuera del rango permitido.";
    if (error.status === 503) return "No hay un proveedor de IA configurado. Probá el modo sin IA o configurá el proveedor.";
    return error.message;
  }

  if (error instanceof Error && error.message) {
    return "No pudimos conectar con la API. Revisá el servicio e intentá de nuevo.";
  }

  return "Ocurrió un error inesperado. Intentá de nuevo.";
}
