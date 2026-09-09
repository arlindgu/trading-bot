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
  { id: "donchian_breakout", label: "Donchian Breakout", description: "Long on a close above the prior 20-bar high, flat on a close below the prior low.", category: "real", frequency: "normal" },
  { id: "rsi_reversion", label: "RSI Reversion", description: "Long when RSI drops below 30 (oversold), exits once it climbs back above 60.", category: "real", frequency: "normal" },
  { id: "bollinger_reversion", label: "Bollinger Reversion", description: "Buys at or below the lower Bollinger band, exits once price reaches the middle band.", category: "real", frequency: "normal" },
  { id: "macd_momentum", label: "MACD Momentum", description: "Long on a bullish MACD/signal-line crossover, flat on a bearish one.", category: "real", frequency: "normal" },
  { id: "atr_breakout", label: "ATR Breakout", description: "Enters on a volatility breakout above the recent mean, rides it with an ATR trailing stop.", category: "real", frequency: "normal" },
  { id: "volume_spike", label: "Volume Spike", description: "Long on a volume spike with a green candle, exits once volume normalizes.", category: "real", frequency: "normal" },
  { id: "relative_momentum", label: "Relative Momentum", description: "Long when the recent return is positive and accelerating versus its own average.", category: "real", frequency: "normal" },
  { id: "buy_and_hold", label: "Buy & Hold", description: "Buys and holds, no exit logic -- the passive benchmark the other strategies are measured against.", category: "real", frequency: "normal" },
  { id: "rsi_scalp", label: "RSI Scalp", description: "1-minute futures RSI reversion -- long under 20, short over 80, exits back through 50.", category: "real", frequency: "high" },
  { id: "ema_scalp", label: "EMA Scalp", description: "1-minute futures EMA cross, always in a position, flips direction the instant the cross reverses.", category: "real", frequency: "high" },
  { id: "momentum_scalp", label: "Momentum Scalp", description: "1-minute futures, follows the sign of recent momentum, flips fast as direction changes.", category: "real", frequency: "high" },
  { id: "candle_reversal", label: "Candle Reversal", description: "Fades the last candle's color, holds one bar, closes right as the next one begins -- then repeats.", category: "real", frequency: "high" },
  { id: "coinflip", label: "Coinflip", description: "Random side, leverage, and take-profit/stop-loss on real futures leverage. For laughs.", category: "joke", frequency: "normal" },
  { id: "moon_phase", label: "Vollmond-Trader", description: "Long during the days around a full moon (computed from the date), flat otherwise.", category: "joke", frequency: "normal" },
  { id: "friday13", label: "Freitag-13-Trader", description: "Closes out on every Friday the 13th out of superstition, holds normally otherwise.", category: "joke", frequency: "normal" },
  { id: "prime_number", label: "Primzahl-Trader", description: "Only holds a position on days whose day-of-month is a prime number.", category: "joke", frequency: "normal" },
  { id: "contrarian_self", label: "Contrarian-Self", description: "Holds for a fixed number of candles, then skips its next entry after a losing trade.", category: "joke", frequency: "normal" },
  { id: "fomo_bot", label: "FOMO-Bot", description: "Only buys after price has already pumped, chasing strength on purpose -- sells when it stalls.", category: "joke", frequency: "normal" },
  { id: "diamond_hands", label: "Diamond-Hands", description: "Buys every dip it sees and never voluntarily sells, no matter how far it drops.", category: "joke", frequency: "normal" },
  { id: "buy_high_sell_low", label: "Buy-High-Sell-Low", description: "Chases fresh highs and panic-sells on the next red candle -- deliberately bad timing.", category: "joke", frequency: "normal" },
  { id: "zodiac", label: "Sternzeichen-Trader", description: "Long or flat purely based on which zodiac sign the current date falls under.", category: "joke", frequency: "normal" },
  { id: "hash_sentiment", label: "Hash-Sentiment-Bot", description: "Pretends to read crowd sentiment, actually just hashes the candle's own OHLCV data.", category: "joke", frequency: "normal" },
  { id: "zappelphilipp", label: "Zappelphilipp", description: "Can't sit still -- closes every 1-minute candle, then coinflips whether to reopen.", category: "joke", frequency: "high" },
  { id: "adrenaline_junkie", label: "Adrenaline-Junkie", description: "Flips side on literally every 1-minute candle at a random leverage, never sits still.", category: "joke", frequency: "high" },
  { id: "panic_bot", label: "Panic-Bot", description: "Opens a random direction, panics and flips the instant price ticks against it by any amount.", category: "joke", frequency: "high" },
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
