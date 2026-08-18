# -*- coding: utf-8 -*-
"""HTTP 版 K线/分时预取：只依赖东方财富公开接口，无通达信/mootdx 依赖。"""

import json
import os
import ssl
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
DAILY_BARS = 77
INTRA_BARS = 240
WORKERS = 8
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def secid(code):
    c = str(code)
    if c.startswith(("6", "9", "5", "11", "13", "18")):
        return "1." + c
    return "0." + c


def limit_ratio(code):
    c = str(code)
    if c.startswith(("300", "301", "688")):
        return 0.20
    if c.startswith(("8", "4", "92")):
        return 0.30
    return 0.10


def in_session(t):
    try:
        hh, mm = int(t[:2]), int(t[3:5])
    except Exception:
        return False
    if hh == 9 and mm >= 30:
        return True
    if hh == 10:
        return True
    if hh == 11 and mm <= 30:
        return True
    if hh == 13:
        return True
    if hh == 14:
        return True
    if hh == 15 and mm <= 0:
        return True
    return False


def http_json(url, referer="https://quote.eastmoney.com/"):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Referer": referer,
        },
    )
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def fetch_daily_tencent(code, lmt=DAILY_BARS):
    prefix = "sh" if str(code).startswith(("6", "9", "5")) else "sz"
    url = (
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?param={prefix}{code},day,,,{lmt},bfq"
    )
    data = http_json(url, "https://gu.qq.com/")
    node = (data.get("data") or {}).get(f"{prefix}{code}") or {}
    kl = node.get("day") or node.get("bfqday") or []
    out = []
    for p in kl:
        if len(p) < 6:
            continue
        d8 = str(p[0]).replace("-", "")[:8]
        o = float(p[1])
        c = float(p[2])
        h = float(p[3])
        l = float(p[4])
        vol = int(float(p[5]))
        if o <= 0 or c <= 0:
            continue
        out.append([d8, round(o, 2), round(h, 2), round(l, 2), round(c, 2), 0.0, vol])
    return out


def fetch_daily_eastmoney(code, lmt=DAILY_BARS):
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid(code)}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56,f57"
        f"&klt=101&fqt=0&end=20500101&lmt={lmt}"
    )
    data = http_json(url)
    kl = (data.get("data") or {}).get("klines") or []
    out = []
    for line in kl:
        p = line.split(",")
        if len(p) < 7:
            continue
        d8 = p[0].replace("-", "")[:8]
        o = float(p[1])
        c = float(p[2])
        h = float(p[3])
        l = float(p[4])
        vol = int(float(p[5]))
        amt = float(p[6])
        if o <= 0 or c <= 0:
            continue
        out.append([d8, round(o, 2), round(h, 2), round(l, 2), round(c, 2), round(amt, 2), round(vol, 2)])
    return out


def fetch_daily(code, lmt=DAILY_BARS):
    last = None
    for _ in range(2):
        try:
            bars = fetch_daily_tencent(code, lmt)
            if bars:
                return bars
        except Exception as e:
            last = e
        try:
            bars = fetch_daily_eastmoney(code, lmt)
            if bars:
                return bars
        except Exception as e:
            last = e
        time.sleep(1)
    raise RuntimeError(f"daily fetch failed: {last}")


def fetch_intraday_tencent(code, date):
    prefix = "sh" if str(code).startswith(("6", "9", "5")) else "sz"
    url = (
        "https://web.ifzq.gtimg.cn/appstock/app/minute/query"
        f"?code={prefix}{code}&date={date}"
    )
    data = http_json(url, "https://gu.qq.com/")
    node = (data.get("data") or {}).get(f"{prefix}{code}") or {}
    rows = (node.get("data") or {}).get("data") or []
    out = []
    for line in rows:
        parts = line.split()
        if len(parts) < 4:
            continue
        t = parts[0]
        if len(t) == 4 and t.isdigit():
            t = t[:2] + ":" + t[2:]
        p = float(parts[1])
        vol = int(float(parts[2]))
        amt = float(parts[3])
        if vol <= 1 or not in_session(t):
            continue
        out.append([t, round(p, 2), round(p, 2), round(p, 2), round(p, 2), round(amt, 2), vol])
    return out


def fetch_intraday_eastmoney(code, date):
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid(code)}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56,f57"
        f"&klt=1&fqt=0&beg={date}&end={date}"
    )
    data = http_json(url)
    kl = (data.get("data") or {}).get("klines") or []
    out = []
    for line in kl:
        p = line.split(",")
        if len(p) < 7:
            continue
        t = p[0].split(" ")[-1][:5]
        o = float(p[1])
        c = float(p[2])
        h = float(p[3])
        l = float(p[4])
        vol = int(float(p[5]))
        amt = float(p[6])
        if vol <= 1 or not in_session(t):
            continue
        out.append([t, round(o, 2), round(h, 2), round(l, 2), round(c, 2), round(amt, 2), round(vol, 2)])
    return out


def fetch_intraday(code, date):
    last = None
    for _ in range(2):
        try:
            pts = fetch_intraday_tencent(code, date)
            if pts:
                return pts
        except Exception as e:
            last = e
        try:
            pts = fetch_intraday_eastmoney(code, date)
            if pts:
                return pts
        except Exception as e:
            last = e
        time.sleep(1)
    raise RuntimeError(f"intraday fetch failed: {last}")


def fetch_one(code, name, date):
    daily = fetch_daily(code)
    if not daily:
        return code, None
    prev_close = daily[-2][4] if len(daily) >= 2 else None
    lr = limit_ratio(code)
    limit_price = round(prev_close * (1 + lr), 2) if prev_close else None
    try:
        intraday = fetch_intraday(code, date)
    except Exception:
        intraday = []
    turnover_yi = round((intraday[-1][5] or 0) / 1e8, 2) if intraday else None
    return code, {
        "name": name,
        "daily": daily,
        "intraday": intraday,
        "prev_close": prev_close,
        "limit_price": limit_price,
        "limit_ratio": lr,
        "turnover_yi": turnover_yi,
    }


def main():
    if len(sys.argv) < 2:
        print("usage: fetch_klines_http.py <YYYYMMDD>")
        return 2
    date8 = sys.argv[1]
    inp = os.path.join(HERE, f"input_{date8}.json")
    if not os.path.exists(inp):
        print(f"missing {inp}")
        return 2
    data = json.load(open(inp, encoding="utf-8"))
    stocks = []
    for r in data.get("limit_up", []):
        code = str(r.get("sec_code") or r.get("code") or "").zfill(6)
        if code:
            stocks.append((code, r.get("sec_name") or r.get("name") or ""))
    result = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch_one, c, n, date8): c for c, n in stocks}
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                c, rec = fut.result()
                if rec:
                    result[c] = rec
            except Exception as e:
                print(f"  ! {code} failed: {e}")
    out = os.path.join(HERE, f"klines_{date8}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    print(f"[OK] klines_{date8}.json: {len(result)}/{len(stocks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
