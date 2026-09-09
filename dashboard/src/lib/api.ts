export interface SymbolSummary {
  open_positions: number
  closed_trades: number
  realized_pnl: number
  unrealized_pnl: number
  total_pnl: number
  mark_price: number | null
}

export interface StatusResponse {
  equity: number | null
  cash: number | null
  starting_cash: number
  total_realized_pnl: number
  total_unrealized_pnl: number
  total_pnl: number
  total_pnl_pct: number | null
  open_positions: number
  last_updated: string | null
  per_symbol: Record<string, SymbolSummary>
}

export interface SymbolHistoryPoint {
  timestamp: string
  mark_price: number
  realized_pnl: number
  unrealized_pnl: number
  total_pnl: number
}

export interface Trade {
  side: "buy" | "sell"
  price: number
  size: number
  timestamp: string
  reason: string | null
  pnl: number | null
}

export interface Account {
  id: string
  label: string
  starting_cash: number
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export function fetchAccounts(): Promise<Account[]> {
  return getJson("/api/accounts")
}

export function fetchStatus(account: string): Promise<StatusResponse> {
  return getJson(`/api/status?account=${encodeURIComponent(account)}`)
}

export function fetchSymbolHistory(account: string, symbol: string): Promise<SymbolHistoryPoint[]> {
  return getJson(`/api/symbols/${symbol}/history?account=${encodeURIComponent(account)}`)
}

export function fetchSymbolTrades(account: string, symbol: string): Promise<Trade[]> {
  return getJson(`/api/symbols/${symbol}/trades?account=${encodeURIComponent(account)}`)
}
