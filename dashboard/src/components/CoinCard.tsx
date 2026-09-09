import { useMemo } from "react"
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { FlashValue } from "@/components/FlashValue"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { fetchSymbolHistory, fetchSymbolTrades, type SymbolSummary } from "@/lib/api"
import { formatUsdt, pnlColorClass } from "@/lib/format"
import { usePolling } from "@/lib/usePolling"

const chartConfig = {
  total_pnl: {
    label: "PnL",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig

export function CoinCard({
  account,
  symbol,
  summary,
  pollMs,
}: {
  account: string
  symbol: string
  summary: SymbolSummary
  pollMs: number
}) {
  const { data: history } = usePolling(() => fetchSymbolHistory(account, symbol), pollMs, account)
  const { data: trades } = usePolling(() => fetchSymbolTrades(account, symbol), pollMs, account)

  const chartData = useMemo(
    () => (history ?? []).map((point) => ({ timestamp: point.timestamp, total_pnl: point.total_pnl })),
    [history]
  )

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>{symbol}</CardTitle>
          <FlashValue value={summary.mark_price} className="font-mono text-xs text-muted-foreground tabular-nums">
            {summary.mark_price !== null ? formatUsdt(summary.mark_price, { decimals: 4 }) : "–"}
          </FlashValue>
        </div>
        <div className="flex flex-col items-end gap-1">
          <FlashValue value={summary.total_pnl} className={`font-mono text-sm font-semibold tabular-nums ${pnlColorClass(summary.total_pnl)}`}>
            {formatUsdt(summary.total_pnl, { signed: true })}
          </FlashValue>
          <div className="flex gap-2">
            <Badge variant="secondary">
              <span className="font-mono text-xs tabular-nums">{summary.open_positions}</span> open
            </Badge>
            <Badge variant="secondary">
              <span className="font-mono text-xs tabular-nums">{summary.closed_trades}</span> closed
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-muted-foreground">Realized</div>
            <FlashValue value={summary.realized_pnl} className={`font-mono text-sm tabular-nums ${pnlColorClass(summary.realized_pnl)}`}>
              {formatUsdt(summary.realized_pnl, { signed: true })}
            </FlashValue>
          </div>
          <div>
            <div className="text-muted-foreground">Unrealized</div>
            <FlashValue
              value={summary.unrealized_pnl}
              className={`font-mono text-sm tabular-nums ${pnlColorClass(summary.unrealized_pnl)}`}
            >
              {formatUsdt(summary.unrealized_pnl, { signed: true })}
            </FlashValue>
          </div>
        </div>

        {chartData.length > 1 ? (
          <ChartContainer config={chartConfig} className="h-32 w-full">
            <LineChart data={chartData} margin={{ left: 0, right: 0, top: 4, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" hide />
              <YAxis hide domain={["auto", "auto"]} />
              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent labelFormatter={(value) => new Date(value as string).toLocaleString()} />}
              />
              <Line dataKey="total_pnl" type="monotone" stroke="var(--color-total_pnl)" strokeWidth={2} dot={false} />
            </LineChart>
          </ChartContainer>
        ) : (
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            Not enough data for a chart yet
          </div>
        )}

        <Separator />

        <div>
          <div className="mb-2 text-sm font-medium">Transaction History</div>
          <ScrollArea className="h-48">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Side</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                  <TableHead className="text-right">Size</TableHead>
                  <TableHead className="text-right">PnL</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(trades ?? []).map((trade, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                      {new Date(trade.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge variant={trade.side === "buy" ? "outline" : "secondary"}>{trade.side}</Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">{formatUsdt(trade.price)}</TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">{trade.size.toFixed(4)}</TableCell>
                    <TableCell
                      className={`text-right font-mono text-xs tabular-nums ${trade.pnl != null ? pnlColorClass(trade.pnl) : ""}`}
                    >
                      {trade.pnl != null ? formatUsdt(trade.pnl, { signed: true }) : "–"}
                    </TableCell>
                  </TableRow>
                ))}
                {(trades ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-sm text-muted-foreground">
                      No trades yet
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  )
}
