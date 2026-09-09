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
    types.py            # Bar
    broker.py           # PaperBroker: multi-lot simulated ledger (fees, slippage, JSON persistence)
    exchange_broker.py  # ExchangeBroker: real spot orders (subclasses PaperBroker)
    futures_broker.py   # FuturesBroker: real long/short + leverage, multi-lot per symbol
    backtest.py         # feeds cached OHLCV bars to a strategy, tracks equity curve
    live.py             # legacy single-symbol paper-trading loop (see "Legacy" below)
    portfolio_live.py   # multi-strategy/shared-cash live loop (run_once/run_loop)
    coinflip_live.py    # same, but for FuturesBroker's side-aware PnL
    state.py            # save/load a PaperBroker's ledger to paper_state/<account>.json (legacy path)
    db.py               # SQLite persistence for the portfolio/live dashboard path
  data/
    fetch.py     # ccxt OHLCV fetch + parquet cache (public endpoints), fetch_latest_bars for fleet dedup
  strategies/
    base.py        # the Strategy contract: on_bar(bar, broker) -> None
    single_lot.py  # SingleLotStrategy: shared multi-lot-per-symbol mechanics for every long/flat strategy
    indicators.py  # EMA/RSI/MACD/ATR/Donchian/BollingerBands -- small streaming indicators
    grid.py         # GridStrategy + GridConfig (its own multi-lot/slot shape)
    coinflip.py     # CoinflipStrategy (futures, its own multi-lot shape + per-lot TP/SL)
    ma_crossover.py, donchian_breakout.py, rsi_reversion.py, bollinger_reversion.py,
    macd_momentum.py, atr_breakout.py, volume_spike.py, relative_momentum.py, buy_and_hold.py,
    moon_phase.py, friday13.py, prime_number.py, contrarian_self.py, fomo_bot.py,
    diamond_hands.py, buy_high_sell_low.py, zodiac.py, hash_sentiment.py
    __init__.py  # STRATEGIES registry: {"grid": (GridConfig, GridStrategy), ...}
cli/
  fetch_data.py          # cache OHLCV history for a config's symbol
  backtest.py            # run a strategy against cached history
  paper_trade.py         # legacy single-symbol live/paper loop (see "Legacy" below)
  portfolio_paper_trade.py  # single-account, multi-strategy/shared-cash CLI (manual/debug use)
  coinflip_trade.py      # single-account coinflip CLI (manual/debug use)
  spot_fleet.py          # PRODUCTION: every spot-side account in one process, see "Fleet processes"
  futures_fleet.py       # PRODUCTION: every coinflip account in one process
config/
  grid_btc_usdt.yaml       # legacy single-symbol quickstart config
  grid_<coin>_usdt.yaml    # per-symbol grid configs (price range genuinely differs per symbol)
  <strategy>.yaml          # one shared config per non-grid strategy, with its own symbols: list
  fleet_spot.yaml          # every spot_fleet.py account: {account, config(s), total_cash, ...}
  fleet_futures.yaml       # every futures_fleet.py account
tests/
```

## Adding a new strategy

1. `tradingbot/strategies/my_strategy.py`: a `MyConfig` dataclass (needs at
   least `symbol`, `exchange`, `timeframe`, `fee_pct`, `slippage_pct`, and a
   `starting_cash` property) and a `MyStrategy` class with `on_bar` and a
   `from_config` classmethod. For a long/flat strategy (0-or-several lots,
   never short), subclass `SingleLotStrategy` (`tradingbot/strategies/single_lot.py`)
   and just call `self._enter(bar, broker, tag)` / `self._exit(bar, broker, reason)`
   -- entering, exiting, accumulating up to `max_concurrent` lots over
   several candles, and surviving a restart are all handled once, there.
   Write a short, human-readable `tag` describing what the strategy is
   doing (e.g. `"rsi_reversion:rsi24.3"`) -- the dashboard shows it verbatim
   in a generic "Info" column with zero extra UI code.
2. Register it in `tradingbot/strategies/__init__.py`:
   `STRATEGIES["my_strategy"] = (MyConfig, MyStrategy)`.
3. Add `config/my_strategy.yaml` with `strategy: my_strategy`, your config
   fields, and a `symbols:` list (one shared file for every symbol, since
   params usually don't vary per symbol -- see any existing non-grid config).
   Grid is the exception: its price range genuinely differs per symbol, so
   it still uses one yaml file per symbol (`configs:` list, not `config:`).
4. Write `tests/test_my_strategy.py` -- construct the strategy directly, feed
   it hand-built `Bar`s and a fresh `PaperBroker`, assert on
   `broker.positions` / `broker.trade_log`. No mocking needed since the
   strategy never touches the network itself.

`cli/backtest.py`, `cli/portfolio_paper_trade.py`, `cli/spot_fleet.py`, etc.
all work for any registered strategy without changes.

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

## Live order execution (Binance Demo Trading)

Every strategy that places real orders does so against **one Binance Demo
Trading account** (demo.binance.com) -- not the older, separate Spot
Testnet product. `ccxt.binance` (spot) and `ccxt.binanceusdm` (futures)
both expose the same `enable_demo_trading(True)` method, keyed by the same
API key/secret, so one credential pair covers everything: grid and every
long/flat real/joke strategy trade the account's **spot** balance via
`tradingbot/core/exchange_broker.py`'s `ExchangeBroker` (subclasses
`PaperBroker` -- same buy/sell/equity interface, so any spot strategy runs
unmodified against either), and Coinflip trades the account's **futures**
balance via `tradingbot/core/futures_broker.py`'s `FuturesBroker`. Binance
keeps the spot and futures balances as two separate pools even under one
account, so there are two numbers, not one.

`cash` on either broker is a self-tracked budget, separate from the
account's real balance -- the bot only ever touches the slice you tell it
to. **This is a real constraint, not a formality**: every account sharing
one of these two pools has its own `--total-cash`/`total_cash:`, and the
*sum* of every account's nominal budget in a pool must stay at or below
that pool's actual real balance (5,000 USDT + 5,000 USDC on this project's
demo account) -- overcommitting it once already caused real "insufficient
balance" errors this project had to fix. See `config/fleet_spot.yaml` /
`config/fleet_futures.yaml` for the current allocation:

Every strategy gets exactly one account at 500 -- no staggered budget
tiers (an earlier version of this project staggered Grid/Coinflip across
several budget tiers; this project deliberately flattened that to one
account per strategy instead):

- **Spot pool (USDT)**: Grid + the 9 real strategies = 10 accounts x 500 =
  5,000 of 5,000 -- exactly at the boundary, zero buffer, by choice.
- **Spot pool (USDC)**: the 9 joke strategies = 9 accounts x 500 = 4,500 of 5,000.
- **Futures pool (USDT / USDC)**: one Coinflip account per margin asset x
  500 = 500 of 5,000 each.

```bash
cp .env.example .env   # fill in BINANCE_DEMO_KEY / _SECRET (from demo.binance.com)

python cli/portfolio_paper_trade.py --demo --account alts8_demo \
    --total-cash 500 --risk-pct 0.03 config/grid_*.yaml
```

## Fleet processes

Every account above used to be its own OS process/Docker container -- at
20 strategies × several budget tiers, that meant dozens of containers each
importing their own copy of pandas/numpy/ccxt/sqlalchemy (~260-300MB each)
and each redundantly re-authenticating and re-fetching public OHLCV data
that every other account trading the same symbol was ALSO fetching, every
poll cycle. `cli/spot_fleet.py` and `cli/futures_fleet.py` replace that
with **one process per real credential group** (spot demo, futures demo):
one shared, already-authenticated `ccxt` client per process, one bar-fetch
per unique `(symbol, timeframe)` per poll cycle shared across every account
trading that symbol (`tradingbot/data/fetch.py`'s `fetch_latest_bars`), and
one `ExchangeBroker`/`FuturesBroker` + `Strategy` instance per account
(never shared across accounts -- only the client and the fetched bars are).
Each account's own cash/positions/trade log stay fully isolated; the SQLite
schema (`tradingbot/core/db.py`) is keyed purely by an `account` string, so
it doesn't care whether one process or twenty wrote a given account's rows.

`cli/portfolio_paper_trade.py` and `cli/coinflip_trade.py` (single-account)
still exist for local debugging/manual runs -- `docker-compose.yml` just
doesn't use them anymore.

## Running with Docker

```bash
cp .env.example .env
docker compose up -d --build
```

Three services, sharing `./paper_state` as a volume so all three see the
same SQLite database:
- `spot-fleet` -- runs `cli/spot_fleet.py config/fleet_spot.yaml` (grid + every real/joke strategy)
- `futures-fleet` -- runs `cli/futures_fleet.py config/fleet_futures.yaml` (coinflip)
- `webapp` -- serves the dashboard + API via gunicorn on port 8080

On a Raspberry Pi: same commands, just `git pull` + `docker compose up -d
--build` again to deploy an update. Port-forwarding/domain/TLS on top of
port 8080 is on you.

## Real strategies (10, including Grid)

All long/flat, spot side of the demo account, built on `SingleLotStrategy`
(except Grid, which has its own slot-indexed shape). Each can hold several
concurrent lots on a symbol (accumulated across separate candles while its
signal stays true, closed together once it flips) instead of being capped
at one trade for its whole lifetime.

| Strategy | Idea |
|---|---|
| Grid | Buy/sell a fixed price ladder, profits from oscillation |
| MA Crossover | Long while EMA9 > EMA21 |
| Donchian Breakout | Long on a close above the prior N-bar high |
| RSI Reversion | Long when RSI < 30, exit above 60 |
| Bollinger Reversion | Buy the lower band, exit at the middle |
| MACD Momentum | Long on a bullish MACD/signal crossover |
| ATR Breakout | Volatility breakout entry, ATR trailing stop |
| Volume Spike | Long on a volume thrust with a green candle |
| Relative Momentum | Long when N-bar return is positive and accelerating |
| Buy & Hold | Buys once (well, up to `max_concurrent`), never sells -- the benchmark |

## Joke strategies (10, including Coinflip)

Also spot side of the demo account (Coinflip is the only leveraged/futures
strategy) -- for laughs, but each still writes a short, human-readable tag
so what it's doing is visible on the dashboard.

`tradingbot/strategies/coinflip.py`: every new candle, flip a coin for
long/short, a coin for leverage, and a coin for a take-profit/stop-loss
band (several concurrent lots allowed, up to `max_concurrent`, each with
its own independently-coinflipped side/leverage/TP/SL); each open lot
closes once price crosses its own TP/SL, or via a much smaller "impatience"
coinflip each candle otherwise. Real long/short + leverage needs futures,
which a spot ledger can't represent -- so this is the one strategy on
`FuturesBroker`, not `ExchangeBroker`.

| Strategy | Idea |
|---|---|
| Coinflip | Random side/leverage/TP-SL, real leverage, for laughs |
| Vollmond-Trader | Long during a full moon (computed from the date), flat otherwise |
| Freitag-13-Trader | Closes out on Friday the 13th, holds otherwise |
| Primzahl-Trader | Only holds on a prime day-of-month |
| Contrarian-Self | Holds a fixed number of bars, then skips its next entry after a loss |
| FOMO-Bot | Only buys after a pump, sells when momentum stalls |
| Diamond-Hands | Buys every dip, literally never sells |
| Buy-High-Sell-Low | Chases new highs, panic-sells on the next red candle |
| Sternzeichen-Trader | Long/flat by a fixed table keyed on the zodiac sign |
| Hash-Sentiment-Bot | Pretends to read sentiment, actually hashes the bar's own OHLCV |

```bash
# .env needs BINANCE_DEMO_KEY / _SECRET (from demo.binance.com)
python cli/coinflip_trade.py --account coinflip_usdt_500 --total-cash 500 \
    --margin-asset USDT --leverage 1,2,3,5 --margin-pct 0.03 --max-concurrent 3 \
    LINK/USDT TIA/USDT DOT/USDT ETH/USDT WIF/USDT AVAX/USDT SOL/USDT ARB/USDT
```

`--margin-asset` picks which futures market to trade (e.g. `USDT` -> the
`LINK/USDT:USDT` perpetual, `USDC` -> `LINK/USDC:USDC`) -- a symbol with no
market in that margin asset is skipped, not fatal. The dashboard's strategy
dropdown switches between all 20 strategies; each budget tier is its own
account/ledger.

## Legacy single-symbol path

`cli/paper_trade.py` + `tradingbot/core/live.py` + `tradingbot/core/state.py`
(JSON-persisted, one strategy/one symbol/its own capital -- the very first
version of this project, before portfolio mode) still work and are covered
by the Quickstart above, but nothing in `docker-compose.yml` or the fleet
configs uses them anymore. Candidate for removal in a future cleanup pass;
left alone for now since they're still the simplest first-run path for
understanding the `Strategy` contract.
