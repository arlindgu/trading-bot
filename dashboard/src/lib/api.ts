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
  fees: Record<string, number>
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

export interface CoinflipInfo {
  side: "long" | "short"
  leverage: number
}

export interface OpenPosition {
  lot_id: string
  size: number
  entry_price: number
  entry_time: string
  tag: string
  target_price: number | null
  coinflip: CoinflipInfo | null
  info: string | null
}

export type StrategyId =
  | "grid"
  | "coinflip"
  | "ma_crossover"
  | "donchian_breakout"
  | "rsi_reversion"
  | "bollinger_reversion"
  | "macd_momentum"
  | "atr_breakout"
  | "volume_spike"
  | "relative_momentum"
  | "buy_and_hold"
  | "moon_phase"
  | "friday13"
  | "prime_number"
  | "contrarian_self"
  | "fomo_bot"
  | "diamond_hands"
  | "buy_high_sell_low"
  | "zodiac"
  | "hash_sentiment"
  | "zappelphilipp"
  | "rsi_scalp"
  | "ema_scalp"
  | "momentum_scalp"
  | "candle_reversal"
  | "adrenaline_junkie"
  | "panic_bot"
  | "raidboss_futures"

export interface Account {
  id: string
  label: string
  starting_cash: number
  strategy: StrategyId
}

export interface WalletBalance {
  usdt: number | null
  usdc: number | null
  error?: string
}

export type FuturesWalletBalance = WalletBalance

export interface CoinBotRow {
  account: string
  label: string
  strategy: StrategyId
  symbol: string
  open_positions: number
  closed_trades: number
  realized_pnl: number
  unrealized_pnl: number
  total_pnl: number
  mark_price: number | null
}

export interface LeaderboardRow {
  id: string
  label: string
  strategy: StrategyId
  equity: number | null
  starting_cash: number
  total_pnl: number | null
  total_pnl_pct: number | null
  last_updated: string | null
  open_trades: number
  closed_trades: number
  won_trades: number
  lost_trades: number
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export function fetchAccounts(): Promise<Account[]> {
  return getJson("/api/accounts")
}

export function fetchWalletBalance(): Promise<WalletBalance> {
  return getJson("/api/wallet_balance")
}

export function fetchFuturesWalletBalance(): Promise<FuturesWalletBalance> {
  return getJson("/api/futures_wallet_balance")
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

export function fetchSymbolPositions(account: string, symbol: string): Promise<OpenPosition[]> {
  return getJson(`/api/symbols/${symbol}/positions?account=${encodeURIComponent(account)}`)
}

export function fetchLeaderboard(): Promise<LeaderboardRow[]> {
  return getJson("/api/leaderboard")
}

export function fetchCoins(): Promise<string[]> {
  return getJson("/api/coins")
}

export function fetchCoinBots(base: string): Promise<CoinBotRow[]> {
  return getJson(`/api/coins/${encodeURIComponent(base)}/bots`)
}
