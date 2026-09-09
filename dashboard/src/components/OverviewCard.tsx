import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FlashValue } from "@/components/FlashValue"
import { formatPct, formatUsdt, pnlColorClass } from "@/lib/format"
import type { StatusResponse } from "@/lib/api"

export function OverviewCard({ status }: { status: StatusResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Portfolio</CardTitle>
        <CardDescription>Shared cash pool across all coins</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
          <div>
            <div className="text-sm text-muted-foreground">Wallet Balance</div>
            <FlashValue value={status.equity} className="font-mono text-sm font-semibold tabular-nums">
              {formatUsdt(status.equity)}
            </FlashValue>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Total PnL</div>
            <div className={pnlColorClass(status.total_pnl)}>
              <FlashValue value={status.total_pnl} className="font-mono text-sm font-semibold tabular-nums">
                {formatUsdt(status.total_pnl, { signed: true })}
              </FlashValue>
              <span className="align-super font-mono text-[10px] font-normal tabular-nums opacity-80">
                {formatPct(status.total_pnl_pct)}
              </span>
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Cash Available</div>
            <FlashValue value={status.cash} className="font-mono text-sm font-semibold tabular-nums">
              {formatUsdt(status.cash)}
            </FlashValue>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Open Positions</div>
            <div className="font-mono text-sm font-semibold tabular-nums">{status.open_positions}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
