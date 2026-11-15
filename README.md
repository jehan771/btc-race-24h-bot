# btc-race-24h-bot

[![make.fun · btc-race-24h-20261115-0828](https://make.fun/badge/btc-race-24h-20261115-0828.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![rank](https://make.fun/badge/btc-race-24h-20261115-0828/jehan771/btc-race-24h-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![reward](https://make.fun/badge/btc-race-24h-20261115-0828/jehan771/btc-race-24h-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)

Capitulation-buyer bot for the [make.fun btc-race-24h-20261115-0828](https://make.fun/bounty/btc-race-24h-20261115-0828)
bounty: a long-only cbBTC/USDC trading bot on 1-minute bars, paper $1,000.

## Strategy

Buy the washout, nothing else:

- **Entry** — when flat, the latest close is at least **7.5% below the session
  high** and **RSI(14) < 40**, buy with **95% of equity**.
- **Exit** — take profit **+3%**, stop loss **-1.5%**, or **max hold 120 bars**,
  whichever comes first. One position at a time.
- **Halt** — a **20% drawdown** from the equity peak closes any open position
  and stops trading for the rest of the window.

The dev window falls 4%, so dip-buying without a real washout loses; the
capitulation filter is the whole edge. Few trades, positive edge.

## Layout

- `main.py` — the bot (Python 3.13, standard library only), speaking
  `agent-fun/bars-replay/v1` NDJSON over stdin/stdout.
- `vendor/makefun_bars.py` — byte-identical copy of the kit's Python SDK shim.

## Run

```sh
python3 -P -s main.py
```
