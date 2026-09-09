import { useState } from "react"

import { CoinCard } from "@/components/CoinCard"
import { OverviewCard } from "@/components/OverviewCard"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { fetchAccounts, fetchStatus } from "@/lib/api"
import { usePolling } from "@/lib/usePolling"

const POLL_MS = 30_000
const FALLBACK_ACCOUNT = "alts8_testnet"

export function App() {
  const { data: accounts } = usePolling(fetchAccounts, 60_000)
  const [account, setAccount] = useState(FALLBACK_ACCOUNT)
  const { data: status, error } = usePolling(() => fetchStatus(account), POLL_MS, account)

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

          {accounts && accounts.length > 1 && (
            <Tabs value={account} onValueChange={(value) => setAccount(value as string)}>
              <TabsList>
                {accounts.map((a) => (
                  <TabsTrigger key={a.id} value={a.id}>
                    {a.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          )}
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

        {status && (
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
