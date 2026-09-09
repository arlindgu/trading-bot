import { useEffect, useMemo, useState } from "react"

import { CoinCard } from "@/components/CoinCard"
import { FlashValue } from "@/components/FlashValue"
import { OverviewCard } from "@/components/OverviewCard"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  fetchAccounts,
  fetchFuturesWalletBalance,
  fetchStatus,
  fetchWalletBalance,
  type StrategyId,
} from "@/lib/api"
import { formatUsdt } from "@/lib/format"
import { usePolling } from "@/lib/usePolling"

const POLL_MS = 30_000
const STRATEGIES: { id: StrategyId; label: string; description: string }[] = [
  { id: "grid", label: "Grid", description: "Buys and sells a fixed price ladder, profiting from price oscillating inside the range." },
  { id: "coinflip", label: "Coinflip", description: "Random side, leverage, and take-profit/stop-loss on real futures leverage. For laughs." },
  { id: "ma_crossover", label: "MA Crossover", description: "Long while the fast EMA (9) is above the slow EMA (21), flat otherwise." },
  { id: "donchian_breakout", label: "Donchian Breakout", description: "Long on a close above the prior 20-bar high, flat on a close below the prior low." },
  { id: "rsi_reversion", label: "RSI Reversion", description: "Long when RSI drops below 30 (oversold), exits once it climbs back above 60." },
  { id: "bollinger_reversion", label: "Bollinger Reversion", description: "Buys at or below the lower Bollinger band, exits once price reaches the middle band." },
  { id: "macd_momentum", label: "MACD Momentum", description: "Long on a bullish MACD/signal-line crossover, flat on a bearish one." },
  { id: "atr_breakout", label: "ATR Breakout", description: "Enters on a volatility breakout above the recent mean, rides it with an ATR trailing stop." },
  { id: "volume_spike", label: "Volume Spike", description: "Long on a volume spike with a green candle, exits once volume normalizes." },
  { id: "relative_momentum", label: "Relative Momentum", description: "Long when the recent return is positive and accelerating versus its own average." },
  { id: "buy_and_hold", label: "Buy & Hold", description: "Buys and holds, no exit logic -- the passive benchmark the other strategies are measured against." },
  { id: "moon_phase", label: "Vollmond-Trader", description: "Long during the days around a full moon (computed from the date), flat otherwise." },
  { id: "friday13", label: "Freitag-13-Trader", description: "Closes out on every Friday the 13th out of superstition, holds normally otherwise." },
  { id: "prime_number", label: "Primzahl-Trader", description: "Only holds a position on days whose day-of-month is a prime number." },
  { id: "contrarian_self", label: "Contrarian-Self", description: "Holds for a fixed number of candles, then skips its next entry after a losing trade." },
  { id: "fomo_bot", label: "FOMO-Bot", description: "Only buys after price has already pumped, chasing strength on purpose -- sells when it stalls." },
  { id: "diamond_hands", label: "Diamond-Hands", description: "Buys every dip it sees and never voluntarily sells, no matter how far it drops." },
  { id: "buy_high_sell_low", label: "Buy-High-Sell-Low", description: "Chases fresh highs and panic-sells on the next red candle -- deliberately bad timing." },
  { id: "zodiac", label: "Sternzeichen-Trader", description: "Long or flat purely based on which zodiac sign the current date falls under." },
  { id: "hash_sentiment", label: "Hash-Sentiment-Bot", description: "Pretends to read crowd sentiment, actually just hashes the candle's own OHLCV data." },
]

export function App() {
  const { data: accounts } = usePolling(fetchAccounts, 60_000)
  const { data: wallet } = usePolling(fetchWalletBalance, 60_000)
  const { data: futuresWallet } = usePolling(fetchFuturesWalletBalance, 60_000)

  const [strategy, setStrategy] = useState<StrategyId>("grid")
  const currentStrategy = useMemo(() => STRATEGIES.find((s) => s.id === strategy), [strategy])
  const accountsForStrategy = useMemo(
    () => (accounts ?? []).filter((a) => a.strategy === strategy),
    [accounts, strategy]
  )

  const [account, setAccount] = useState<string | null>(null)
  useEffect(() => {
    if (accountsForStrategy.length > 0 && !accountsForStrategy.some((a) => a.id === account)) {
      setAccount(accountsForStrategy[0].id)
    }
  }, [accountsForStrategy, account])

  const { data: status, error } = usePolling(
    () => (account ? fetchStatus(account) : Promise.reject(new Error("no account selected"))),
    POLL_MS,
    account
  )

  return (
    <div className="min-h-svh bg-background text-foreground">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">STRATA</h1>
            <p className="text-sm text-muted-foreground">
              {status?.last_updated
                ? `Last updated: ${new Date(status.last_updated).toLocaleString()}`
                : "Waiting for data..."}
            </p>
            {wallet?.usdt != null && wallet?.usdc != null && (
              <p className="text-sm text-muted-foreground">
                Demo spot wallet:{" "}
                <FlashValue value={wallet.usdt + wallet.usdc} className="font-mono tabular-nums">
                  {formatUsdt(wallet.usdt + wallet.usdc)}
                </FlashValue>
              </p>
            )}
            {futuresWallet?.usdt != null && futuresWallet?.usdc != null && (
              <p className="text-sm text-muted-foreground">
                Demo futures wallet:{" "}
                <FlashValue value={futuresWallet.usdt + futuresWallet.usdc} className="font-mono tabular-nums">
                  {formatUsdt(futuresWallet.usdt + futuresWallet.usdc)}
                </FlashValue>
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Select value={strategy} onValueChange={(value) => value && setStrategy(value as StrategyId)}>
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {STRATEGIES.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>

            {accountsForStrategy.length > 1 && account && (
              <Select value={account} onValueChange={(value) => value && setAccount(value)}>
                <SelectTrigger className="w-[170px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {accountsForStrategy.map((a) => (
                      <SelectItem key={a.id} value={a.id}>
                        {a.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            )}
          </div>
        </header>

        {currentStrategy && (
          <div className="rounded-md border bg-muted/30 px-4 py-3 text-sm">{currentStrategy.description}</div>
        )}

        {error && (
          <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Failed to reach the API: {error.message}
          </div>
        )}

        {!status && !error && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </div>
        )}

        {status && <OverviewCard status={status} />}

        {status && account && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {Object.entries(status.per_symbol)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([symbol, summary]) => (
                <CoinCard key={`${account}-${symbol}`} account={account} symbol={symbol} summary={summary} pollMs={POLL_MS} />
              ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default App
