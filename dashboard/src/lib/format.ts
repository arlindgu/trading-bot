export function formatUsdt(
  value: number | null | undefined,
  opts: { signed?: boolean; decimals?: number } = {}
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–"
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: opts.decimals ?? 2,
    maximumFractionDigits: opts.decimals ?? 2,
  }).format(Math.abs(value))
  const sign = value < 0 ? "-" : opts.signed && value > 0 ? "+" : ""
  return `${sign}${formatted} USDT`
}

export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–"
  const sign = value > 0 ? "+" : ""
  return `${sign}${value.toFixed(2)}%`
}

export function pnlColorClass(value: number): string {
  if (value > 0) return "text-emerald-600 dark:text-emerald-400"
  if (value < 0) return "text-red-600 dark:text-red-500"
  return "text-muted-foreground"
}
