"""SQLite-backed persistence for the live/paper trading dashboard.

Separate from tradingbot/core/state.py (JSON-based), which single-symbol
backtest/paper-trading scripts still use -- this is only for the portfolio
live-trading path that feeds the web dashboard, where per-symbol trade
history and PnL-over-time charts need real queries instead of re-parsing a
JSON blob on every request.
"""
from __future__ import annotations

import itertools
from pathlib import Path

from sqlalchemy import Column, Float, Integer, String, create_engine, delete, func, select
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from tradingbot.core.broker import PaperBroker, Position

Base = declarative_base()


class PositionRow(Base):
    __tablename__ = "positions"
    account = Column(String, primary_key=True)
    lot_id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)
    size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_time = Column(String, nullable=False)
    tag = Column(String, default="")


class TradeRow(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(String, nullable=False)
    lot_id = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    timestamp = Column(String, nullable=False)
    tag = Column(String, default="")
    reason = Column(String, nullable=True)
    pnl = Column(Float, nullable=True)


class CashBalanceRow(Base):
    __tablename__ = "cash_balance"
    account = Column(String, primary_key=True)
    cash = Column(Float, nullable=False)
    fee_pct = Column(Float, nullable=False)
    slippage_pct = Column(Float, nullable=False)


class PortfolioSnapshotRow(Base):
    __tablename__ = "portfolio_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    equity = Column(Float, nullable=False)
    cash = Column(Float, nullable=False)


class SymbolSnapshotRow(Base):
    __tablename__ = "symbol_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    mark_price = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    total_pnl = Column(Float, nullable=False)


def get_session_factory(db_path: Path) -> sessionmaker:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    # WAL instead of the default rollback journal: readers (the dashboard)
    # don't block writers (the bot processes), and it's far more resilient
    # to a process being killed mid-write -- the default journal mode
    # corrupted this database once already under concurrent access.
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def restore_positions(broker, session: Session, account: str) -> None:
    """Restore positions/trade-count bookkeeping onto an already-constructed
    broker (PaperBroker or ExchangeBroker) from persisted state. Separate
    from `load_broker` so ExchangeBroker -- which needs its own constructor
    args (API credentials) instead of a cash figure -- can reuse this.
    """
    positions = session.execute(select(PositionRow).where(PositionRow.account == account)).scalars().all()
    for p in positions:
        broker.positions[p.lot_id] = Position(p.lot_id, p.symbol, p.size, p.entry_price, p.entry_time, p.tag)

    # Resume the lot counter above the highest id seen so far, same reasoning as PaperBroker.from_dict.
    used = [int(lot_id.rsplit("-", 1)[-1]) for lot_id in broker.positions]
    broker._lot_counter = itertools.count(max(used, default=0) + 1)

    broker._db_persisted_trade_count = session.execute(
        select(func.count()).select_from(TradeRow).where(TradeRow.account == account)
    ).scalar_one()


def load_broker(session: Session, account: str, initial_cash: float, fee_pct: float, slippage_pct: float) -> PaperBroker:
    row = session.get(CashBalanceRow, account)
    if row is None:
        broker = PaperBroker(cash=initial_cash, fee_pct=fee_pct, slippage_pct=slippage_pct)
    else:
        broker = PaperBroker(cash=row.cash, fee_pct=row.fee_pct, slippage_pct=row.slippage_pct)
    restore_positions(broker, session, account)
    return broker


def save_broker(session: Session, account: str, broker: PaperBroker) -> None:
    existing = session.get(CashBalanceRow, account)
    if existing is None:
        session.add(CashBalanceRow(account=account, cash=broker.cash, fee_pct=broker.fee_pct, slippage_pct=broker.slippage_pct))
    else:
        existing.cash = broker.cash

    session.execute(delete(PositionRow).where(PositionRow.account == account))
    for p in broker.positions.values():
        session.add(
            PositionRow(
                account=account, lot_id=p.lot_id, symbol=p.symbol, size=p.size,
                entry_price=p.entry_price, entry_time=str(p.entry_time), tag=p.tag,
            )
        )

    persisted = getattr(broker, "_db_persisted_trade_count", 0)
    for trade in broker.trade_log[persisted:]:
        session.add(
            TradeRow(
                account=account, lot_id=trade["lot_id"], symbol=trade["symbol"], side=trade["side"],
                price=trade["price"], size=trade["size"], timestamp=trade["timestamp"], tag=trade.get("tag", ""),
                reason=trade.get("reason"), pnl=trade.get("pnl"),
            )
        )
    broker._db_persisted_trade_count = len(broker.trade_log)
    session.commit()


def append_portfolio_snapshot(session: Session, account: str, timestamp: str, equity: float, cash: float) -> None:
    session.add(PortfolioSnapshotRow(account=account, timestamp=timestamp, equity=equity, cash=cash))
    session.commit()


def append_symbol_snapshot(
    session: Session, account: str, symbol: str, timestamp: str,
    mark_price: float, realized_pnl: float, unrealized_pnl: float,
) -> None:
    session.add(
        SymbolSnapshotRow(
            account=account, symbol=symbol, timestamp=timestamp, mark_price=mark_price,
            realized_pnl=realized_pnl, unrealized_pnl=unrealized_pnl, total_pnl=realized_pnl + unrealized_pnl,
        )
    )
    session.commit()


def get_portfolio_history(session: Session, account: str) -> list[dict]:
    rows = session.execute(
        select(PortfolioSnapshotRow).where(PortfolioSnapshotRow.account == account).order_by(PortfolioSnapshotRow.id)
    ).scalars().all()
    return [{"timestamp": r.timestamp, "equity": r.equity, "cash": r.cash} for r in rows]


def get_symbol_history(session: Session, account: str, symbol: str) -> list[dict]:
    rows = session.execute(
        select(SymbolSnapshotRow)
        .where(SymbolSnapshotRow.account == account, SymbolSnapshotRow.symbol == symbol)
        .order_by(SymbolSnapshotRow.id)
    ).scalars().all()
    return [
        {
            "timestamp": r.timestamp, "mark_price": r.mark_price, "realized_pnl": r.realized_pnl,
            "unrealized_pnl": r.unrealized_pnl, "total_pnl": r.total_pnl,
        }
        for r in rows
    ]


def get_trades_for_symbol(session: Session, account: str, symbol: str) -> list[dict]:
    rows = session.execute(
        select(TradeRow)
        .where(TradeRow.account == account, TradeRow.symbol == symbol)
        .order_by(TradeRow.id.desc())
    ).scalars().all()
    return [
        {
            "side": r.side, "price": r.price, "size": r.size, "timestamp": r.timestamp,
            "reason": r.reason, "pnl": r.pnl,
        }
        for r in rows
    ]


def get_symbols(session: Session, account: str) -> list[str]:
    rows = session.execute(
        select(TradeRow.symbol).where(TradeRow.account == account).distinct()
    ).scalars().all()
    return sorted(rows)
