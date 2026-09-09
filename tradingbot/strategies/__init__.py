from __future__ import annotations

from tradingbot.strategies.atr_breakout import AtrBreakoutConfig, AtrBreakoutStrategy
from tradingbot.strategies.base import Strategy
from tradingbot.strategies.bollinger_reversion import BollingerReversionConfig, BollingerReversionStrategy
from tradingbot.strategies.buy_and_hold import BuyAndHoldConfig, BuyAndHoldStrategy
from tradingbot.strategies.buy_high_sell_low import BuyHighSellLowConfig, BuyHighSellLowStrategy
from tradingbot.strategies.contrarian_self import ContrarianSelfConfig, ContrarianSelfStrategy
from tradingbot.strategies.diamond_hands import DiamondHandsConfig, DiamondHandsStrategy
from tradingbot.strategies.donchian_breakout import DonchianBreakoutConfig, DonchianBreakoutStrategy
from tradingbot.strategies.fomo_bot import FomoBotConfig, FomoBotStrategy
from tradingbot.strategies.friday13 import Friday13Config, Friday13Strategy
from tradingbot.strategies.grid import GridConfig, GridStrategy
from tradingbot.strategies.hash_sentiment import HashSentimentConfig, HashSentimentStrategy
from tradingbot.strategies.ma_crossover import MaCrossoverConfig, MaCrossoverStrategy
from tradingbot.strategies.macd_momentum import MacdMomentumConfig, MacdMomentumStrategy
from tradingbot.strategies.moon_phase import MoonPhaseConfig, MoonPhaseStrategy
from tradingbot.strategies.prime_number import PrimeNumberConfig, PrimeNumberStrategy
from tradingbot.strategies.relative_momentum import RelativeMomentumConfig, RelativeMomentumStrategy
from tradingbot.strategies.rsi_reversion import RsiReversionConfig, RsiReversionStrategy
from tradingbot.strategies.volume_spike import VolumeSpikeConfig, VolumeSpikeStrategy
from tradingbot.strategies.zappelphilipp import ZappelphilippConfig, ZappelphilippStrategy
from tradingbot.strategies.zodiac import ZodiacConfig, ZodiacStrategy

# Registry a new strategy joins by adding one line here -- CLI scripts and
# tests never need to change to pick it up.
STRATEGIES: dict[str, tuple[type, type[Strategy]]] = {
    "grid": (GridConfig, GridStrategy),
    "ma_crossover": (MaCrossoverConfig, MaCrossoverStrategy),
    "donchian_breakout": (DonchianBreakoutConfig, DonchianBreakoutStrategy),
    "rsi_reversion": (RsiReversionConfig, RsiReversionStrategy),
    "bollinger_reversion": (BollingerReversionConfig, BollingerReversionStrategy),
    "macd_momentum": (MacdMomentumConfig, MacdMomentumStrategy),
    "atr_breakout": (AtrBreakoutConfig, AtrBreakoutStrategy),
    "volume_spike": (VolumeSpikeConfig, VolumeSpikeStrategy),
    "relative_momentum": (RelativeMomentumConfig, RelativeMomentumStrategy),
    "buy_and_hold": (BuyAndHoldConfig, BuyAndHoldStrategy),
    "moon_phase": (MoonPhaseConfig, MoonPhaseStrategy),
    "friday13": (Friday13Config, Friday13Strategy),
    "prime_number": (PrimeNumberConfig, PrimeNumberStrategy),
    "contrarian_self": (ContrarianSelfConfig, ContrarianSelfStrategy),
    "fomo_bot": (FomoBotConfig, FomoBotStrategy),
    "diamond_hands": (DiamondHandsConfig, DiamondHandsStrategy),
    "buy_high_sell_low": (BuyHighSellLowConfig, BuyHighSellLowStrategy),
    "zodiac": (ZodiacConfig, ZodiacStrategy),
    "hash_sentiment": (HashSentimentConfig, HashSentimentStrategy),
    "zappelphilipp": (ZappelphilippConfig, ZappelphilippStrategy),
}


def load_strategy(name: str, raw_config: dict) -> tuple[object, Strategy]:
    config_cls, strategy_cls = STRATEGIES[name]
    cfg = config_cls(**raw_config)
    return cfg, strategy_cls.from_config(cfg)
