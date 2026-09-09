import { Fragment, useEffect, useMemo, useState } from "react"

import { CoinCard } from "@/components/CoinCard"
import { FlashValue } from "@/components/FlashValue"
import { OverviewCard } from "@/components/OverviewCard"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  fetchAccounts,
  fetchFuturesWalletBalance,
  fetchStatus,
  fetchWalletBalance,
  type StrategyId,
} from "@/lib/api"
import { formatUsdt } from "@/lib/format"
import { GROUPS, STRATEGIES } from "@/lib/strategies"
import { usePolling } from "@/lib/usePolling"

const POLL_MS = 30_000

function initialParams(): { strategy: StrategyId | null; account: string | null } {
  const params = new URLSearchParams(window.location.search)
  const strategy = params.get("strategy")
  const account = params.get("account")
  return {
    strategy: strategy && STRATEGIES.some((s) => s.id === strategy) ? (strategy as StrategyId) : null,
    account,
  }
}

export function App() {
  const { data: accounts } = usePolling(fetchAccounts, 60_000)
  const { data: wallet } = usePolling(fetchWalletBalance, 60_000)
  const { data: futuresWallet } = usePolling(fetchFuturesWalletBalance, 60_000)

  // A leaderboard row link ("as if using the selector") lands here via
  // ?strategy=X&account=Y instead of always starting on Grid.
  const [initial] = useState(initialParams)
  const [strategy, setStrategy] = useState<StrategyId>(initial.strategy ?? "grid")
  const currentStrategy = useMemo(() => STRATEGIES.find((s) => s.id === strategy), [strategy])
  const accountsForStrategy = useMemo(
    () => (accounts ?? []).filter((a) => a.strategy === strategy),
    [accounts, strategy]
  )

  const [account, setAccount] = useState<string | null>(initial.account)
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
            <Button variant="outline" size="sm" render={<a href="/leaderboard" />}>
              Leaderboard
            </Button>

            <Select value={strategy} onValueChange={(value) => value && setStrategy(value as StrategyId)}>
              <SelectTrigger className="w-[260px]">
                <SelectValue>{(value: StrategyId) => STRATEGIES.find((s) => s.id === value)?.label ?? value}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {GROUPS.map((group, i) => (
                  <Fragment key={`${group.key}-${group.frequency}`}>
                    {i > 0 && <SelectSeparator />}
                    <SelectGroup>
                      <SelectLabel>{group.label}</SelectLabel>
                      {STRATEGIES.filter((s) => s.category === group.key && s.frequency === group.frequency).map((s) => (
                        <SelectItem key={s.id} value={s.id}>
                          {s.label}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </Fragment>
                ))}
              </SelectContent>
            </Select>

            {accountsForStrategy.length > 1 && account && (
              <Select value={account} onValueChange={(value) => value && setAccount(value)}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue>{(value: string) => accountsForStrategy.find((a) => a.id === value)?.label ?? value}</SelectValue>
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
