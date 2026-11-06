
import streamlit as st
import pandas as pd
import numpy as np
import requests, sqlite3, time, threading, json, os
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timezone, timedelta
import websocket

APP_TITLE = "COINPILOT AI — MASTER OWNER v1.5 SIGNAL & EXIT DESK"
DB_PATH = "data/coinpilot.db"
BASE_URL = "https://data-api.binance.vision"  # public market-data REST endpoint

# Dynamic candidate universe: liquid, active Binance Spot USDT pairs only.
STABLE_BASES = {"USDC", "FDUSD", "TUSD", "USDP", "DAI", "USDE", "PYUSD", "EUR", "USTC", "BUSD"}
LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")

@st.cache_data(ttl=300, show_spinner=False)
def get_dynamic_top15(min_quote_volume=5_000_000.0):
    """Return the 15 most liquid eligible Binance USDT Spot markets."""
    info_r = requests.get(BASE_URL + "/api/v3/exchangeInfo", params={"permissions": "SPOT"}, timeout=12)
    info_r.raise_for_status()
    ticker_r = requests.get(BASE_URL + "/api/v3/ticker/24hr", timeout=12)
    ticker_r.raise_for_status()
    allowed = {}
    for item in info_r.json().get("symbols", []):
        base = item.get("baseAsset", "")
        symbol = item.get("symbol", "")
        if (item.get("status") == "TRADING" and item.get("quoteAsset") == "USDT"
                and item.get("isSpotTradingAllowed", True)
                and base not in STABLE_BASES
                and not base.endswith(LEVERAGED_SUFFIXES)
                and not any(x in base for x in ("2L", "2S", "3L", "3S", "5L", "5S"))):
            allowed[symbol] = base
    ranked = []
    for t in ticker_r.json():
        sym = t.get("symbol")
        if sym not in allowed:
            continue
        try:
            qv = float(t.get("quoteVolume", 0))
            bid, ask = float(t.get("bidPrice", 0)), float(t.get("askPrice", 0))
            last = float(t.get("lastPrice", 0))
            spread = ((ask-bid)/((ask+bid)/2)*100) if bid > 0 and ask > 0 else 999.0
            change = float(t.get("priceChangePercent", 0))
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if qv >= float(min_quote_volume) and last > 0 and spread <= 0.50:
            ranked.append({"Pair": sym, "24h Quote Volume (USDT)": qv,
                           "24h Change %": change, "Spread %": spread})
    ranked.sort(key=lambda x: x["24h Quote Volume (USDT)"], reverse=True)
    return ranked[:15]


st.set_page_config(page_title=APP_TITLE, page_icon="🚀", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=15000, key="coinpilot_auto_refresh")

st.markdown("""
<style>
.stApp {background:radial-gradient(circle at 12% 0%,#203b68 0%,#111d35 38%,#090f1d 100%);color:#f5f8ff;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#101e36 0%,#101426 100%);border-right:1px solid #35517b;}
h1,h2,h3 {color:#f7fbff!important;letter-spacing:.2px;}
[data-testid="stAppViewContainer"] {background:transparent;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color:#294766!important;border-radius:16px!important;background:linear-gradient(145deg,rgba(21,42,68,.92),rgba(13,27,48,.94));}
.cp-held {border:1px solid #28d7b0;border-left:5px solid #28d7b0;border-radius:14px;padding:13px 15px;background:linear-gradient(110deg,rgba(20,110,95,.30),rgba(20,45,70,.82));box-shadow:0 0 18px rgba(40,215,176,.10);}
.cp-sell {border:1px solid #ff536d;border-left:5px solid #ff536d;border-radius:14px;padding:13px 15px;background:linear-gradient(110deg,rgba(120,28,54,.34),rgba(35,27,53,.92));animation:cpSellPulse 1.1s ease-in-out infinite;}
.cp-buy {border:1px solid #38d9a9;border-left:5px solid #38d9a9;border-radius:14px;padding:13px 15px;background:linear-gradient(110deg,rgba(20,100,82,.26),rgba(20,43,68,.90));}
.cp-wait {border:1px solid #536985;border-left:5px solid #8da6c4;border-radius:14px;padding:13px 15px;background:rgba(23,39,61,.86);}
@keyframes cpSellPulse {0%,100%{box-shadow:0 0 5px rgba(255,65,95,.25);filter:brightness(1)}50%{box-shadow:0 0 24px rgba(255,65,95,.75);filter:brightness(1.25)}}
.cp-pill {display:inline-block;padding:4px 9px;border-radius:20px;font-size:11px;font-weight:800;letter-spacing:.6px;background:#163c54;color:#b8f4ff;margin-left:6px;}
.cp-muted {color:#a9bdd3;font-size:12px;}
p, label, [data-testid="stCaptionContainer"] {color:#d3def0;}
[data-testid="stMetric"] {background:linear-gradient(145deg,#1b3153,#15223b);padding:16px;border-radius:15px;border:1px solid #3b5e91;box-shadow:0 5px 18px #050b1833;}
[data-testid="stMetricValue"] {color:#ffffff!important;font-weight:800;}
[data-testid="stMetricLabel"] {color:#b9c9e5!important;}
.stButton>button {border-radius:10px;border:1px solid #4d7fc0;background:linear-gradient(100deg,#1769aa,#5546b8);color:#fff;font-weight:800;min-height:2.6rem;}
.stButton>button:hover {border-color:#75d9ff;color:#fff;box-shadow:0 0 16px #32b8ff55;}
div[data-testid="stDataFrame"] {border:1px solid #36547d;border-radius:12px;overflow:hidden;}
div[data-testid="stAlert"] {border-radius:12px;}
hr {border-color:#385176;}
</style>
""", unsafe_allow_html=True)

def db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, side TEXT, qty REAL,
        entry REAL, exit REAL, stop REAL, target REAL, status TEXT,
        opened TEXT, closed TEXT, pnl REAL DEFAULT 0, fees REAL DEFAULT 0,
        strategy TEXT, notes TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT, symbol TEXT,
        signal TEXT, score INTEGER, price REAL, reason TEXT)""")
    for col, definition in [("initial_qty","REAL DEFAULT 0"),("exit_stage","INTEGER DEFAULT 0"),
                            ("realized_partial","REAL DEFAULT 0"),("entry_fee_remaining","REAL DEFAULT 0")]:
        try: con.execute(f"ALTER TABLE trades ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError: pass
    con.execute("UPDATE trades SET initial_qty=qty WHERE initial_qty=0 OR initial_qty IS NULL")
    con.execute("UPDATE trades SET entry_fee_remaining=fees WHERE entry_fee_remaining=0 OR entry_fee_remaining IS NULL")
    row = con.execute("SELECT value FROM settings WHERE key='starting_balance'").fetchone()
    if not row:
        con.execute("INSERT INTO settings VALUES ('starting_balance','1000')")
    defaults = {
        "fee_rate": "0.001", "auto_paper_enabled": "0",
        "auto_paper_stake": "1000", "auto_paper_score": "78",
        "auto_paper_max_positions": "3", "auto_paper_daily_loss": "25",
        "auto_paper_cooldown": "60"
    }
    for key, value in defaults.items():
        con.execute("INSERT OR IGNORE INTO settings VALUES (?,?)", (key, value))
    con.commit()
    return con


# Process-wide Binance combined-stream worker. Public market data only.
@st.cache_resource
def start_market_stream():
    state = {"prices": {}, "connected": False, "last_message": None, "error": None}
    lock = threading.Lock()
    def on_message(ws, message):
        try:
            payload = json.loads(message)
            data = payload.get("data", {})
            symbol = data.get("s")
            price = float(data.get("c"))
            with lock:
                state["prices"][symbol] = {"price": price, "event_time": data.get("E")}
                state["last_message"] = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            with lock:
                state["error"] = str(exc)
    def on_open(ws):
        with lock:
            state["connected"] = True
            state["error"] = None
    def on_close(ws, *args):
        with lock:
            state["connected"] = False
    def on_error(ws, error):
        with lock:
            state["connected"] = False
            state["error"] = str(error)
    def worker():
        while True:
            try:
                # Subscribe to all USDT symbols in the default core watchlist.
                streams = "/".join(f"{sym.lower()}@ticker" for sym in
                                   ["btcusdt","ethusdt","bnbusdt","solusdt","xrpusdt","adausdt","dogeusdt","linkusdt"])
                ws = websocket.WebSocketApp(
                    f"wss://stream.binance.com:9443/stream?streams={streams}",
                    on_message=on_message, on_open=on_open,
                    on_close=on_close, on_error=on_error)
                ws.run_forever(ping_interval=25, ping_timeout=10)
            except Exception as exc:
                with lock:
                    state["connected"] = False
                    state["error"] = str(exc)
            time.sleep(5)
    thread = threading.Thread(target=worker, daemon=True, name="coinpilot-binance-ws")
    thread.start()
    def snapshot():
        with lock:
            return {"prices": dict(state["prices"]), "connected": state["connected"],
                    "last_message": state["last_message"], "error": state["error"]}
    return snapshot

market_snapshot = start_market_stream()

con = db()

def get_setting(key, default):
    row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default

def set_setting(key, value):
    con.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, str(value)))
    con.commit()


def live_price(symbol):
    snap = market_snapshot()
    item = snap["prices"].get(symbol)
    if item:
        return float(item["price"]), "WebSocket"
    # Fallback to REST if the stream has not yet delivered this pair.
    r = requests.get(BASE_URL + "/api/v3/ticker/price", params={"symbol": symbol}, timeout=6)
    r.raise_for_status()
    return float(r.json()["price"]), "REST fallback"

def apply_staged_exit(tid, sym, px, fee_rate, source="price feed"):
    """Paper-only 50/25/25 scale-out at 2R/4R/5R with a -1R/BE/+2R stop ladder."""
    row=con.execute("SELECT qty,entry,stop,target,initial_qty,exit_stage,realized_partial,entry_fee_remaining FROM trades WHERE id=? AND status='OPEN'",(tid,)).fetchone()
    if not row: return
    qty,entry,stop,target,initial_qty,stage,realized,fee_remaining=row
    initial_qty=initial_qty or qty; stage=int(stage or 0); realized=realized or 0; fee_remaining=fee_remaining or 0
    r=entry-stop if entry>stop else (target-entry)/5
    if r<=0: return
    milestones=[(2,.50),(4,.25),(5,.25)]
    while stage<3 and px>=entry+milestones[stage][0]*r:
        multiple,fraction=milestones[stage]
        sell=min(qty,initial_qty*fraction)
        allocated_fee=fee_remaining*(sell/qty) if qty else 0
        realized+=(px-entry)*sell-allocated_fee-px*sell*fee_rate
        qty-=sell; fee_remaining-=allocated_fee; stage+=1
        con.execute(
            "INSERT INTO events(created,symbol,signal,score,price,reason) VALUES(?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), sym, "SELL", 100, px,
             f"AUTO PAPER STAGED EXIT • sold {int(milestones[stage-1][1]*100)}% at {multiple}R")
        )
        if stage==1: stop=entry
        elif stage==2: stop=entry+2*r
        if stage==3 or qty<=initial_qty*1e-8:
            con.execute("UPDATE trades SET qty=0,exit=?,status='CLOSED',closed=?,pnl=?,exit_stage=3,realized_partial=?,entry_fee_remaining=0,notes=? WHERE id=?",
                        (px,datetime.now(timezone.utc).isoformat(),realized,realized,"ALL STAGED TARGETS FILLED • "+source,tid))
            return
        con.execute("UPDATE trades SET qty=?,stop=?,exit_stage=?,realized_partial=?,entry_fee_remaining=? WHERE id=?",
                    (qty,stop,stage,realized,fee_remaining,tid))
    if qty>0 and px<=stop:
        total=realized+(px-entry)*qty-fee_remaining-px*qty*fee_rate
        con.execute("UPDATE trades SET exit=?,status='CLOSED',closed=?,pnl=?,exit_stage=?,realized_partial=?,entry_fee_remaining=0,notes=? WHERE id=?",
                    (px,datetime.now(timezone.utc).isoformat(),total,stage,realized,f"STOP EXIT • ladder stage {stage} • {source}",tid))


def auto_engine_cycle(watch_symbols, timeframe):
    """One safe paper-only cycle: monitor exits, then open qualifying virtual BUYs."""
    fee_rate = float(get_setting("fee_rate", "0.001"))
    # Monitor open positions using the staged 50/25/25 exit ladder.
    open_rows = con.execute("SELECT id,symbol FROM trades WHERE status='OPEN'").fetchall()
    for tid, sym in open_rows:
        try:
            px, source = live_price(sym)
            # A confirmed bearish closed-candle signal exits any remaining long paper quantity.
            try:
                _, _, exit_signal, exit_score, exit_reason = analyze(sym, timeframe)
            except Exception:
                exit_signal, exit_score, exit_reason = "WAIT", 50, "Signal unavailable"
            if exit_signal == "SELL" and exit_score <= 28:
                row = con.execute(
                    "SELECT qty,entry,fees,realized_partial,entry_fee_remaining,exit_stage FROM trades WHERE id=? AND status='OPEN'",
                    (tid,)
                ).fetchone()
                if row:
                    qty, entry, legacy_fee, partial, fee_remaining, stage = row
                    fee_remaining = fee_remaining or 0
                    partial = partial or 0
                    total = partial + (px-entry)*qty - fee_remaining - px*qty*fee_rate
                    con.execute(
                        "UPDATE trades SET qty=0,exit=?,status='CLOSED',closed=?,pnl=?,exit_stage=?,realized_partial=?,entry_fee_remaining=0,notes=? WHERE id=?",
                        (px, datetime.now(timezone.utc).isoformat(), total, int(stage or 0), total,
                         "BEARISH SELL SIGNAL EXIT • "+exit_reason+" • "+source, tid)
                    )
                    con.execute(
                        "INSERT INTO events(created,symbol,signal,score,price,reason) VALUES(?,?,?,?,?,?)",
                        (datetime.now(timezone.utc).isoformat(), sym, "SELL", exit_score, px,
                         "AUTO PAPER EXIT • "+exit_reason)
                    )
                    continue
            apply_staged_exit(tid, sym, px, fee_rate, source)
        except Exception:
            pass

    if get_setting("auto_paper_enabled", "0") != "1":
        con.commit()
        return

    # Daily realized loss circuit breaker.
    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_pnl = con.execute(
        "SELECT COALESCE(SUM(pnl),0) FROM trades WHERE status='CLOSED' AND closed>=?",
        (day_start,)
    ).fetchone()[0]
    daily_limit = float(get_setting("auto_paper_daily_loss", "25"))
    if today_pnl <= -abs(daily_limit):
        con.commit()
        return

    max_positions = int(float(get_setting("auto_paper_max_positions", "3")))
    current_open = con.execute("SELECT COUNT(*) FROM trades WHERE status='OPEN'").fetchone()[0]
    if current_open >= max_positions:
        con.commit()
        return

    stake = float(get_setting("auto_paper_stake", "50"))
    threshold = int(float(get_setting("auto_paper_score", "78")))
    cooldown = int(float(get_setting("auto_paper_cooldown", "60")))
    cash, open_cost = get_wallet()
    used = con.execute("SELECT COALESCE(SUM(qty*entry+fees),0) FROM trades WHERE status='OPEN'").fetchone()[0]
    available = cash - used
    for sym in watch_symbols:
        if current_open >= max_positions or stake * (1 + fee_rate) > available:
            break
        # Avoid duplicate open positions for same pair.
        if con.execute("SELECT 1 FROM trades WHERE symbol=? AND status='OPEN'", (sym,)).fetchone():
            continue
        recent_trade = con.execute(
            "SELECT opened FROM trades WHERE symbol=? ORDER BY id DESC LIMIT 1", (sym,)
        ).fetchone()
        if recent_trade:
            try:
                last = datetime.fromisoformat(recent_trade[0])
                if (datetime.now(timezone.utc) - last).total_seconds() < cooldown * 60:
                    continue
            except Exception:
                pass
        try:
            df, candle, signal, score, reason = analyze(sym, timeframe)
            # Only open paper BUYs on strong positive scores.
            if signal != "BUY" or score < threshold:
                continue
            px, source = live_price(sym)
            stop_distance = px * 0.02
            risk_cash = cash * 0.01
            qty = min(risk_cash / stop_distance, stake / px) if stop_distance > 0 else 0
            fee = qty * px * fee_rate
            stop = px - stop_distance
            target = px + stop_distance * 5
            con.execute(
                """INSERT INTO trades(symbol,side,qty,entry,stop,target,status,opened,fees,strategy,notes)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (sym, "BUY", qty, px, stop, target, "OPEN",
                 datetime.now(timezone.utc).isoformat(), fee, "Auto Paper Engine",
                 f"Score {score}/100; {reason}; price source {source}; staged 50/25/25 exits; 1% planned risk; 5R final target"),
            )
            con.execute("UPDATE trades SET initial_qty=?,entry_fee_remaining=? WHERE id=(SELECT MAX(id) FROM trades)", (qty, fee))
            con.execute(
                "INSERT INTO events(created,symbol,signal,score,price,reason) VALUES(?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), sym, signal, score, px, "AUTO PAPER: " + reason)
            )
            available -= qty * px + fee
            current_open += 1
        except Exception:
            continue
    con.commit()

@st.cache_data(ttl=8, show_spinner=False)
def get_klines(symbol, interval="5m", limit=150):
    url = BASE_URL + "/api/v3/klines"
    r = requests.get(url, params={"symbol":symbol,"interval":interval,"limit":limit}, timeout=8)
    r.raise_for_status()
    raw = r.json()
    cols = ["time","open","high","low","close","volume","close_time","quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]
    df = pd.DataFrame(raw, columns=cols)
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    return df

def indicators(df):
    d = df.copy()
    d["ema9"] = d.close.ewm(span=9, adjust=False).mean()
    d["ema21"] = d.close.ewm(span=21, adjust=False).mean()
    d["ema50"] = d.close.ewm(span=50, adjust=False).mean()
    delta = d.close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    d["rsi"] = 100 - (100 / (1 + rs))
    fast = d.close.ewm(span=12, adjust=False).mean()
    slow = d.close.ewm(span=26, adjust=False).mean()
    d["macd"] = fast - slow
    d["macd_signal"] = d.macd.ewm(span=9, adjust=False).mean()
    d["vol_avg"] = d.volume.rolling(20).mean()
    return d

def analyze(symbol, interval):
    candles = get_klines(symbol, interval)
    # Binance's final kline is usually still forming. Ignore it so signals use closed candles only.
    if len(candles) > 2:
        candles = candles.iloc[:-1].copy()
    # Refuse to generate fresh trading signals from an old/stalled candle feed.
    interval_seconds = {"1m":60,"3m":180,"5m":300,"15m":900,"30m":1800,
                        "1h":3600,"2h":7200,"4h":14400,"6h":21600,"8h":28800,
                        "12h":43200,"1d":86400}.get(interval, 900)
    last_close_ms = int(candles.iloc[-1]["close_time"])
    candle_age = (time.time() * 1000 - last_close_ms) / 1000
    if candle_age > interval_seconds * 2.5:
        raise ValueError(f"STALE MARKET DATA: last closed candle is {candle_age/60:.1f} minutes old")
    df = indicators(candles)
    if len(df) < 55:
        raise ValueError("Not enough closed candles to calculate indicators safely.")
    x = df.iloc[-1]
    prev = df.iloc[-2]
    score, reasons = 50, []
    if x.ema9 > x.ema21 > x.ema50:
        score += 18; reasons.append("EMA trend aligned bullish")
    elif x.ema9 < x.ema21 < x.ema50:
        score -= 18; reasons.append("EMA trend aligned bearish")
    if x.macd > x.macd_signal and prev.macd <= prev.macd_signal:
        score += 12; reasons.append("MACD bullish crossover")
    elif x.macd < x.macd_signal and prev.macd >= prev.macd_signal:
        score -= 12; reasons.append("MACD bearish crossover")
    if pd.notna(x.rsi):
        if 50 <= x.rsi <= 68:
            score += 10; reasons.append("RSI supports bullish momentum")
        elif x.rsi > 75:
            score -= 8; reasons.append("RSI overheated")
        elif x.rsi < 28:
            score += 5; reasons.append("RSI deeply oversold (reversal risk)")
        elif x.rsi < 45:
            score -= 8; reasons.append("RSI weak")
    if pd.notna(x.vol_avg) and x.vol_avg > 0 and x.volume > 1.5*x.vol_avg:
        score += 8 if x.close > x.open else -8
        reasons.append("Volume expansion")
    score = int(max(0,min(100,score)))
    signal = "BUY" if score >= 72 else "SELL" if score <= 28 else "WAIT"
    return df, x, signal, score, "; ".join(reasons) or "No strong confluence"

def build_trade_plan(df, candle, risk_pct=1.0, reward_multiple=5.0):
    """ATR-based illustrative plan from the latest closed candle."""
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    entry = float(candle.close)
    if not np.isfinite(atr) or atr <= 0 or entry <= 0:
        raise ValueError("ATR/price unavailable.")
    distance = max(1.5 * atr, entry * 0.005)
    stop = entry - distance
    target = entry + distance * reward_multiple
    qty_per_1000 = ((1000.0 * risk_pct / 100.0) / distance)
    return {"entry": entry, "stop": stop, "target": target, "atr": atr,
            "risk_distance_pct": distance / entry * 100.0,
            "reward_multiple": reward_multiple, "qty_per_1000": qty_per_1000}


def money(x):
    return f"${x:,.2f}"


def record_signal_event(symbol, signal, score, price, reason):
    """Persist only meaningful signal changes or a 15-minute heartbeat."""
    now = datetime.now(timezone.utc)
    last = con.execute(
        "SELECT created,signal,score FROM events WHERE symbol=? ORDER BY id DESC LIMIT 1",
        (symbol,)
    ).fetchone()
    should_log = True
    if last:
        try:
            age = (now - datetime.fromisoformat(last[0])).total_seconds()
            should_log = (last[1] != signal or last[2] != score or age >= 900)
        except Exception:
            should_log = True
    if should_log:
        con.execute(
            "INSERT INTO events(created,symbol,signal,score,price,reason) VALUES(?,?,?,?,?,?)",
            (now.isoformat(), symbol, signal, int(score), float(price), reason)
        )
        con.commit()
        return True
    return False


def get_wallet():
    start = float(get_setting("starting_balance","1000"))
    closed = con.execute("SELECT COALESCE(SUM(pnl),0) FROM trades WHERE status='CLOSED'").fetchone()[0]
    open_rows = con.execute("SELECT symbol,qty,entry,fees FROM trades WHERE status='OPEN'").fetchall()
    open_cost = sum(q*e + f for _,q,e,f in open_rows)
    return start + closed, open_cost


def get_open_holding_map():
    """Return current virtual Spot holdings keyed by symbol, across all paper strategies."""
    rows = con.execute("SELECT symbol, SUM(qty) FROM trades WHERE status='OPEN' GROUP BY symbol HAVING SUM(qty)>0").fetchall()
    return {symbol: float(qty) for symbol, qty in rows}

st.sidebar.markdown("# 🚀 COINPILOT AI")
st.sidebar.caption("BINANCE MARKET INTELLIGENCE • PAPER MODE")
st.sidebar.markdown("<div style='padding:10px;border:1px solid #2d806f;border-radius:10px;background:#102b2a'><b style='color:#55e0bd'>MASTER OWNER</b><br><span style='color:#b5c8d8;font-size:12px'>LEVEL 50 / 50 • LIFETIME FREE</span></div>", unsafe_allow_html=True)
page = st.sidebar.radio("WORKSPACE", ["Overview", "Live Scanner", "Trade Desk", "Signal Centre", "Strategy Validation", "Auto Paper Engine", "Paper Trading", "Backtesting Lab", "Trade Journal", "Settings"])
symbols_default = ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","LINKUSDT"]
use_dynamic_top15 = st.sidebar.toggle("Dynamic Top 15 USDT Spot", value=True,
    help="Ranks active Binance Spot USDT pairs by 24h quote volume, then filters stablecoin/leveraged tokens and wide spreads.")
minimum_liquidity = st.sidebar.selectbox("Minimum 24h liquidity", ["$2M", "$5M", "$10M", "$25M"], index=1)
min_volume_value = {"$2M": 2_000_000, "$5M": 5_000_000, "$10M": 10_000_000, "$25M": 25_000_000}[minimum_liquidity]
universe_error = None
dynamic_universe = []
if use_dynamic_top15:
    try:
        dynamic_universe = get_dynamic_top15(min_volume_value)
        symbols = [x["Pair"] for x in dynamic_universe]
        if not symbols:
            raise RuntimeError("No eligible pairs met the liquidity and spread filters.")
    except Exception as exc:
        universe_error = str(exc)
        symbols = symbols_default
else:
    symbols_text = st.sidebar.text_area("Manual watchlist (comma-separated)", ",".join(symbols_default), height=95)
    symbols = [s.strip().upper() for s in symbols_text.split(",") if s.strip()]
interval = st.sidebar.selectbox("Signal timeframe", ["5m","15m","1h","4h"], index=1)
st.sidebar.caption("Live Binance data • Personal Windows terminal")
execution_mode = st.sidebar.radio(
    "EXECUTION MODE",
    ["Virtual trading", "Manual real trading"],
    index=0,
    help="Virtual mode records simulated trades. Manual real mode provides signals and Binance links; you place and manage orders yourself."
)
if execution_mode == "Manual real trading":
    st.sidebar.warning("Manual mode only. No real orders are sent by COINPILOT.")
if st.sidebar.button("↻ Refresh market data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

cash, open_cost = get_wallet()
open_pnl = 0.0
open_trades = con.execute("SELECT id,symbol,qty,entry,fees FROM trades WHERE status='OPEN'").fetchall()
for tid,sym,qty,entry,fees in open_trades:
    try:
        p = float(requests.get(BASE_URL+"/api/v3/ticker/price",params={"symbol":sym},timeout=5).json()["price"])
        open_pnl += (p-entry)*qty-fees
    except Exception:
        pass

st.markdown("<div style='display:flex;align-items:center;justify-content:space-between'><div><div style='color:#7fa6ce;font-size:12px;letter-spacing:3px'>BINANCE-POWERED PAPER TRADING TERMINAL</div><h1 style='margin:0'>COINPILOT <span style='color:#45d6c5'>AI</span></h1><div style='color:#9eb2ca'>Trade the plan. Prove the edge. Protect the capital.</div></div><div style='text-align:right;color:#2ee6a6;font-weight:700'>● MARKET DATA CONNECTOR<br><span style='font-size:11px;color:#91a5bf'>MASTER OWNER • LEVEL 50 • SIGNAL / PAPER DESK</span></div></div>", unsafe_allow_html=True)
st.write("")
ws_status = market_snapshot()
if ws_status["connected"]:
    st.caption(f"🟢 Binance WebSocket connected • Last tick: {ws_status['last_message'] or 'waiting'}")
else:
    st.caption("🟡 Binance WebSocket unavailable • public REST market-data fallback enabled")
if use_dynamic_top15:
    if universe_error:
        st.warning(f"Dynamic Top 15 unavailable; using the core 8-pair fallback. Reason: {universe_error[:180]}")
    else:
        st.caption(f"Dynamic universe: {len(symbols)} eligible USDT Spot pairs • liquidity floor {minimum_liquidity} • refreshed every 5 minutes")
        with st.expander("View current Top 15 candidate universe"):
            st.dataframe(pd.DataFrame(dynamic_universe), use_container_width=True, hide_index=True)


if page == "Learning Academy":
    st.subheader("Your crypto spot trading classroom")
    st.info("Learning mode: virtual capital only. No real orders, no leverage, and no API credentials.")
    lessons = {
        "1 • How a spot market works": {
            "goal": "Understand what you own when you buy a spot asset.",
            "body": [
                "A spot purchase exchanges quote currency (for example USDT) for an asset (for example BTC). You own the purchased asset; there is no borrowing or liquidation mechanism like leveraged futures.",
                "A trading pair such as BTCUSDT tells you how many USDT one BTC costs. The base asset is BTC; the quote asset is USDT.",
                "A market order prioritises execution, not price. A limit order sets a maximum buy price or minimum sell price, but may not fill."
            ],
            "takeaway": "Spot removes leverage risk, but the asset price can still fall sharply."
        },
        "2 • Candlesticks and timeframes": {
            "goal": "Read open, high, low and close (OHLC).",
            "body": [
                "Each candle summarises trading during one interval. The body shows open-to-close movement; the wicks show the high and low.",
                "A green candle usually closes above its open; a red candle closes below. Candle colour alone is not a strategy.",
                "A 5-minute chart contains more noise than a 4-hour chart. Always know which timeframe your rule uses."
            ],
            "takeaway": "Wait for a candle to close before treating its pattern as confirmed."
        },
        "3 • Trend and market structure": {
            "goal": "Distinguish an uptrend, downtrend and range.",
            "body": [
                "An uptrend often forms higher highs and higher lows. A downtrend often forms lower highs and lower lows.",
                "A range moves between areas of support and resistance. Trend-following rules often struggle in sideways markets.",
                "No single moving average proves a trend. Use price structure, context and more than one observation."
            ],
            "takeaway": "The same indicator can behave differently in trending and ranging markets."
        },
        "4 • EMA, RSI, MACD and volume": {
            "goal": "Understand what the app's indicators measure.",
            "body": [
                "EMA gives more weight to recent prices. EMA 9/21/50 alignment is a trend filter, not a buy guarantee.",
                "RSI measures recent momentum on a 0–100 scale. High RSI does not automatically mean sell; low RSI does not automatically mean buy.",
                "MACD compares moving averages to describe momentum. Crossovers can lag and whipsaw.",
                "Relative volume compares current volume with its recent average. A volume spike can accompany either direction."
            ],
            "takeaway": "Indicators describe past price and volume; they do not predict the future."
        },
        "5 • Entries, exits and risk/reward": {
            "goal": "Plan the loss before thinking about the profit.",
            "body": [
                "An entry is only one part of a trade plan. Define the invalidation point, stop, target, position size and maximum acceptable loss first.",
                "Risk/reward compares potential loss with potential gain. A 2:1 target-to-risk ratio can still lose money if the win rate and costs are poor.",
                "Stops may fill worse than their trigger during fast markets. Backtests that assume perfect fills can overstate results."
            ],
            "takeaway": "Never increase position size to recover a loss."
        },
        "6 • Fees, slippage and trading psychology": {
            "goal": "See why gross profit is not net profit.",
            "body": [
                "Fees apply according to the exchange's current fee schedule and account tier. This prototype uses an adjustable illustrative fee.",
                "Slippage is the difference between the expected and actual execution price. Thin liquidity and volatility can increase it.",
                "FOMO, revenge trading and moving stops farther away are common process failures. A written plan helps reduce impulsive decisions."
            ],
            "takeaway": "A strategy must survive costs and disciplined execution, not just look good on a chart."
        }
    }
    lesson_name = st.selectbox("Choose a lesson", list(lessons.keys()))
    lesson = lessons[lesson_name]
    st.markdown(f"### {lesson_name}")
    st.write(f"**Learning objective:** {lesson['goal']}")
    for paragraph in lesson["body"]:
        st.write(paragraph)
    st.success("Key takeaway: " + lesson["takeaway"])
    st.markdown("### Knowledge check")
    quiz = {
        "1 • How a spot market works": ("What happens when you buy BTCUSDT on spot?", ["You borrow BTC with leverage", "You exchange quote currency for BTC", "You guarantee a profit"], 1, "A spot buy exchanges quote currency (USDT) for the base asset (BTC)."),
        "2 • Candlesticks and timeframes": ("When is a candle's OHLC information final?", ["Before the interval starts", "Only after the candle closes", "Whenever it turns green"], 1, "The candle is still changing until its interval closes."),
        "3 • Trend and market structure": ("Which pattern is commonly associated with an uptrend?", ["Higher highs and higher lows", "Lower highs and lower lows", "Random movement only"], 0, "Higher highs and higher lows are a common uptrend structure."),
        "4 • EMA, RSI, MACD and volume": ("Does RSI above 70 automatically mean you should sell?", ["Yes, always", "No, momentum can remain strong", "It guarantees a reversal"], 1, "An overbought reading is context, not an automatic trade instruction."),
        "5 • Entries, exits and risk/reward": ("What should be defined before entering a trade?", ["Only the profit target", "Entry, invalidation, stop and position size", "How to recover a loss"], 1, "Risk and exit planning come before the entry."),
        "6 • Fees, slippage and trading psychology": ("Why include fees and slippage in testing?", ["They make charts look better", "They reduce or change realised returns", "They guarantee execution"], 1, "Trading costs can turn a grossly profitable idea into a net loser.")
    }
    question, options, correct, explanation = quiz[lesson_name]
    answer = st.radio(question, options, key="academy_quiz_" + str(list(lessons).index(lesson_name)))
    if st.button("Check my answer", key="academy_check_" + str(list(lessons).index(lesson_name))):
        if options.index(answer) == correct:
            st.success("Correct. " + explanation)
        else:
            st.error("Not quite. " + explanation)
    st.caption("Study one lesson, answer its check, then practise in the virtual environment. Passing a quiz measures recall, not trading skill.")

elif page == "Strategy Validation":
    st.subheader("Strategy validation workbench")
    st.warning("Research only. This is a signal-event study, not a complete exchange execution simulator or a promise of future returns.")
    left, right = st.columns(2)
    sv_symbol = left.selectbox("Market", symbols, key="sv_symbol")
    sv_interval = right.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1, key="sv_interval")
    sv_limit = st.selectbox("Closed historical candles", [300, 500, 1000], index=2, key="sv_limit")
    horizon = st.slider("Outcome horizon (candles)", 1, 20, 5)
    fee_pct = st.number_input("Estimated fee per side (%)", 0.0, 1.0, float(get_setting("fee_rate", "0.001"))*100, 0.01) / 100
    st.markdown("**Three transparent long-only spot signal rules**")
    st.write("- Trend Rider: EMA 9 above EMA 21 above EMA 50, RSI 50–68, MACD above signal.")
    st.write("- Momentum: RSI crosses above 50 and MACD is above its signal line.")
    st.write("- Breakout: close exceeds the previous 20-candle high with above-average volume.")
    if st.button("Run strategy comparison", type="primary"):
        try:
            candles = get_klines(sv_symbol, sv_interval, sv_limit)
            candles = candles.iloc[:-1].copy()  # exclude unfinished candle
            d = indicators(candles).reset_index(drop=True)
            d["prior_high20"] = d["high"].shift(1).rolling(20).max()
            d["vol20"] = d["volume"].shift(1).rolling(20).mean()
            d["rsi_prev"] = d["rsi"].shift(1)
            d["macd_above"] = d["macd"] > d["macd_signal"]
            rules = {
                "Trend Rider": (d["ema9"] > d["ema21"]) & (d["ema21"] > d["ema50"]) & d["rsi"].between(50, 68) & d["macd_above"],
                "Momentum": (d["rsi_prev"] <= 50) & (d["rsi"] > 50) & d["macd_above"],
                "Breakout": (d["close"] > d["prior_high20"]) & (d["volume"] > 1.5*d["vol20"])
            }
            result_rows = []
            detail_rows = []
            split = int(len(d) * 0.70)
            for name, mask in rules.items():
                signals = d.index[mask.fillna(False)].tolist()
                outcomes = []
                for idx in signals:
                    # Signal known at close; hypothetical entry at next candle open.
                    entry_idx, exit_idx = idx + 1, idx + 1 + horizon
                    if exit_idx >= len(d):
                        continue
                    entry = float(d.loc[entry_idx, "open"])
                    exit_price = float(d.loc[exit_idx, "close"])
                    net_pct = ((exit_price / entry) - 1 - 2*fee_pct) * 100
                    period = "Train" if idx < split else "Test"
                    outcomes.append((period, net_pct, d.loc[idx, "time"], d.loc[entry_idx, "time"]))
                    detail_rows.append({"Strategy": name, "Signal time": d.loc[idx, "time"], "Entry time": d.loc[entry_idx, "time"],
                                        "Entry next open": entry, "Exit time": d.loc[exit_idx, "time"], "Exit close": exit_price,
                                        "Net return %": net_pct, "Sample": period})
                for period in ["Train", "Test"]:
                    vals = [x[1] for x in outcomes if x[0] == period]
                    result_rows.append({"Strategy": name, "Sample": period, "Signals": len(vals),
                                        "Positive outcomes %": round(100*sum(v > 0 for v in vals)/len(vals), 1) if vals else 0,
                                        "Average net return %": round(float(np.mean(vals)), 4) if vals else 0,
                                        "Median net return %": round(float(np.median(vals)), 4) if vals else 0})
            summary = pd.DataFrame(result_rows)
            details = pd.DataFrame(detail_rows)
            st.markdown("### Out-of-sample comparison")
            st.dataframe(summary, use_container_width=True, hide_index=True)
            st.caption(f"{len(d)} closed candles • First 70% of sample = training • Last 30% = test • Outcome measured {horizon} candles after next-open entry • Estimated round-trip fees {2*fee_pct*100:.3f}% • Signals with insufficient future candles excluded.")
            if len(details):
                st.markdown("### Signal-by-signal evidence")
                st.dataframe(details, use_container_width=True, hide_index=True)
                st.download_button("Download validation evidence CSV", details.to_csv(index=False).encode("utf-8"),
                                   file_name=f"{sv_symbol}_{sv_interval}_strategy_validation.csv", mime="text/csv")
            else:
                st.info("No eligible signal events in this sample. Do not force trades by loosening rules without a reason.")
            st.error("Important limitations: overlapping signal outcomes are not a portfolio equity curve; no stop-loss, order-book spread, partial fills, tax or market impact is modelled. The test segment is a small holdout, not proof of a durable edge. Repeat across multiple pairs, timeframes and market regimes before drawing conclusions.")
        except Exception as exc:
            st.error(f"Validation could not complete: {exc}")
    else:
        st.info("Choose a pair and timeframe, then run the comparison. No strategy is ranked as a winner until enough out-of-sample evidence exists.")


if page == "Overview":
    st.subheader("Command centre")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Virtual cash", money(cash))
    c2.metric("Open positions", str(len(open_trades)))
    c3.metric("Open P&L", money(open_pnl), delta=f"{open_pnl:+.2f}")
    total_closed = con.execute("SELECT COALESCE(SUM(pnl),0) FROM trades WHERE status='CLOSED'").fetchone()[0]
    c4.metric("Realized P&L", money(total_closed), delta=f"{total_closed:+.2f}")
    st.info("Paper mode is active. No real Binance orders can be placed by this version.")
    st.subheader("Market Pulse  ·  Live recommendations")
    st.caption("Owned coins stay highlighted. A confirmed bearish signal on a coin you hold flashes SELL / EXIT. A bearish signal on a coin you do not own is only a WATCH — Spot trading does not short-sell.")
    held_map = get_open_holding_map()
    if held_map:
        st.success("YOUR VIRTUAL HOLDINGS: " + "  ·  ".join(f"{k} ({v:.6g})" for k,v in held_map.items()))
    pulse_symbols = symbols[:15]
    cols = st.columns(3)
    for i,sym in enumerate(pulse_symbols):
        with cols[i%3]:
            try:
                df,x,sig,score,reason = analyze(sym,interval)
                px, feed = live_price(sym)
                held_qty = held_map.get(sym,0.0)
                if held_qty > 0 and sig == "SELL":
                    display_signal, css_class = "🔴 SELL / EXIT NOW", "cp-sell"
                    status_line = f"HELD POSITION · {held_qty:.6g} {sym.replace('USDT','')} · review exit immediately"
                elif held_qty > 0:
                    display_signal, css_class = ("🟢 HOLDING · BUY BIAS" if sig=="BUY" else "🟢 HOLDING · WAIT"), "cp-held"
                    status_line = f"OWNED · {held_qty:.6g} {sym.replace('USDT','')} · position remains highlighted"
                elif sig == "BUY":
                    display_signal, css_class = "🟢 BUY SETUP", "cp-buy"
                    status_line = "NOT OWNED · eligible for a paper entry after review"
                elif sig == "SELL":
                    display_signal, css_class = "🟠 BEARISH WATCH", "cp-wait"
                    status_line = "NOT OWNED · no Spot sell order is applicable"
                else:
                    display_signal, css_class = "🟡 WAIT", "cp-wait"
                    status_line = "No qualified entry or exit signal"
                st.markdown(f'<div class="{css_class}"><div style="display:flex;justify-content:space-between;gap:8px"><b style="font-size:16px">{sym}</b><span class="cp-pill">{score}/100</span></div><div style="font-size:16px;font-weight:850;margin:8px 0">{display_signal}</div><div class="cp-muted">{status_line}</div></div>', unsafe_allow_html=True)
                st.caption(f"Live {px:,.6g} · RSI {float(x.rsi):.1f} · {feed}")
                st.progress(score)
                if sig == "BUY" and held_qty <= 0 and execution_mode == "Virtual trading":
                    if st.button(f"＋ BUY $100 PAPER · {sym}", key=f"pulse_buy_{sym}", use_container_width=True):
                        cash_now, used_now = get_wallet()
                        used_now = con.execute("SELECT COALESCE(SUM(qty*entry+fees),0) FROM trades WHERE status='OPEN'").fetchone()[0]
                        fee_now = 100.0 * float(get_setting("fee_rate","0.001"))
                        if 100.0 + fee_now > cash_now - used_now:
                            st.error("Not enough virtual cash for this $100 paper entry.")
                        else:
                            plan_now = build_trade_plan(df, x, 1.0, 5.0)
                            qty_now = 100.0 / px
                            con.execute("INSERT INTO trades(symbol,side,qty,entry,stop,target,status,opened,fees,strategy,notes,initial_qty,entry_fee_remaining) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (sym,"BUY",qty_now,px,plan_now["stop"],plan_now["target"],"OPEN",datetime.now(timezone.utc).isoformat(),fee_now,"Market Pulse Paper BUY",f"Manual one-click paper entry • score {score}/100 • staged exits 50% at 2R, 25% at 4R, 25% at 5R • initial stop -1R",qty_now,fee_now))
                            con.commit()
                            st.toast(f"Virtual BUY opened: {sym}", icon="🟢")
                            st.rerun()
                elif held_qty > 0 and sig == "SELL":
                    st.warning("SELL signal active for a coin in your virtual holdings.")
            except Exception as e:
                st.warning(f"{sym}: market data unavailable ({str(e)[:100]})")
    with st.expander("What do these strategy names mean?  ·  Plain-English guide"):
        st.markdown("""**Trend Rider** — buys only when the short-, medium- and longer-term moving averages line up upward. It tries to ride an established trend; it can be late or lose money in sideways markets.

**Momentum Hunter** — looks for strengthening price momentum (for example RSI/MACD confirmation and supportive volume). It tries to catch acceleration, but momentum can reverse quickly.

**Breakout Scanner** — watches for a candle closing above a recent resistance/high with stronger-than-usual volume. Breakouts can fail and fall back into the range.

**Important:** these are research filters, not three magic profit machines. COINPILOT currently uses a combined rule-based signal score for BUY / WAIT / bearish SELL; it does not claim that any strategy is profitable or that a score is a win probability. We will only promote a strategy after realistic out-of-sample testing.""")
    st.caption("Exit plan: sell 50% at +2R, 25% at +4R, final 25% at +5R. Initial stop at -1R; after first target move stop to break-even; after second target move stop to +2R. 1R is the entry-to-initial-stop distance. This is a paper-trading rule, not a profit guarantee.")

elif page == "Live Scanner":
    st.subheader("Live signal scanner")
    st.caption(f"Timeframe: {interval} • Signals refresh when the page reruns.")
    rows=[]
    for sym in symbols:
        try:
            df,x,sig,score,reason = analyze(sym,interval)
            live_px, price_source = live_price(sym)
            rows.append({"Pair":sym,"Signal":sig,"Score":score,"Live price":live_px,"Candle close":x.close,"RSI":round(float(x.rsi),1),"Price feed":price_source,"Reason":reason})
            fresh_event = record_signal_event(sym, sig, score, float(live_px), reason)
            if fresh_event and sig == "BUY":
                st.toast(f"New BUY setup: {sym} • score {score}/100", icon="🟢")
        except Exception as e:
            rows.append({"Pair":sym,"Signal":"ERROR","Score":0,"Last price":np.nan,"RSI":np.nan,"EMA 9":np.nan,"EMA 21":np.nan,"Reason":str(e)[:120]})
    con.commit()
    if rows:
        frame=pd.DataFrame(rows).sort_values("Score",ascending=False)
        st.dataframe(frame, use_container_width=True, hide_index=True)
        st.subheader("Inspect a pair")
        selected=st.selectbox("Choose market", [r["Pair"] for r in rows if r["Signal"]!="ERROR"])
        if selected:
            df,x,sig,score,reason=analyze(selected,interval)
            st.markdown(f"### {selected} — {sig} ({score}/100)")
            st.write(reason)
            st.line_chart(df.set_index("time")[["close","ema9","ema21","ema50"]], use_container_width=True)
            st.caption("Signal engine v0.1: EMA structure, RSI, MACD crossover and relative volume. Validate before real-money use.")



elif page == "Trade Desk":
    st.subheader("Live signal trade desk")
    st.caption("Research configuration: 1% planned account risk per trade • 5:1 reward-to-risk target • 70% win rate is an objective to evaluate, never a guarantee. Signals use closed candles; live prices are shown separately.")

    if execution_mode == "Virtual trading":
        st.success("VIRTUAL MODE — buttons on this page create simulated positions only. No Binance order is placed.")
    else:
        st.warning("MANUAL REAL MODE — COINPILOT does not connect to your Binance account or place orders. Review each signal, then decide and execute independently on Binance.")

    a, b, c = st.columns(3)
    score_floor = a.slider("Minimum BUY signal score", 50, 95, 72, 1, key="desk_score")
    risk_pct = b.number_input("Planned account risk (%)", 0.1, 3.0, 1.0, 0.1, key="desk_risk")
    reward_multiple = c.selectbox("Target / risk", [3.0, 4.0, 5.0], index=2, key="desk_rr")

    rows = []
    for sym in symbols:
        try:
            df, candle, signal, score, reason = analyze(sym, interval)
            live_px, feed = live_price(sym)
            plan = build_trade_plan(df, candle, risk_pct, reward_multiple) if signal == "BUY" else None
            rows.append({
                "symbol": sym, "signal": signal, "score": score, "reason": reason,
                "candle": candle, "plan": plan, "live_px": float(live_px), "feed": feed
            })
        except Exception as exc:
            st.caption(f"{sym}: market data unavailable — {str(exc)[:100]}")

    buys = [r for r in rows if r["signal"] == "BUY" and r["score"] >= score_floor]
    sells = [r for r in rows if r["signal"] == "SELL"]
    waits = [r for r in rows if r["signal"] == "WAIT"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Qualified BUY setups", len(buys))
    m2.metric("SELL / exit warnings", len(sells))
    m3.metric("WAIT", len(waits))

    st.markdown("### Current watchlist signals")
    if rows:
        signal_table = pd.DataFrame([{
            "Pair": r["symbol"], "Signal": r["signal"], "Score": r["score"],
            "Live price": r["live_px"], "Data": r["feed"], "Reason": r["reason"]
        } for r in rows])
        st.dataframe(signal_table, use_container_width=True, hide_index=True)
    else:
        st.info("No market data available. Check your internet connection and try Refresh market data.")

    st.markdown("### BUY opportunities")
    if not buys:
        st.info("No BUY setup currently meets your selected threshold. WAIT is a valid outcome. Do not lower the threshold simply to force trades.")
    for r in buys:
        sym, score, reason, plan, live_px = r["symbol"], r["score"], r["reason"], r["plan"], r["live_px"]
        with st.container(border=True):
            h1, h2 = st.columns([3, 1])
            h1.markdown(f"#### 🟢 {sym} — BUY setup")
            h1.caption(f"Rule score {score}/100 • Closed-candle signal • {r['feed']}")
            h2.metric("Live reference", f"{live_px:,.6g}")
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Reference entry", f"{plan['entry']:,.6g}")
            p2.metric("Illustrative stop", f"{plan['stop']:,.6g}")
            p3.metric("Illustrative target", f"{plan['target']:,.6g}")
            p4.metric("Stop distance", f"{plan['risk_distance_pct']:.2f}%")
            st.write(f"**Signal explanation:** {reason}")
            st.caption(
                f"ATR(14): {plan['atr']:.6g} • Planned reward/risk: {plan['reward_multiple']:.1f}:1 • "
                f"Approximate position quantity per 1,000 USDT account equity at {risk_pct:.1f}% risk: "
                f"{plan['qty_per_1000']:.8g} {sym.replace('USDT','')}."
            )
            if execution_mode == "Virtual trading":
                stake = st.number_input(
                    f"Virtual position size (USDT) — {sym}",
                    min_value=10.0, max_value=100000.0, value=100.0, step=10.0,
                    key=f"desk_stake_{sym}"
                )
                fee_rate = float(get_setting("fee_rate", "0.001"))
                if st.button(f"Open VIRTUAL BUY — {sym}", key=f"desk_paper_{sym}", type="primary"):
                    cash_now, cost_now = get_wallet()
                    qty = stake / live_px
                    fee = stake * fee_rate
                    if stake + fee > cash_now - cost_now:
                        st.error("Insufficient virtual cash. Adjust the virtual stake or wallet balance.")
                    else:
                        con.execute("""INSERT INTO trades(symbol,side,qty,entry,stop,target,status,opened,fees,strategy,notes)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                            (sym, "BUY", qty, live_px, plan["stop"], plan["target"], "OPEN",
                             datetime.now(timezone.utc).isoformat(), fee, "Trade Desk Signal",
                             f"Score {score}/100; {reason}"))
                        con.commit()
                        st.success(f"Virtual position opened for {sym}.")
                        st.rerun()
            else:
                st.markdown("**Before placing a real Spot order:**")
                st.caption("Confirm the pair and side • check available balance • calculate quantity • review spread and fees • decide your own stop-loss and exit • never risk money needed for essentials.")
                trade_url = f"https://www.binance.com/en/trade/{sym.replace('USDT','')}_USDT"
                st.link_button(f"Open {sym} on Binance — manual review", trade_url)

    st.markdown("### SELL signals and exit warnings")
    if not sells:
        st.info("No SELL signal currently detected in the watchlist.")
    for r in sells:
        sym = r["symbol"]
        with st.container(border=True):
            st.markdown(f"#### 🔴 {sym} — SELL / EXIT REVIEW")
            st.write(f"**Signal score:** {r['score']}/100 (bearish side) • **Live reference:** {r['live_px']:,.6g}")
            st.write(f"**Why:** {r['reason']}")
            st.caption("For Spot holdings, interpret this as a possible exit/review warning if you already own the asset. It is not an instruction to short-sell.")
            st.link_button(f"Review {sym} on Binance", f"https://www.binance.com/en/trade/{sym.replace('USDT','')}_USDT")

    st.markdown("### Virtual positions needing attention")
    open_rows = con.execute(
        "SELECT id,symbol,qty,entry,stop,target,fees FROM trades WHERE status='OPEN' ORDER BY id DESC"
    ).fetchall()
    if not open_rows:
        st.caption("No open virtual positions.")
    for tid, sym, qty, entry, stop, target, entry_fee in open_rows:
        try:
            px, _ = live_price(sym)
            flag = "STOP level touched — review exit" if px <= stop else "TARGET level touched — review exit" if px >= target else "Position within planned range"
            st.write(f"**{sym} #{tid}:** {flag} • Live {px:,.6g} • Stop {stop:,.6g} • Target {target:,.6g}")
            if px <= stop or px >= target:
                st.warning("Price has reached or crossed a planned level. This is an alert only; the virtual engine does not guarantee an exact fill.")
        except Exception:
            st.caption(f"{sym} #{tid}: current price unavailable.")

    st.caption("Scores are rule-based confluence scores, not probabilities of profit. Entry is based on the latest closed candle, not a guaranteed fill. ATR stop/target levels are illustrative. Fees, spread, slippage, gaps and volatility can change outcomes.")

elif page == "Signal Centre":
    st.subheader("Signal Centre")
    st.caption("Persistent signal history from your scanner. Alerts are informational and are not trade instructions.")
    left, right = st.columns([2,1])
    min_score = left.slider("Highlight score threshold", 50, 95, 75, 1)
    buy_only = right.toggle("BUY signals only", value=False)
    scan_now = st.button("Scan watchlist now", type="primary")
    rows = []
    for sym in symbols:
        try:
            df, candle, sig, score, reason = analyze(sym, interval)
            px, feed = live_price(sym)
            fresh = record_signal_event(sym, sig, score, px, reason)
            rows.append({
                "Pair": sym, "Signal": sig, "Score": score, "Live price": px,
                "RSI": round(float(candle.rsi), 1), "Feed": feed, "Reason": reason
            })
            if fresh and sig == "BUY":
                st.toast(f"New BUY setup: {sym} • {score}/100", icon="🟢")
        except Exception as exc:
            rows.append({"Pair":sym,"Signal":"ERROR","Score":0,"Live price":np.nan,
                         "RSI":np.nan,"Feed":"Unavailable","Reason":str(exc)[:120]})
    con.commit()
    if rows:
        current = pd.DataFrame(rows)
        if buy_only:
            current = current[current["Signal"] == "BUY"]
        st.markdown("### Current market signals")
        st.dataframe(
            current.style.apply(
                lambda col: ["background-color: rgba(35,190,140,.12)" if v == "BUY"
                             else "background-color: rgba(230,90,110,.12)" if v == "SELL"
                             else "" for v in col], subset=["Signal"]
            ),
            use_container_width=True, hide_index=True
        )
        qualified = current[(current["Signal"] == "BUY") & (current["Score"] >= min_score)]
        st.metric("BUY setups above your threshold", len(qualified))
    st.markdown("### Recent signal history")
    hist = con.execute(
        "SELECT created,symbol,signal,score,price,reason FROM events ORDER BY id DESC LIMIT 200"
    ).fetchall()
    if hist:
        hist_df = pd.DataFrame(hist, columns=["Timestamp UTC","Pair","Signal","Score","Price","Reason"])
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download signal history CSV",
            hist_df.to_csv(index=False).encode("utf-8"),
            file_name="coinpilot_signal_history.csv",
            mime="text/csv"
        )
    else:
        st.info("No signal events recorded yet. Scan the watchlist to start building your signal history.")
    st.caption("A signal score is a rule-based confluence score, not a probability of profit. A BUY label is not a promise that price will rise.")

elif page == "Auto Paper Engine":
    st.markdown("# ⚡ COINPILOT AUTO PAPER DESK")
    st.markdown("**$1,000 virtual portfolio** · Spot-only BUY entries and SELL exits · 1% planned account risk · staged profit booking: 50% at 2R, 25% at 4R, 25% at 5R")
    st.info("SIMULATION ONLY — no Binance account connection, API keys or real orders. The engine evaluates closed-candle signals and manages virtual positions while this page remains open.")

    enabled = get_setting("auto_paper_enabled", "0") == "1"
    with st.container(border=True):
        st.markdown("### 🕹️ Engine control")
        with st.form("auto_engine_settings_v13"):
            new_enabled = st.toggle("Enable automatic paper trading", value=enabled)
            a,b,c = st.columns(3)
            stake = a.number_input("Maximum position notional (USDT)", min_value=25.0, max_value=1000.0,
                                   value=min(1000.0,max(25.0,float(get_setting("auto_paper_stake","1000")))), step=25.0)
            threshold = b.slider("Minimum BUY score", 60, 95, int(float(get_setting("auto_paper_score","78"))))
            max_pos = c.number_input("Maximum simultaneous positions", min_value=1, max_value=3,
                                     value=min(3,max(1,int(float(get_setting("auto_paper_max_positions","3"))))))
            d,e,f = st.columns(3)
            daily_loss = d.number_input("Daily realized-loss pause (USDT)", min_value=5.0, max_value=100.0,
                                        value=min(100.0,max(5.0,float(get_setting("auto_paper_daily_loss","25")))), step=5.0)
            cooldown = e.number_input("Pair re-entry cooldown (minutes)", min_value=5, max_value=1440,
                                      value=int(float(get_setting("auto_paper_cooldown","60"))))
            fee_pct = f.number_input("Estimated fee per side (%)", min_value=0.0, max_value=1.0,
                                     value=float(get_setting("fee_rate","0.001"))*100, step=0.01)
            saved = st.form_submit_button("💾 Save settings and apply", type="primary")
        if saved:
            set_setting("auto_paper_enabled", "1" if new_enabled else "0")
            set_setting("auto_paper_stake", stake)
            set_setting("auto_paper_score", threshold)
            set_setting("auto_paper_max_positions", max_pos)
            set_setting("auto_paper_daily_loss", daily_loss)
            set_setting("auto_paper_cooldown", cooldown)
            set_setting("fee_rate", fee_pct/100)
            st.success("Paper engine settings saved.")
            st.rerun()

    # Run one paper cycle on every 15-second Streamlit refresh while this page is selected.
    auto_engine_cycle(symbols, interval)
    cash, open_cost = get_wallet()
    auto_open = con.execute(
        "SELECT id,symbol,qty,entry,stop,target,opened,notes FROM trades WHERE status='OPEN' AND strategy='Auto Paper Engine' ORDER BY id DESC"
    ).fetchall()
    auto_closed = con.execute(
        "SELECT id,symbol,qty,entry,exit,pnl,opened,closed,notes FROM trades WHERE status='CLOSED' AND strategy='Auto Paper Engine' ORDER BY id DESC LIMIT 100"
    ).fetchall()
    auto_stats = con.execute(
        "SELECT COUNT(*),COALESCE(SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END),0),COALESCE(SUM(pnl),0),COALESCE(AVG(pnl),0) FROM trades WHERE status='CLOSED' AND strategy='Auto Paper Engine'"
    ).fetchone()

    open_rows = []
    unrealized = 0.0
    marked_value = 0.0
    for row in auto_open:
        tid,sym,qty,entry,stop,target,opened,notes = row
        try:
            px, feed = live_price(sym)
            upnl = (px-entry)*qty
            unrealized += upnl
            marked_value += px*qty
            open_rows.append({"ID":tid,"Pair":sym,"Action":"🟢 BUY / OPEN","Qty":qty,"Entry":entry,
                              "Live price":px,"Stop":stop,"Final target":target,"Unrealized P&L":upnl,
                              "Feed":feed,"Opened (UTC)":opened})
        except Exception:
            open_rows.append({"ID":tid,"Pair":sym,"Action":"🟢 BUY / OPEN","Qty":qty,"Entry":entry,
                              "Live price":np.nan,"Stop":stop,"Final target":target,"Unrealized P&L":np.nan,
                              "Feed":"STALE / unavailable","Opened (UTC)":opened})
    realized = float(auto_stats[2] or 0)
    win_rate = (100*auto_stats[1]/auto_stats[0]) if auto_stats[0] else 0.0
    equity_est = cash + unrealized
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Virtual equity (est.)", money(equity_est), delta=f"{equity_est-1000:+.2f} vs $1,000")
    m2.metric("Available virtual cash", money(max(0,cash-open_cost)))
    m3.metric("Open positions", str(len(auto_open)), delta=f"{unrealized:+.2f} unrealized P&L")
    m4.metric("Closed P&L", money(realized), delta=f"{realized:+.2f}")
    k1,k2,k3 = st.columns(3)
    k1.metric("Closed paper trades", str(auto_stats[0]))
    k2.metric("Observed win rate", f"{win_rate:.1f}%", help="Descriptive sample statistic, not a prediction or guarantee.")
    k3.metric("Average closed trade", money(float(auto_stats[3] or 0)))

    st.markdown("### 🟢 BUY / open positions")
    if open_rows:
        st.dataframe(pd.DataFrame(open_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No automated positions are open. Start the engine above; it will wait for qualified BUY setups rather than force trades.")

    st.markdown("### 🔴 SELL / completed trade results")
    if auto_closed:
        history = pd.DataFrame(auto_closed, columns=["Trade ID","Pair","Remaining qty","Entry price","Exit price","Net P&L","Opened UTC","Closed UTC","Exit reason"])
        history["Action"] = history["Net P&L"].apply(lambda x: "🟢 PROFIT" if x > 0 else "🔴 LOSS" if x < 0 else "⚪ FLAT")
        history = history[["Trade ID","Pair","Action","Entry price","Exit price","Net P&L","Opened UTC","Closed UTC","Exit reason"]]
        st.dataframe(history, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download automated trade history CSV", history.to_csv(index=False).encode("utf-8"),
                           file_name="coinpilot_auto_paper_trade_history.csv", mime="text/csv")
    else:
        st.info("Closed BUY → SELL results will appear here after a stop, staged target or bearish SELL signal closes a virtual position.")

    st.markdown("### 📡 Latest BUY / SELL activity")
    activity = con.execute(
        "SELECT created,symbol,signal,score,price,reason FROM events WHERE reason LIKE 'AUTO PAPER%' ORDER BY id DESC LIMIT 40"
    ).fetchall()
    if activity:
        act = pd.DataFrame(activity,columns=["Time UTC","Pair","Action","Score","Price","Execution detail"])
        st.dataframe(act,use_container_width=True,hide_index=True)
    else:
        st.caption("No automated BUY or SELL events recorded yet.")

    st.caption("Automation runs every 15 seconds only while COINPILOT is open and this Auto Paper Engine page is selected. A 1% planned risk uses stop-distance position sizing; the $1,000 figure is virtual starting equity, not a guaranteed loss cap. The 70% win rate is a research objective, not a guarantee. Stops can slip in real markets; paper fills are approximations.")

elif page == "Paper Trading":
    st.subheader("Virtual trading desk")
    st.caption("Simulated Spot only • 1% planned account risk • staged exits: sell 50% at +2R, 25% at +4R, final 25% at +5R • initial stop at -1R • after first target stop moves to break-even • after second target stop moves to +2R. R = original entry-to-stop distance.")
    cash, open_cost = get_wallet()
    fee_rate=float(get_setting("fee_rate","0.001"))
    with st.form("open_trade"):
        a,b,c=st.columns(3)
        sym=a.selectbox("Pair",symbols)
        side=b.selectbox("Side",["BUY"])
        stake=c.number_input("Position size (USDT)",min_value=10.0,max_value=100000.0,value=100.0,step=10.0)
        d,e,f=st.columns(3)
        stop_pct=d.number_input("Initial stop distance %",min_value=0.1,max_value=20.0,value=2.0,step=0.1)
        risk_pct=e.number_input("Planned account risk %",min_value=0.1,max_value=3.0,value=1.0,step=0.1)
        strategy=f.selectbox("Strategy tag",["Combined COINPILOT signal","Trend Rider","Momentum Hunter","Breakout Scanner","Manual"], help="Choose a label for your journal. The strategy names are explained in the Market Pulse guide; selecting a label does not improve or guarantee the trade.")
        submitted=st.form_submit_button("＋ Open simulated BUY")
    if submitted:
        try:
            price=float(requests.get(BASE_URL+"/api/v3/ticker/price",params={"symbol":sym},timeout=6).json()["price"])
            stop_distance=price*(stop_pct/100)
            risk_cash=cash*(risk_pct/100)
            qty=min(risk_cash/stop_distance,stake/price) if stop_distance>0 else 0
            stake_used=qty*price
            fee=stake_used*fee_rate
            available=cash-open_cost
            if stake_used+fee > available:
                st.error(f"Insufficient virtual cash. Available approximately {money(available)}.")
            else:
                con.execute("""INSERT INTO trades(symbol,side,qty,entry,stop,target,status,opened,fees,strategy,notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (sym,"BUY",qty,price,price-stop_distance,price+stop_distance*5,"OPEN",
                     datetime.now(timezone.utc).isoformat(),fee,strategy,
                     "STAGED EXIT 50% at 2R, 25% at 4R, 25% at 5R; ladder stop"))
                con.execute("UPDATE trades SET initial_qty=?,entry_fee_remaining=? WHERE id=(SELECT MAX(id) FROM trades)",(qty,fee))
                con.commit()
                st.success(f"Simulated position opened: {sym} at {price} • planned risk {money(risk_cash)} • staged exits 50/25/25")
                st.rerun()
        except Exception as e:
            st.error(f"Could not open simulated trade: {e}")
    st.markdown("### Open positions")
    rows=con.execute("SELECT id,symbol,qty,entry,stop,target,opened,fees,strategy FROM trades WHERE status='OPEN' ORDER BY id DESC").fetchall()
    if not rows:
        st.info("No open paper positions yet. Use the form above.")
    for tid,sym,qty,entry,stop,target,opened,fees,strategy in rows:
        try:
            price=float(requests.get(BASE_URL+"/api/v3/ticker/price",params={"symbol":sym},timeout=5).json()["price"])
            apply_staged_exit(tid,sym,price,fee_rate,"Paper Trading monitor")
            fresh=con.execute("SELECT status,qty,stop,exit_stage,realized_partial FROM trades WHERE id=?",(tid,)).fetchone()
            if not fresh or fresh[0]!="OPEN":
                st.success(f"{sym} #{tid}: staged exit completed • P&L {money(fresh[4] if fresh else 0)}")
                continue
            qty,stop,stage,partial=fresh[1],fresh[2],fresh[3],fresh[4]
            pnl=(price-entry)*qty-fees-(price*qty*fee_rate)+(partial or 0)
            with st.container(border=True):
                x1,x2,x3,x4=st.columns([2,2,2,2])
                x1.markdown(f"**{sym}**")
                x1.caption(strategy)
                x2.metric("Entry",f"{entry:,.6g}")
                x3.metric("Live price",f"{price:,.6g}")
                x4.metric("Net unrealized",money(pnl),delta=f"{pnl:+.2f}")
                st.caption(f"Remaining qty {qty:.8g} • Ladder stop {stop:.6g} • Final target {target:.6g} • Stage {stage}/3 • Partial P&L {money(partial or 0)} • Opened {opened[:19]}")
                if st.button(f"Close position #{tid}",key=f"close{tid}"):
                    exit_fee=price*qty*fee_rate
                    part=con.execute("SELECT realized_partial,entry_fee_remaining FROM trades WHERE id=?",(tid,)).fetchone()
                    realized=(price-entry)*qty-(part[1] or 0)-exit_fee+(part[0] or 0)
                    con.execute("UPDATE trades SET exit=?,status='CLOSED',closed=?,pnl=? WHERE id=?",
                                (price,datetime.now(timezone.utc).isoformat(),realized,tid))
                    con.commit(); st.success(f"Closed with simulated net P&L {money(realized)}"); st.rerun()
        except Exception as e:
            st.warning(f"{sym}: unable to fetch current price: {e}")


elif page == "Backtesting Lab":
    st.subheader("Strategy backtesting lab")
    st.caption("Research protocol: 1% of current simulated equity at risk per trade; 5R target; 70% win rate is a test objective, not a forecast or guarantee. Backtest first, then paper trade; no real orders are placed.")
    a,b,c,d=st.columns(4)
    bt_symbol=a.selectbox("Market",symbols,key="bt_symbol")
    bt_interval=b.selectbox("Candle interval",["5m","15m","1h","4h","1d"],index=2,key="bt_interval")
    bt_limit=c.selectbox("Historical candles",[300,500,1000],index=2)
    bt_fee=d.number_input("Fee per side (%)",min_value=0.0,max_value=1.0,value=float(get_setting("fee_rate","0.001"))*100,step=0.01)/100
    sl_pct=st.slider("Stop distance (%)",0.5,10.0,2.0,0.5)
    risk_pct=st.number_input("Planned account risk per trade (%)",min_value=0.1,max_value=3.0,value=1.0,step=0.1)
    reward_multiple=5.0
    st.info(f"Staged exits: sell 50% at +2R, 25% at +4R, final 25% at +5R. Stop ladder: initial -1R; after +2R move stop to break-even; after +4R move stop to +2R. The 70% win-rate is a research objective, not a guarantee. Gross full-target outcome for this schedule is +3.25R before fees.")
    starting=st.number_input("Backtest starting balance (USDT)",min_value=100.0,max_value=100000.0,value=1000.0,step=100.0)
    if st.button("▶ Run historical backtest",type="primary"):
        try:
            bt_candles = get_klines(bt_symbol,bt_interval,bt_limit)
            if len(bt_candles) > 2:
                bt_candles = bt_candles.iloc[:-1].copy()
            raw=indicators(bt_candles).reset_index(drop=True)
            raw=raw.dropna(subset=["ema50","rsi","macd_signal"]).reset_index(drop=True)
            balance=float(starting); position=None; trades=[]; equity=[]
            for i in range(1,len(raw)-1):
                cur=raw.iloc[i]; nxt=raw.iloc[i+1]
                bullish=(cur.ema9>cur.ema21>cur.ema50 and 50<=cur.rsi<=68 and cur.macd>cur.macd_signal)
                bearish=(cur.ema9<cur.ema21 or cur.macd<cur.macd_signal)
                if position is None and bullish:
                    entry=float(nxt.open)
                    r_distance=entry*(sl_pct/100)
                    planned_risk_cash=balance*(risk_pct/100)
                    qty=min(planned_risk_cash/r_distance,balance/(entry*(1+bt_fee))) if r_distance>0 else 0
                    budget=qty*entry; entry_fee=budget*bt_fee
                    if qty>0 and budget+entry_fee<=balance:
                        balance-=budget+entry_fee
                        position={"entry":entry,"qty":qty,"initial_qty":qty,"stop":entry-r_distance,
                                  "target":entry+5*r_distance,"r":r_distance,"entry_fee_remaining":entry_fee,
                                  "realized":0.0,"stage":0,"time":nxt.time,"planned_risk":planned_risk_cash}
                elif position is not None:
                    low=float(nxt.low); high=float(nxt.high)
                    # If both initial stop and a profit milestone occur in one candle, assume stop first.
                    if position["stage"]==0 and low<=position["stop"] and high>=position["entry"]+2*position["r"]:
                        exit_px=position["stop"]
                        final=position["realized"]+(exit_px-position["entry"])*position["qty"]-position["entry_fee_remaining"]-exit_px*position["qty"]*bt_fee
                        balance+=position["qty"]*exit_px-exit_px*position["qty"]*bt_fee
                        trades.append({"Entry time":position["time"],"Exit time":nxt.time,"Entry":position["entry"],"Exit":exit_px,"Net P&L":final,"Exit reason":"Initial stop (-1R)"})
                        position=None
                    else:
                        milestones=[(2,.50),(4,.25),(5,.25)]
                        while position is not None and position["stage"]<3:
                            multiple,fraction=milestones[position["stage"]]
                            level=position["entry"]+multiple*position["r"]
                            if high<level: break
                            sell_qty=min(position["qty"],position["initial_qty"]*fraction)
                            alloc_fee=position["entry_fee_remaining"]*(sell_qty/position["qty"])
                            exit_fee=level*sell_qty*bt_fee
                            position["realized"]+=(level-position["entry"])*sell_qty-alloc_fee-exit_fee
                            position["qty"]-=sell_qty
                            position["entry_fee_remaining"]-=alloc_fee
                            balance+=level*sell_qty-exit_fee
                            position["stage"]+=1
                            if position["stage"]==1: position["stop"]=position["entry"]
                            elif position["stage"]==2: position["stop"]=position["entry"]+2*position["r"]
                            if position["stage"]==3 or position["qty"]<=position["initial_qty"]*1e-8:
                                trades.append({"Entry time":position["time"],"Exit time":nxt.time,"Entry":position["entry"],"Exit":level,"Net P&L":position["realized"],"Exit reason":"Staged targets 2R/4R/5R"})
                                position=None
                                break
                        if position is not None:
                            exit_px=None; reason=None
                            if low<=position["stop"]:
                                exit_px=position["stop"]; reason=f"Ladder stop after stage {position['stage']}"
                            elif bearish:
                                exit_px=float(nxt.open); reason="Trend exit"
                            if exit_px is not None:
                                final=position["realized"]+(exit_px-position["entry"])*position["qty"]-position["entry_fee_remaining"]-exit_px*position["qty"]*bt_fee
                                balance+=position["qty"]*exit_px-exit_px*position["qty"]*bt_fee
                                trades.append({"Entry time":position["time"],"Exit time":nxt.time,"Entry":position["entry"],"Exit":exit_px,"Net P&L":final,"Exit reason":reason})
                                position=None
                equity.append({"Time":cur.time,"Equity":balance+(position["qty"]*float(cur.close) if position else 0)})
            if position is not None:
                last=raw.iloc[-1]; exit_px=float(last.close)
                final=position["realized"]+(exit_px-position["entry"])*position["qty"]-position["entry_fee_remaining"]-exit_px*position["qty"]*bt_fee
                balance+=position["qty"]*exit_px-exit_px*position["qty"]*bt_fee
                trades.append({"Entry time":position["time"],"Exit time":last.time,"Entry":position["entry"],"Exit":exit_px,"Net P&L":final,"Exit reason":"End of sample"})
            tdf=pd.DataFrame(trades)
            final_balance=balance
            total_pnl=final_balance-starting
            winrate=(tdf["Net P&L"]>0).mean()*100 if len(tdf) else 0.0
            gross_profit=tdf.loc[tdf["Net P&L"]>0,"Net P&L"].sum() if len(tdf) else 0
            gross_loss=abs(tdf.loc[tdf["Net P&L"]<0,"Net P&L"].sum()) if len(tdf) else 0
            profit_factor=gross_profit/gross_loss if gross_loss>0 else (float("inf") if gross_profit>0 else 0)
            avg_trade=float(tdf["Net P&L"].mean()) if len(tdf) else 0.0
            avg_win=float(tdf.loc[tdf["Net P&L"]>0,"Net P&L"].mean()) if len(tdf[tdf["Net P&L"]>0]) else 0.0
            avg_loss=float(tdf.loc[tdf["Net P&L"]<0,"Net P&L"].mean()) if len(tdf[tdf["Net P&L"]<0]) else 0.0
            equity.append({"Time":raw.iloc[-1].time,"Equity":final_balance})
            equity_df=pd.DataFrame(equity).drop_duplicates(subset=["Time"]).sort_values("Time")
            equity_df["Peak"]=equity_df["Equity"].cummax()
            equity_df["Drawdown %"]=(equity_df["Equity"]/equity_df["Peak"]-1)*100
            max_dd=abs(float(equity_df["Drawdown %"].min())) if len(equity_df) else 0.0
            m1,m2,m3,m4,m5,m6=st.columns(6)
            m1.metric("Net result",money(total_pnl),delta=f"{total_pnl:+.2f}")
            m2.metric("Completed trades",len(tdf))
            m3.metric("Win rate",f"{winrate:.1f}%")
            m4.metric("Profit factor",f"{profit_factor:.2f}" if np.isfinite(profit_factor) else "∞")
            m5.metric("Max drawdown",f"{max_dd:.2f}%")
            m6.metric("Expectancy / trade",money(avg_trade))
            st.caption(f"Ending balance: {money(final_balance)} • Data sample: {len(raw)} CLOSED candles • Planned risk: {risk_pct:.1f}% of equity per trade • Target: {reward_multiple:.0f}R • Fees: {bt_fee*100:.3f}% per side")
            if len(tdf):
                st.metric("70% win-rate research objective", "MET" if winrate >= 70 else "NOT MET", delta=f"{winrate-70:+.1f} percentage points vs objective")
            else:
                st.metric("70% win-rate research objective", "NOT EVALUABLE", help="No completed trades in this sample.")
            with st.expander("Additional performance statistics"):
                st.write(f"Average winning trade: {money(avg_win)}")
                st.write(f"Average losing trade: {money(avg_loss)}")
                st.write(f"Gross profit: {money(gross_profit)}")
                st.write(f"Gross loss: {money(gross_loss)}")
            if len(tdf):
                st.line_chart(equity_df.set_index("Time")["Equity"],use_container_width=True)
                st.dataframe(tdf,use_container_width=True,hide_index=True)
                st.download_button("Download backtest trades CSV",tdf.to_csv(index=False).encode(),file_name=f"{bt_symbol}_{bt_interval}_backtest.csv",mime="text/csv")
                st.download_button("Download equity curve CSV",equity_df.to_csv(index=False).encode(),file_name=f"{bt_symbol}_{bt_interval}_equity.csv",mime="text/csv")
            else:
                st.warning("No trades triggered under these rules in the selected sample. That is a valid result; do not loosen rules just to force trades.")
            st.warning("Backtest limitations: single market, limited candle sample, simplified fills, no order-book depth, no funding, no tax, no survivorship or regime guarantees. Validate on unseen data and paper trade before considering real funds.")
        except Exception as e:
            st.error(f"Backtest failed: {e}")

elif page == "Trade Journal":
    st.subheader("Trade journal & scorecard")
    alltrades=con.execute("SELECT id,symbol,side,qty,entry,exit,stop,target,status,opened,closed,pnl,fees,strategy FROM trades ORDER BY id DESC").fetchall()
    if alltrades:
        df=pd.DataFrame(alltrades,columns=["ID","Pair","Side","Qty","Entry","Exit","Stop","Target","Status","Opened","Closed","Net P&L","Entry fee","Strategy"])
        closed=df[df.Status=="CLOSED"].copy()
        winrate=(closed["Net P&L"]>0).mean()*100 if len(closed) else 0
        gp=float(closed.loc[closed["Net P&L"]>0,"Net P&L"].sum()) if len(closed) else 0.0
        gl=abs(float(closed.loc[closed["Net P&L"]<0,"Net P&L"].sum())) if len(closed) else 0.0
        pf=gp/gl if gl>0 else (float("inf") if gp>0 else 0.0)
        expectancy=float(closed["Net P&L"].mean()) if len(closed) else 0.0
        a,b,c,d,e=st.columns(5)
        a.metric("Completed trades",len(closed))
        b.metric("Win rate",f"{winrate:.1f}%")
        c.metric("Net realized P&L",money(closed["Net P&L"].sum() if len(closed) else 0))
        d.metric("Profit factor",f"{pf:.2f}" if np.isfinite(pf) else "∞")
        e.metric("Expectancy / trade",money(expectancy))
        if len(closed):
            closed["Closed"] = pd.to_datetime(closed["Closed"], errors="coerce", utc=True)
            closed = closed.sort_values("Closed")
            closed["Equity"] = float(get_setting("starting_balance","1000")) + closed["Net P&L"].cumsum()
            closed["Peak"] = closed["Equity"].cummax()
            closed["Drawdown %"] = (closed["Equity"] / closed["Peak"] - 1) * 100
            max_dd = abs(float(closed["Drawdown %"].min()))
            st.metric("Realized-equity max drawdown", f"{max_dd:.2f}%")
            st.line_chart(closed.set_index("Closed")["Equity"], use_container_width=True)
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.download_button("Download trade journal CSV",df.to_csv(index=False).encode(),file_name="coinpilot_trade_journal.csv",mime="text/csv")
    else:
        st.info("Your trade journal is empty. Every paper trade will be recorded here.")

elif page == "Settings":
    st.subheader("System configuration")
    st.warning("Changing the starting balance resets the accounting baseline. Existing trade records are retained.")
    start=float(get_setting("starting_balance","1000"))
    new_start=st.number_input("Starting virtual balance (USDT)",min_value=100.0,max_value=1000000.0,value=start,step=100.0)
    fee=float(get_setting("fee_rate","0.001"))*100
    new_fee=st.number_input("Estimated fee per side (%)",min_value=0.0,max_value=1.0,value=fee,step=0.01)
    if st.button("Save settings"):
        set_setting("starting_balance",new_start)
        set_setting("fee_rate",new_fee/100)
        st.success("Settings saved.")
    st.markdown("### Master owner privileges")
    st.success("MASTER OWNER • LEVEL 50 / 50 • Lifetime free • All current owner modules unlocked. Commercial subscriptions will apply only to customer accounts in a future multi-user release.")
    st.markdown("### Strategy research configuration")
    st.success("Default objective: 1.0% planned account risk per trade • 5:1 reward-to-risk • 70% win rate as a research benchmark only. Validate on historical out-of-sample data, then paper trade across market conditions before considering any manual real trade.")
    st.markdown("### Safety controls")
    st.success("Real API trading is disabled. Manual Real mode only opens Binance market pages; no order is submitted and no API key or secret is requested or stored. COINPILOT does not authorize or execute real trades.")
    st.markdown("### Master Owner")
    st.write("Local owner profile • Level 50 / 50 • Lifetime free. This is a local profile marker, not cloud authentication.")
    st.markdown("### Signal methodology")
    st.write("Signals combine EMA 9/21/50 trend structure, RSI, MACD crossover and relative volume. The score is a rule-based confluence score, not a statistically calibrated probability.")
    st.markdown("### Data and execution limitations")
    st.write("Market prices are fetched from Binance public endpoints. This prototype uses 15-second periodic REST refreshes rather than a resilient always-on WebSocket service. Paper fills are approximate and do not reproduce order-book queue position or all market microstructure effects.")

st.markdown("---")
st.caption("COINPILOT AI v1.3 • AUTO PAPER TRADING • MASTER OWNER LEVEL 50 • Experimental research software • Paper trading only • Not financial advice")
