import os
import time
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TIMEFRAME = "5m"
CHECK_SECONDS = 60
RSI_PERIOD = 1000
BUY_MIN, BUY_MAX = 10, 15
SELL_MIN, SELL_MAX = 85, 90
TP_RSI = 50
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 10, 22, 4

SYMBOLS = {
    "XAUUSD": "GC=F", "BTCUSD": "BTC-USD",
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X", "USDCHF": "CHF=X", "USDCAD": "CAD=X",
    "AUDUSD": "AUDUSD=X", "NZDUSD": "NZDUSD=X",
    "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X",
    "EURAUD": "EURAUD=X", "EURCAD": "EURCAD=X",
    "EURCHF": "EURCHF=X", "EURNZD": "EURNZD=X",
    "GBPJPY": "GBPJPY=X", "GBPAUD": "GBPAUD=X",
    "GBPCAD": "GBPCAD=X", "GBPCHF": "GBPCHF=X",
    "GBPNZD": "GBPNZD=X", "AUDJPY": "AUDJPY=X",
    "AUDCAD": "AUDCAD=X", "AUDCHF": "AUDCHF=X",
    "AUDNZD": "AUDNZD=X", "CADJPY": "CADJPY=X",
    "CADCHF": "CADCHF=X", "CHFJPY": "CHFJPY=X",
    "NZDJPY": "NZDJPY=X", "NZDCAD": "NZDCAD=X",
    "NZDCHF": "NZDCHF=X",
}

state = {s: {"trade": None, "last_signal": None, "tp_sent": False} for s in SYMBOLS}

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram token/chat ID yok!")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=15
        )
        if not r.ok:
            print("Telegram error:", r.text)
    except Exception as e:
        print("Telegram error:", e)

def get_prices(symbol):
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": TIMEFRAME, "range": "1mo"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20
        )
        r.raise_for_status()
        result = r.json()["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        return [float(x) for x in closes if x is not None]
    except Exception as e:
        print(symbol, "data error:", e)
        return []

def rsi(prices, period=RSI_PERIOD):
    if len(prices) < period + 1:
        return None
    changes = [prices[i] - prices[i-1] for i in range(1, len(prices))][-period:]
    gains = [x if x > 0 else 0 for x in changes]
    losses = [abs(x) if x < 0 else 0 for x in changes]
    ag, al = sum(gains)/period, sum(losses)/period
    if al == 0:
        return 100.0
    return 100 - (100 / (1 + ag/al))

def ema(values, period):
    if len(values) < period:
        return []
    m = 2 / (period + 1)
    out = [sum(values[:period]) / period]
    for v in values[period:]:
        out.append((v - out[-1]) * m + out[-1])
    return out

def macd(prices):
    fast, slow = ema(prices, MACD_FAST), ema(prices, MACD_SLOW)
    if not fast or not slow:
        return None
    fast = fast[MACD_SLOW - MACD_FAST:]
    n = min(len(fast), len(slow))
    line = [a-b for a,b in zip(fast[-n:], slow[-n:])]
    sig = ema(line, MACD_SIGNAL)
    if len(sig) < 2:
        return None
    line = line[MACD_SIGNAL-1:]
    return line[-2], line[-1], sig[-2], sig[-1]

def check_signal(name, prices):
    if len(prices) < RSI_PERIOD + 5:
        print(f"{name}: candles az {len(prices)}/{RSI_PERIOD+5}")
        return
    price = prices[-1]
    rv = rsi(prices)
    mc = macd(prices)
    if rv is None or mc is None:
        return

    pm, cm, ps, cs = mc
    bullish = pm <= ps and cm > cs
    bearish = pm >= ps and cm < cs
    s = state[name]

    print(f"{name} | Price={price:.5f} | RSI={rv:.2f} | MACD={cm:.6f} | Signal={cs:.6f}")

    if BUY_MIN <= rv <= BUY_MAX and bullish and s["last_signal"] != "BUY":
        send_telegram(
            f"🟢 <b>BUY SIGNAL</b>\n\n📊 {name}\n⏱ {TIMEFRAME}\n"
            f"💰 Entry: {price}\n📈 RSI: {rv:.2f}\n"
            f"〽️ MACD: {MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL}\n"
            f"⬆️ Bullish Cross\n\n🎯 TP1: RSI {TP_RSI}"
        )
        s.update(trade="BUY", last_signal="BUY", tp_sent=False)
        return

    if SELL_MIN <= rv <= SELL_MAX and bearish and s["last_signal"] != "SELL":
        send_telegram(
            f"🔴 <b>SELL SIGNAL</b>\n\n📊 {name}\n⏱ {TIMEFRAME}\n"
            f"💰 Entry: {price}\n📉 RSI: {rv:.2f}\n"
            f"〽️ MACD: {MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL}\n"
            f"⬇️ Bearish Cross\n\n🎯 TP1: RSI {TP_RSI}"
        )
        s.update(trade="SELL", last_signal="SELL", tp_sent=False)
        return

    if s["trade"] == "BUY" and rv >= TP_RSI and not s["tp_sent"]:
        send_telegram(f"🎯 <b>BUY TP1</b>\n\n📊 {name}\n💰 Price: {price}\n📈 RSI: {rv:.2f}\n\nRSI 50-e ýetdi.")
        s.update(trade=None, tp_sent=True)

    elif s["trade"] == "SELL" and rv <= TP_RSI and not s["tp_sent"]:
        send_telegram(f"🎯 <b>SELL TP1</b>\n\n📊 {name}\n💰 Price: {price}\n📉 RSI: {rv:.2f}\n\nRSI 50-e ýetdi.")
        s.update(trade=None, tp_sent=True)

    if BUY_MAX < rv < SELL_MIN:
        s["last_signal"] = None

print("RSI + MACD SIGNAL BOT STARTED")
send_telegram(
    f"🤖 <b>RSI + MACD BOT BAŞLADY!</b>\n\n"
    f"⏱ {TIMEFRAME}\n🟢 BUY: RSI {BUY_MIN}-{BUY_MAX} + MACD bullish cross\n"
    f"🔴 SELL: RSI {SELL_MIN}-{SELL_MAX} + MACD bearish cross\n"
    f"〽️ MACD: {MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL}\n"
    f"🎯 TP1: RSI {TP_RSI}\n📊 Instruments: {len(SYMBOLS)}"
)

while True:
    for name, yahoo_symbol in SYMBOLS.items():
        try:
            check_signal(name, get_prices(yahoo_symbol))
        except Exception as e:
            print(name, "ERROR:", e)
        time.sleep(2)
    print("Next scan:", datetime.now().strftime("%H:%M:%S"))
    time.sleep(CHECK_SECONDS)
