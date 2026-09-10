import type { StrategyId } from "@/lib/api"

export type Category = "real" | "joke"
export type Frequency = "normal" | "high"

export interface StrategyMeta {
  id: StrategyId
  label: string
  description: string
  category: Category
  frequency: Frequency
}

export const STRATEGIES: StrategyMeta[] = [
  { id: "grid", label: "Grid", description: "Buys and sells a fixed price ladder, profiting from price oscillating inside the range.", category: "real", frequency: "normal" },
  { id: "ma_crossover", label: "MA Crossover", description: "Long while the fast EMA (9) is above the slow EMA (21), flat otherwise.", category: "real", frequency: "normal" },
  { id: "rsi_reversion", label: "RSI Reversion", description: "Long when RSI drops below 30 (oversold), exits once it climbs back above 60.", category: "real", frequency: "normal" },
  { id: "buy_and_hold", label: "Buy & Hold", description: "Buys and holds, no exit logic -- the passive benchmark the other strategies are measured against.", category: "real", frequency: "normal" },
  { id: "micro_donchian", label: "Micro-Donchian", description: "1-minute spot Donchian breakout on a 5-bar channel -- tight enough to break on ordinary noise.", category: "real", frequency: "high" },
  { id: "bollinger_pinch", label: "Bollinger-Pinch", description: "1-minute spot Bollinger reversion on a tight 10-bar/1-std band, exits at the middle band.", category: "real", frequency: "high" },
  { id: "macd_pulse", label: "MACD-Pulse", description: "1-minute spot MACD (3/8/3) crossover, fast enough to flip several times an hour.", category: "real", frequency: "high" },
  { id: "atr_flicker", label: "ATR-Flicker", description: "1-minute spot volatility-burst entry -- reacts to single candles blowing past their ATR.", category: "real", frequency: "high" },
  { id: "volume_pulse", label: "Volume-Pulse", description: "1-minute spot volume-thrust entry on a 10-bar average, exits once volume normalizes.", category: "real", frequency: "high" },
  { id: "tick_momentum", label: "Tick-Momentum", description: "1-minute spot momentum on a 2-bar lookback, flips long/flat on almost every candle.", category: "real", frequency: "high" },
  { id: "rsi_scalp", label: "RSI Scalp", description: "1-minute futures RSI reversion -- long under 20, short over 80, exits back through 50.", category: "real", frequency: "high" },
  { id: "ema_scalp", label: "EMA Scalp", description: "1-minute futures EMA cross, always in a position, flips direction the instant the cross reverses.", category: "real", frequency: "high" },
  { id: "momentum_scalp", label: "Momentum Scalp", description: "1-minute futures, follows the sign of recent momentum, flips fast as direction changes.", category: "real", frequency: "high" },
  { id: "candle_reversal", label: "Candle Reversal", description: "Fades the last candle's color, holds one bar, closes right as the next one begins -- then repeats.", category: "real", frequency: "high" },
  { id: "coinflip", label: "Coinflip", description: "Random side, leverage, and take-profit/stop-loss on real futures leverage. For laughs.", category: "joke", frequency: "normal" },
  { id: "friday13", label: "Freitag-13-Trader", description: "Closes out on every Friday the 13th out of superstition, holds normally otherwise.", category: "joke", frequency: "normal" },
  { id: "contrarian_self", label: "Contrarian-Self", description: "Holds for a fixed number of candles, then skips its next entry after a losing trade.", category: "joke", frequency: "normal" },
  { id: "diamond_hands", label: "Diamond-Hands", description: "Buys every dip it sees and never voluntarily sells, no matter how far it drops.", category: "joke", frequency: "normal" },
  { id: "hash_sentiment", label: "Hash-Sentiment-Bot", description: "Pretends to read crowd sentiment, actually just hashes the candle's own OHLCV data.", category: "joke", frequency: "normal" },
  { id: "zappelphilipp", label: "Zappelphilipp", description: "Can't sit still -- closes every 1-minute candle, then coinflips whether to reopen.", category: "joke", frequency: "high" },
  { id: "pendel_bot", label: "Pendel-Bot", description: "Swings in and out like a pendulum -- long on even candles, flat on odd ones, every 1m candle.", category: "joke", frequency: "high" },
  { id: "herzschlag_bot", label: "Herzschlag-Bot", description: "A heartbeat -- buys, holds one candle, sells, buys again, forever, on 1-minute bars.", category: "joke", frequency: "high" },
  { id: "wackelkontakt_bot", label: "Wackelkontakt-Bot", description: "Hashes the candle into a coin every 1-minute bar and jumps to whatever side it says.", category: "joke", frequency: "high" },
  { id: "sekundenschlaf_bot", label: "Sekundenschlaf-Bot", description: "Opens a position, naps for 1-3 candles, wakes up, closes, and rolls a fresh nap.", category: "joke", frequency: "high" },
  { id: "trommelwirbel_bot", label: "Trommelwirbel-Bot", description: "Builds a position over 3 candles, dumps it all on the 4th, and starts the next drumroll.", category: "joke", frequency: "high" },
  { id: "adrenaline_junkie", label: "Adrenaline-Junkie", description: "Flips side on literally every 1-minute candle at a random leverage, never sits still.", category: "joke", frequency: "high" },
  { id: "panic_bot", label: "Panic-Bot", description: "Opens a random direction, panics and flips the instant price ticks against it by any amount.", category: "joke", frequency: "high" },
  { id: "raidboss_futures", label: "RAIDBOSS", description: "Rolls a random mood every candle -- nibble, yolo, double down, flip sides, rage quit, or do nothing. No plan, real leverage.", category: "joke", frequency: "high" },
]

export const GROUPS: { key: Category; frequency: Frequency; label: string }[] = [
  { key: "real", frequency: "normal", label: "Real" },
  { key: "real", frequency: "high", label: "Real (High Frequency)" },
  { key: "joke", frequency: "normal", label: "Joke" },
  { key: "joke", frequency: "high", label: "Joke (High Frequency)" },
]

export function strategyLabel(id: StrategyId | string): string {
  return STRATEGIES.find((s) => s.id === id)?.label ?? id
}
