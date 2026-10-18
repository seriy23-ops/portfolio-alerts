# Portfolio alerts -> Telegram

Runs every weekday after the US close (05:00 Bangkok, Tue-Sat), checks every ticker in `alerts.py`,
and sends you a Telegram digest. Free, no AI, no server.

## What it flags
- 1-day drop: stocks -6%, ETFs -3%, crypto -9%
- 5-day drop: stocks -12%, ETFs -6%, crypto -18%
- Close below the 200-day average (the day it happens)
- Death cross (50-day falls under 200-day)
- Latest 2 headlines for any flagged ticker
- Mondays only: names still >10% under their 200-day, or deep below their 52-week high

Tickers you previously flagged (TSLA, AAPL, PINS, TGTX, VIST, ATNM; watch: PLTR, PANW, GOOG/GOOGL) are tagged.
Change the lists and thresholds at the top of `alerts.py`.

## Setup (about 10 minutes)

1. **Create the bot.** In Telegram, message **@BotFather**, send `/newbot`, follow the prompts.
   Copy the token it gives you.
2. **Get your chat ID.** Send any message to your new bot, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser. Find `"chat":{"id": 123456789`.
   That number is your chat ID.
3. **Create a private GitHub repo** and upload everything in this folder
   (keep the `.github/workflows/alerts.yml` path exactly).
4. **Add secrets.** Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:
   - `TELEGRAM_BOT_TOKEN` = the token
   - `TELEGRAM_CHAT_ID` = the number
5. **Test.** Repo -> Actions -> portfolio-alerts -> Run workflow. You should get a Telegram message in about a minute.

After that it runs by itself. Never paste the bot token into the code or share it.

## Local test
```
pip install -r requirements.txt
python alerts.py            # prints to console
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python alerts.py   # sends to Telegram
```

## Limits
- Technical rules plus headlines only. It does not read fundamentals or earnings reports.
- Data comes from Yahoo Finance via yfinance: free but occasionally delayed or missing. Missing tickers are listed in the digest.
- Some tickers (e.g. SAFX, BTC-labelled ETFs) may have no Yahoo data; they just show up under "No data for".
- Not financial advice.
