const integerFormatter = new Intl.NumberFormat("es-AR");
const percentFormatter = new Intl.NumberFormat("es-AR", {
  style: "percent",
  maximumFractionDigits: 1,
});
const decimalFormatter = new Intl.NumberFormat("es-AR", {
  maximumFractionDigits: 2,
});

export function formatNumber(value: number | undefined): string {
  return integerFormatter.format(value ?? 0);
}

export function formatPercent(value: number | undefined): string {
  return percentFormatter.format(value ?? 0);
}

export function formatScore(value: number | undefined): string {
  return value === undefined ? "—" : decimalFormatter.format(value);
}

export function formatSeconds(value: number | undefined): string {
  if (value === undefined || !Number.isFinite(value)) return "—";
  if (value < 60) return `${decimalFormatter.format(value)} s`;
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);
  return `${minutes} min ${seconds} s`;
}
