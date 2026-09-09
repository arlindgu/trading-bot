import { useEffect, useMemo, useState } from "react"

import { CoinCard } from "@/components/CoinCard"
import { FlashValue } from "@/components/FlashValue"
import { OverviewCard } from "@/components/OverviewCard"
import { Badge } from "@/components/ui/badge"
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
const STRATEGIES: { id: StrategyId; label: string }[] = [
  { id: "grid", label: "Grid" },
  { id: "coinflip", label: "Coinflip" },
]

export function App() {
  const { data: accounts } = usePolling(fetchAccounts, 60_000)
  const { data: wallet } = usePolling(fetchWalletBalance, 60_000)
  const { data: futuresWallet } = usePolling(fetchFuturesWalletBalance, 60_000)

  const [strategy, setStrategy] = useState<StrategyId>("grid")
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
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {wallet?.usdt != null && (
              <Badge variant="outline" className="gap-1.5 py-1.5">
                Testnet spot wallet
                <FlashValue value={wallet.usdt} className="font-mono tabular-nums">
                  {formatUsdt(wallet.usdt)}
                </FlashValue>
              </Badge>
            )}
            {futuresWallet?.usdt != null && futuresWallet?.usdc != null && (
              <Badge variant="outline" className="gap-1.5 py-1.5">
                Futures demo wallet
                <FlashValue value={futuresWallet.usdt + futuresWallet.usdc} className="font-mono tabular-nums">
                  {formatUsdt(futuresWallet.usdt + futuresWallet.usdc)}
                </FlashValue>
              </Badge>
            )}

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
