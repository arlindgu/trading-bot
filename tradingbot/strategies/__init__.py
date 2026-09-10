from __future__ import annotations

from tradingbot.strategies.atr_flicker import AtrFlickerConfig, AtrFlickerStrategy
from tradingbot.strategies.base import Strategy
from tradingbot.strategies.bollinger_pinch import BollingerPinchConfig, BollingerPinchStrategy
from tradingbot.strategies.buy_and_hold import BuyAndHoldConfig, BuyAndHoldStrategy
from tradingbot.strategies.contrarian_self import ContrarianSelfConfig, ContrarianSelfStrategy
from tradingbot.strategies.diamond_hands import DiamondHandsConfig, DiamondHandsStrategy
from tradingbot.strategies.friday13 import Friday13Config, Friday13Strategy
from tradingbot.strategies.grid import GridConfig, GridStrategy
from tradingbot.strategies.hash_sentiment import HashSentimentConfig, HashSentimentStrategy
from tradingbot.strategies.herzschlag_bot import HerzschlagBotConfig, HerzschlagBotStrategy
from tradingbot.strategies.ma_crossover import MaCrossoverConfig, MaCrossoverStrategy
from tradingbot.strategies.macd_pulse import MacdPulseConfig, MacdPulseStrategy
from tradingbot.strategies.micro_donchian import MicroDonchianConfig, MicroDonchianStrategy
from tradingbot.strategies.pendel_bot import PendelBotConfig, PendelBotStrategy
from tradingbot.strategies.rsi_reversion import RsiReversionConfig, RsiReversionStrategy
from tradingbot.strategies.sekundenschlaf_bot import SekundenschlafBotConfig, SekundenschlafBotStrategy
from tradingbot.strategies.tick_momentum import TickMomentumConfig, TickMomentumStrategy
from tradingbot.strategies.trommelwirbel_bot import TrommelwirbelBotConfig, TrommelwirbelBotStrategy
from tradingbot.strategies.volume_pulse import VolumePulseConfig, VolumePulseStrategy
from tradingbot.strategies.wackelkontakt_bot import WackelkontaktBotConfig, WackelkontaktBotStrategy
from tradingbot.strategies.zappelphilipp import ZappelphilippConfig, ZappelphilippStrategy

# Registry a new strategy joins by adding one line here -- CLI scripts and
# tests never need to change to pick it up.
STRATEGIES: dict[str, tuple[type, type[Strategy]]] = {
    "grid": (GridConfig, GridStrategy),
    "ma_crossover": (MaCrossoverConfig, MaCrossoverStrategy),
    "rsi_reversion": (RsiReversionConfig, RsiReversionStrategy),
    "buy_and_hold": (BuyAndHoldConfig, BuyAndHoldStrategy),
    # High-frequency spot (1m bars), small position_pct per trade.
    "micro_donchian": (MicroDonchianConfig, MicroDonchianStrategy),
    "bollinger_pinch": (BollingerPinchConfig, BollingerPinchStrategy),
    "macd_pulse": (MacdPulseConfig, MacdPulseStrategy),
    "atr_flicker": (AtrFlickerConfig, AtrFlickerStrategy),
    "volume_pulse": (VolumePulseConfig, VolumePulseStrategy),
    "tick_momentum": (TickMomentumConfig, TickMomentumStrategy),
    "friday13": (Friday13Config, Friday13Strategy),
    "contrarian_self": (ContrarianSelfConfig, ContrarianSelfStrategy),
    "diamond_hands": (DiamondHandsConfig, DiamondHandsStrategy),
    "hash_sentiment": (HashSentimentConfig, HashSentimentStrategy),
    "zappelphilipp": (ZappelphilippConfig, ZappelphilippStrategy),
    # High-frequency joke spot (1m bars), small position_pct per trade.
    "pendel_bot": (PendelBotConfig, PendelBotStrategy),
    "herzschlag_bot": (HerzschlagBotConfig, HerzschlagBotStrategy),
    "wackelkontakt_bot": (WackelkontaktBotConfig, WackelkontaktBotStrategy),
    "sekundenschlaf_bot": (SekundenschlafBotConfig, SekundenschlafBotStrategy),
    "trommelwirbel_bot": (TrommelwirbelBotConfig, TrommelwirbelBotStrategy),
}


def load_strategy(name: str, raw_config: dict) -> tuple[object, Strategy]:
    config_cls, strategy_cls = STRATEGIES[name]
    cfg = config_cls(**raw_config)
    return cfg, strategy_cls.from_config(cfg)
