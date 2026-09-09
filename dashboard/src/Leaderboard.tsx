import { useMemo } from "react"

import { FlashValue } from "@/components/FlashValue"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { fetchLeaderboard, type LeaderboardRow } from "@/lib/api"
import { formatPct, formatUsdt, pnlColorClass } from "@/lib/format"
import { strategyLabel } from "@/lib/strategies"
import { usePolling } from "@/lib/usePolling"

const POLL_MS = 30_000

function accountHref(row: LeaderboardRow): string {
  return `/?strategy=${encodeURIComponent(row.strategy)}&account=${encodeURIComponent(row.id)}`
}

export function Leaderboard() {
  const { data: rows, error } = usePolling(fetchLeaderboard, POLL_MS)

  const ranked = useMemo(() => {
    if (!rows) return []
    // Accounts with no snapshot yet (brand new) sort to the bottom, not
    // mixed in with real 0.00% performers.
    return [...rows].sort((a, b) => {
      if (a.total_pnl_pct == null && b.total_pnl_pct == null) return 0
      if (a.total_pnl_pct == null) return 1
      if (b.total_pnl_pct == null) return -1
      return b.total_pnl_pct - a.total_pnl_pct
    })
  }, [rows])

  const best = ranked[0]
  const worst = ranked.length > 1 ? ranked[ranked.length - 1] : undefined

  return (
    <div className="min-h-svh bg-background text-foreground">
      <div className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-8">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">Leaderboard</h1>
            <p className="text-sm text-muted-foreground">Every strategy, ranked by PnL %. Click a row to open it.</p>
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

        {!rows && !error && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        )}

        {best && worst && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <a href={accountHref(best)} className="rounded-lg border p-4 transition-colors hover:bg-muted/50">
              <div className="mb-1 flex items-center gap-2">
                <Badge>Best</Badge>
                <span className="text-sm font-medium">{strategyLabel(best.strategy)}</span>
              </div>
              <FlashValue
                value={best.total_pnl_pct ?? 0}
                className={`font-mono text-xl font-semibold tabular-nums ${pnlColorClass(best.total_pnl_pct ?? 0)}`}
              >
                {formatPct(best.total_pnl_pct)}
              </FlashValue>
            </a>
            <a href={accountHref(worst)} className="rounded-lg border p-4 transition-colors hover:bg-muted/50">
              <div className="mb-1 flex items-center gap-2">
                <Badge variant="secondary">Worst</Badge>
                <span className="text-sm font-medium">{strategyLabel(worst.strategy)}</span>
              </div>
              <FlashValue
                value={worst.total_pnl_pct ?? 0}
                className={`font-mono text-xl font-semibold tabular-nums ${pnlColorClass(worst.total_pnl_pct ?? 0)}`}
              >
                {formatPct(worst.total_pnl_pct)}
              </FlashValue>
            </a>
          </div>
        )}

        {ranked.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">#</TableHead>
                <TableHead>Strategy</TableHead>
                <TableHead>Budget</TableHead>
                <TableHead className="text-right">Equity</TableHead>
                <TableHead className="text-right">PnL</TableHead>
                <TableHead className="text-right">PnL %</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ranked.map((row, i) => (
                <TableRow
                  key={row.id}
                  className="cursor-pointer"
                  onClick={() => {
                    window.location.href = accountHref(row)
                  }}
                >
                  <TableCell className="font-mono text-xs text-muted-foreground tabular-nums">{i + 1}</TableCell>
                  <TableCell className="text-sm font-medium">{strategyLabel(row.strategy)}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground tabular-nums">
                    {formatUsdt(row.starting_cash)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">{formatUsdt(row.equity)}</TableCell>
                  <TableCell
                    className={`text-right font-mono text-xs tabular-nums ${row.total_pnl != null ? pnlColorClass(row.total_pnl) : ""}`}
                  >
                    {formatUsdt(row.total_pnl, { signed: true })}
                  </TableCell>
                  <TableCell
                    className={`text-right font-mono text-sm font-semibold tabular-nums ${row.total_pnl_pct != null ? pnlColorClass(row.total_pnl_pct) : ""}`}
                  >
                    {formatPct(row.total_pnl_pct)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  )
}

export default Leaderboard
