# trading-bot

Modular crypto trading bot. Backtest and paper-trading only -- no exchange
API keys with order permissions are used anywhere in this repo, and no real
orders are ever placed.

## Architecture

Every strategy implements one method:

```python
class Strategy(ABC):
    def on_bar(self, bar: Bar, broker: PaperBroker) -> None: ...
```

A strategy owns all of its logic and state (e.g. which grid levels are
filled) and calls `broker.buy(...)` / `broker.sell(...)` itself when it
decides to trade. The engine (`tradingbot/core/backtest.py` for backtests,
`tradingbot/core/live.py` for paper trading) just calls `on_bar` once per bar
and keeps the books -- so a strategy behaves identically in both, and adding
a new one never requires touching the engine.

```
tradingbot/
  core/
    types.py     # Bar
    broker.py    # PaperBroker: multi-lot simulated ledger (fees, slippage, JSON persistence)
    backtest.py  # feeds cached OHLCV bars to a strategy, tracks equity curve
    live.py      # polls recent OHLCV bars on a timer, feeds them the same way
    state.py     # save/load a PaperBroker's ledger to paper_state/<account>.json
  data/
    fetch.py     # ccxt OHLCV fetch + parquet cache (public endpoints only)
  strategies/
    base.py      # the Strategy contract
    grid.py       # GridStrategy + GridConfig
    __init__.py  # STRATEGIES registry: {"grid": (GridConfig, GridStrategy), ...}
cli/
  fetch_data.py  # cache OHLCV history for a config's symbol
  backtest.py    # run a strategy against cached history
  paper_trade.py # run a strategy against live-polled data (simulated fills)
config/
  grid_btc_usdt.yaml
tests/
```

## Adding a new strategy

1. `tradingbot/strategies/my_strategy.py`: a `MyConfig` dataclass (needs at
   least `symbol`, `exchange`, `timeframe`, `fee_pct`, `slippage_pct`, and a
   `starting_cash` property) and a `MyStrategy(Strategy)` class with
   `on_bar` and a `from_config` classmethod.
2. Register it in `tradingbot/strategies/__init__.py`:
   `STRATEGIES["my_strategy"] = (MyConfig, MyStrategy)`.
3. Add `config/my_strategy_xyz.yaml` with `strategy: my_strategy` plus your
   config fields.
4. Write `tests/test_my_strategy.py` -- construct the strategy directly, feed
   it hand-built `Bar`s and a fresh `PaperBroker`, assert on
   `broker.positions` / `broker.trade_log`. No mocking needed since the
   strategy never touches the network itself.

`cli/backtest.py` and `cli/paper_trade.py` work for any registered strategy
without changes.

## Grid trading strategy

`GridStrategy` splits a price range into `num_grids` slots. Each slot buys
at its lower boundary and sells at its upper boundary, then resets to buy
again -- it profits from price oscillating inside the range, independent of
trend. See `config/grid_btc_usdt.yaml` for the tunable parameters.

## Quickstart

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python cli/fetch_data.py config/grid_btc_usdt.yaml
python cli/backtest.py config/grid_btc_usdt.yaml

python cli/paper_trade.py config/grid_btc_usdt.yaml --once   # single pass
python cli/paper_trade.py config/grid_btc_usdt.yaml           # loop, poll every 5 min

pytest
```

## Portfolio mode + live dashboard

`cli/portfolio_paper_trade.py` runs several strategies against ONE shared
cash pool (instead of each with its own capital) and persists state to a
SQLite database (`paper_state/trading.db`) instead of a JSON file, so a
Flask API (`webapp/app.py`) can serve per-symbol trade history and PnL
charts to a React + shadcn/ui dashboard (`dashboard/`).

```bash
python cli/fetch_data.py config/grid_link_usdt.yaml   # per symbol, for backtests/sweeps
python cli/portfolio_backtest.py --total-cash 500 config/grid_*.yaml
python cli/portfolio_sweep.py --total-cash 500 --num-grids 10,20,30 --risk-pct 0.005,0.01,0.02 config/grid_*.yaml

python cli/portfolio_paper_trade.py --total-cash 500 --account alts8 config/grid_*.yaml
```

## Live order execution (testnet)

`tradingbot/core/exchange_broker.py`'s `ExchangeBroker` places REAL orders
against an authenticated exchange account -- Binance Spot Testnet by
default (fake funds, real order API/execution semantics). Same
buy/sell/equity interface as `PaperBroker` (it subclasses it), so
`GridStrategy` runs unmodified against either. `cash` is a self-tracked
budget separate from the account's real wallet balance, so the bot only
ever touches the slice of the account you tell it to.

```bash
cp .env.example .env   # fill in BINANCE_TESTNET_API_KEY / _SECRET (testnet.binance.vision)

python cli/portfolio_paper_trade.py --testnet --account alts8_testnet \
    --total-cash 500 --risk-pct 0.03 config/grid_*.yaml
```

Real money execution is intentionally not implemented -- going from testnet
to a real account only needs `testnet=False` and a real API key, but that
should stay a deliberate, explicit step, not something added proactively.

## Running with Docker

```bash
cp .env.example .env   # only needed for --testnet
docker compose up -d --build
```

Two services, sharing `./paper_state` as a volume so both see the same
SQLite database:
- `bot` -- runs `cli/portfolio_paper_trade.py` on a loop (edit the command
  in `docker-compose.yml` to change symbols/account/budget)
- `webapp` -- serves the dashboard + API via gunicorn on port 8080

On a Raspberry Pi: same commands, just `git pull` + `docker compose up -d
--build` again to deploy an update. Port-forwarding/domain/TLS on top of
port 8080 is on you. `docker-compose.yml` runs 5 grid bots (staggered
500/1k/2k/4k/8k budgets) + 10 coinflip bots (see below) + `webapp` -- edit
or comment out services there to run fewer.

## Coinflip strategy (for laughs)

`tradingbot/strategies/coinflip.py`: every new candle, flip a coin for
long/short and a coin for leverage; while a position is open, flip a coin
each new candle whether to close it. No signal, no edge -- a benchmark for
"what does doing nothing smarter than chance look like", running real
long/short positions with real leverage.

Real long/short + leverage needs futures, which a spot ledger can't
represent -- so this uses `tradingbot/core/futures_broker.py`
(`FuturesBroker`) against Binance USDT-M Futures **Demo Trading**
(demo.binance.com; the older futures testnet sandbox mode is deprecated),
not `PaperBroker`/`ExchangeBroker`. Same self-tracked-budget principle as
`ExchangeBroker`: `--total-cash` caps what a bot uses of the demo account's
real balance, independent of the account's actual size.

```bash
# .env needs BINANCE_DEMO_FUTURES_KEY / _SECRET (from demo.binance.com)
python cli/coinflip_trade.py --account coinflip_usdt_500 --total-cash 500 \
    --margin-asset USDT --leverage 1,2,3,5 --margin-pct 0.03 \
    LINK/USDT TIA/USDT DOT/USDT ETH/USDT WIF/USDT AVAX/USDT SOL/USDT ARB/USDT
```

`--margin-asset` picks which futures market to trade (e.g. `USDT` -> the
`LINK/USDT:USDT` perpetual, `USDC` -> `LINK/USDC:USDC`) -- a symbol with no
market in that margin asset (DOT has no USDC perpetual) is skipped, not
fatal. The dashboard's strategy dropdown (Grid / Coinflip) switches between
them; each budget tier is its own account/ledger.

`--total-cash` is a self-tracked budget cap, not segregated real funds --
every bot in a margin group draws on the same demo wallet balance. Keep the
sum of tiers within a margin group at or below that wallet's actual balance
(`docker-compose.yml` stages 500/750/1,000/1,250/1,500 per group, summing to
5,000 USDT and 5,000 USDC to match the demo account), or bots will start
hitting real "insufficient balance" errors once several are in positions at
once.
