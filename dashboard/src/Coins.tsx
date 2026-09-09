import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { fetchCoinBots, fetchCoins, type CoinBotRow } from "@/lib/api"
import { formatUsdt, pnlColorClass } from "@/lib/format"
import { strategyLabel } from "@/lib/strategies"
import { usePolling } from "@/lib/usePolling"

const POLL_MS = 30_000

function initialCoin(): string | null {
  return new URLSearchParams(window.location.search).get("coin")
}

function accountHref(row: CoinBotRow): string {
  return `/?strategy=${encodeURIComponent(row.strategy)}&account=${encodeURIComponent(row.account)}`
}

export function Coins() {
  const { data: allCoins, error: coinsError } = usePolling(fetchCoins, 300_000)
  const [coin, setCoin] = useState<string | null>(initialCoin)

  useEffect(() => {
    if (!coin && allCoins && allCoins.length > 0) setCoin(allCoins[0])
  }, [allCoins, coin])

  const { data: rows, error: botsError } = usePolling(
    () => (coin ? fetchCoinBots(coin) : Promise.reject(new Error("no coin selected"))),
    POLL_MS,
    coin
  )

  const error = coinsError ?? botsError

  return (
    <div className="min-h-svh bg-background text-foreground">
      <div className="mx-auto flex max-w-4xl min-w-0 flex-col gap-6 px-4 py-8">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">Coins</h1>
            <p className="text-sm text-muted-foreground">Pick a coin, see how every bot is trading it right now.</p>
          </div>
          <Button variant="outline" size="sm" render={<a href="/" />}>
            Back to dashboard
          </Button>
        </header>

        {error && (
          <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Failed to reach the API: {error.message}
          </div>
        )}

        {!allCoins && !error && <Skeleton className="h-9 w-full" />}

        {allCoins && (
          <div className="flex flex-wrap gap-2">
            {allCoins.map((c) => (
              <Button key={c} size="sm" variant={c === coin ? "default" : "outline"} onClick={() => setCoin(c)}>
                {c}
              </Button>
            ))}
          </div>
        )}

        {!rows && !error && coin && (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        )}

        {rows && rows.length === 0 && <p className="text-sm text-muted-foreground">No bot has traded {coin} yet.</p>}

        {rows && rows.length > 0 && (
          <div className="min-w-0 overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Symbol</TableHead>
                  <TableHead className="text-right">Open</TableHead>
                  <TableHead className="text-right">Closed</TableHead>
                  <TableHead className="text-right">Mark</TableHead>
                  <TableHead className="text-right">PnL</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow
                    key={`${row.account}-${row.symbol}`}
                    className="cursor-pointer"
                    onClick={() => {
                      window.location.href = accountHref(row)
                    }}
                  >
                    <TableCell className="text-sm font-medium">{strategyLabel(row.strategy)}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{row.symbol}</TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">{row.open_positions}</TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">{row.closed_trades}</TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {row.mark_price != null ? formatUsdt(row.mark_price) : "–"}
                    </TableCell>
                    <TableCell className={`text-right font-mono text-sm font-semibold tabular-nums ${pnlColorClass(row.total_pnl)}`}>
                      {formatUsdt(row.total_pnl, { signed: true })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  )
}

export default Coins
