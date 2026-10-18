"""Daily portfolio check -> Telegram.

Rule-based (no AI). Flags technical events for each holding and sends a digest.
Env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID. Without them it prints to console.
"""
import datetime as dt
import os
import sys

import pandas as pd
import requests
import yfinance as yf

# ---------------------------------------------------------------- holdings
ETFS = """SPY VOO IVV QQQ IWM IYY IVW NOBL KNG XLE XHB XLB XLC XLF XLRE XLV SDY SPLG
FEZ MCHI FXI AIQ PPA ESGG LVHI IJS PDI BITS SFY URA IAU AAAU GOLD
BITB BRRR EZBC FETH IBIT MAXI""".split()

STOCKS = """AAPL AMD GOOG GOOGL ASML COST DELL PLTR SHOP TSLA V ARCC COIN EPR ESLT GEV MAIN
NDAQ NLR PANW PINS SOC TEM TGTX VIST VRNS PLD LLY VZ XOM MDB ATNM INTC SPXL AMZN ANET
KTOS APP NVDA MTZ MARA PGY SAFX SPGI""".split()

CRYPTO = {"BTC": "BTC-USD"}  # your label -> Yahoo symbol

# Thresholds (negative = drop)
DAY_DROP = {"stock": -0.06, "etf": -0.03, "crypto": -0.09}
WEEK_DROP = {"stock": -0.12, "etf": -0.06, "crypto": -0.18}

# Tickers you previously flagged; shown with a marker in the digest
PRIOR_URGENT = {"TSLA", "AAPL", "PINS", "TGTX", "VIST", "ATNM"}
PRIOR_WATCH = {"PLTR", "PANW", "GOOG", "GOOGL"}


def build_universe():
    kinds = {}
    for t in ETFS:
        kinds[t] = "etf"
    for t in STOCKS:
        kinds.setdefault(t, "stock")
    for label in CRYPTO:
        kinds[label] = "crypto"
    return kinds


def yahoo_symbol(t):
    return CRYPTO.get(t, t)


def tag(t):
    if t in PRIOR_URGENT:
        return f"{t} [prev. urgent]"
    if t in PRIOR_WATCH:
        return f"{t} [prev. watch]"
    return t


def analyse(close: pd.Series, kind: str):
    """Return (events, ongoing) for one price series."""
    close = close.dropna()
    if len(close) < 60:
        return [], []
    last, prev = close.iloc[-1], close.iloc[-2]
    day = last / prev - 1
    week = last / close.iloc[-6] - 1 if len(close) >= 6 else 0.0
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    high52 = close.iloc[-252:].max()
    dd = last / high52 - 1

    events, ongoing = [], []

    if day <= DAY_DROP[kind]:
        events.append(f"1-day drop {day:+.1%}")
    if week <= WEEK_DROP[kind]:
        events.append(f"5-day drop {week:+.1%}")

    if len(close) >= 201 and not pd.isna(sma200.iloc[-2]):
        if prev >= sma200.iloc[-2] and last < sma200.iloc[-1]:
            events.append(f"closed below 200-day avg ({sma200.iloc[-1]:.2f})")
        if sma50.iloc[-2] >= sma200.iloc[-2] and sma50.iloc[-1] < sma200.iloc[-1]:
            events.append("death cross (50-day under 200-day)")
        if last < sma200.iloc[-1] * 0.90:
            ongoing.append(f"{(last / sma200.iloc[-1] - 1):+.0%} vs 200-day")
    if dd <= (-0.20 if kind == "etf" else -0.35):
        ongoing.append(f"{dd:+.0%} from 52w high")
    return events, ongoing


def headlines(symbol, n=2):
    try:
        items = yf.Ticker(symbol).news or []
    except Exception:
        return []
    out = []
    for it in items[:n]:
        title = it.get("title") or (it.get("content") or {}).get("title")
        if title:
            out.append(title)
    return out


def send_telegram(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print(text)
        return
    for i in range(0, len(text), 3900):
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat, "text": text[i : i + 3900]},
            timeout=30,
        )
        r.raise_for_status()


def main():
    kinds = build_universe()
    symbols = sorted({yahoo_symbol(t) for t in kinds})
    data = yf.download(
        symbols, period="15mo", interval="1d", auto_adjust=True,
        group_by="ticker", progress=False, threads=True,
    )

    alerts, ongoing_all, missing = [], [], []
    for t, kind in sorted(kinds.items()):
        sym = yahoo_symbol(t)
        try:
            close = data[sym]["Close"]
        except Exception:
            missing.append(t)
            continue
        events, ongoing = analyse(close, kind)
        if events:
            alerts.append((t, sym, events))
        if ongoing:
            ongoing_all.append((t, ongoing))
        if close.dropna().empty:
            missing.append(t)

    today = dt.date.today().isoformat()
    lines = [f"Portfolio check {today}"]

    if len(set(missing)) > len(kinds) / 2:
        lines.append("\nDATA FETCH FAILED for most tickers (Yahoo Finance problem). "
                     "Today's check is NOT reliable; no conclusions drawn.")
    elif alerts:
        lines.append(f"\nNEW FLAGS ({len(alerts)}):")
        for t, sym, events in alerts:
            lines.append(f"- {tag(t)}: " + "; ".join(events))
            for h in headlines(sym):
                lines.append(f"    news: {h}")
    else:
        lines.append("\nNo new flags today.")

    # Ongoing weakness list: Mondays only (Bangkok mornings after Friday's close)
    if dt.date.today().weekday() == 0 and ongoing_all:
        lines.append("\nWEEKLY - still weak:")
        for t, notes in ongoing_all:
            lines.append(f"- {tag(t)}: " + ", ".join(notes))

    if missing:
        lines.append("\nNo data for: " + ", ".join(sorted(set(missing))))

    lines.append("\nRule-based technical flags only, not advice.")
    send_telegram("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
