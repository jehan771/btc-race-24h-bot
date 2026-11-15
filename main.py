"""Capitulation-buyer bot for make.fun btc-race-24h-20261115-0828.

Strategy: buy the capitulation. The bot watches the cbBTC/USDC 1-minute
bars (symbol CBBTC) and only buys when the market has washed out: the latest
close sits at least 7.5% below the session high AND RSI(14) is under 40.
One position at a time, 95% of equity per trade, take profit +3%, stop loss
-1.5%, max hold 120 bars, and a 20% equity-drawdown halt that closes any open
position and stops trading for the rest of the window.

Protocol: agent-fun/bars-replay/v1, NDJSON over stdin/stdout, via the kit
shim in vendor/makefun_bars.py (byte-identical copy of the kit SDK). Long
only, no shorts, no leverage. Deterministic: no wall clock, no randomness.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
RSI_PERIOD = 14
RSI_ENTRY_MAX = 40
DROP_BPS = 750            # entry: close >= 7.5% below the session high
BUY_WEIGHT_BPS = 9500     # 95% of equity per trade
TAKE_PROFIT_BPS = 300     # +3% from the entry reference price
STOP_LOSS_BPS = 150       # -1.5% from the entry reference price
MAX_HOLD_BARS = 120
HALT_DRAWDOWN_BPS = 2000  # 20% drawdown from the equity peak halts trading
MAX_SLIPPAGE_BPS = 100


class CapitulationBuyer:
    """Strategy state: session high, Wilder RSI(14), entry, equity peak."""

    def __init__(self):
        self.session_high = None   # highest bar high seen (price units)
        self.prev_close = None
        self._seed_changes = []    # (gain, loss) pairs while seeding RSI
        self.avg_gain = None       # Wilder-smoothed average gain
        self.avg_loss = None       # Wilder-smoothed average loss
        self.entry_ref = None      # close at the bar the buy was decided
        self.entry_seq = None      # seq of the bar the buy was decided
        self.peak_equity = None    # highest equity seen (quote units)
        self.halted = False

    def on_close(self, close):
        """Fold one close into the RSI(14) state (Wilder smoothing)."""
        if self.prev_close is None:
            self.prev_close = close
            return
        change = close - self.prev_close
        self.prev_close = close
        gain = change if change > 0 else 0
        loss = -change if change < 0 else 0
        if self.avg_gain is None:
            self._seed_changes.append((gain, loss))
            if len(self._seed_changes) == RSI_PERIOD:
                self.avg_gain = sum(g for g, _ in self._seed_changes) / RSI_PERIOD
                self.avg_loss = sum(l for _, l in self._seed_changes) / RSI_PERIOD
        else:
            self.avg_gain = (self.avg_gain * (RSI_PERIOD - 1) + gain) / RSI_PERIOD
            self.avg_loss = (self.avg_loss * (RSI_PERIOD - 1) + loss) / RSI_PERIOD

    def rsi(self):
        """Current RSI(14), or None until 14 closes have been seen."""
        if self.avg_loss is None:
            return None
        if self.avg_loss == 0:
            return 100.0
        rs = self.avg_gain / self.avg_loss
        return 100.0 - 100.0 / (1.0 + rs)


BOT = CapitulationBuyer()


def _sell_all(state):
    """One order selling the whole CBBTC holding, or [] when flat."""
    holding = state.positions.get(SYMBOL)
    if holding is None or holding.qty <= 0:
        return []
    return [{
        "side": "sell",
        "symbol": SYMBOL,
        "qty": holding.qty,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }]


def on_batch(state, batch):
    """Decide this batch's orders from the latest bar and the account."""
    for bar in batch.get("bars", []):
        if bar.get("symbol") != SYMBOL:
            continue
        high = int(bar["h"])
        if BOT.session_high is None or high > BOT.session_high:
            BOT.session_high = high
        BOT.on_close(int(bar["c"]))
    if state.warming_up:
        return []

    if BOT.peak_equity is None or state.equity > BOT.peak_equity:
        BOT.peak_equity = state.equity
    if BOT.peak_equity and state.equity * 10000 < BOT.peak_equity * (10000 - HALT_DRAWDOWN_BPS):
        BOT.halted = True
        return _sell_all(state)
    if BOT.halted:
        return []

    close = state.close(SYMBOL)
    if close is None:
        return []
    holding = state.positions.get(SYMBOL)
    if holding is not None and holding.qty > 0:
        if BOT.entry_ref is not None:
            if close * 10000 >= BOT.entry_ref * (10000 + TAKE_PROFIT_BPS):
                return _sell_all(state)
            if close * 10000 <= BOT.entry_ref * (10000 - STOP_LOSS_BPS):
                return _sell_all(state)
        if BOT.entry_seq is not None and state.seq - BOT.entry_seq >= MAX_HOLD_BARS:
            return _sell_all(state)
        return []

    rsi = BOT.rsi()
    if rsi is None or rsi >= RSI_ENTRY_MAX:
        return []
    if BOT.session_high is None:
        return []
    if close * 10000 > BOT.session_high * (10000 - DROP_BPS):
        return []
    notional = state.equity * BUY_WEIGHT_BPS // 10000
    notional = min(notional, state.cash, state.weight_room(SYMBOL))
    if notional <= 0:
        return []
    BOT.entry_ref = close
    BOT.entry_seq = state.seq
    return [{
        "side": "buy",
        "symbol": SYMBOL,
        "notional_quote_units": notional,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }]


if __name__ == "__main__":
    makefun_bars.run(on_batch)
