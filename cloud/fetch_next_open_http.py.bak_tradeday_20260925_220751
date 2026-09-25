# -*- coding: utf-8 -*-
"""HTTP 版次日竞价溢价：用东方财富日K计算 T+1 开盘价。"""

import glob
import json
import os
import sys
from datetime import datetime, timedelta

from fetch_klines_http import fetch_daily, limit_ratio

HERE = os.path.dirname(os.path.abspath(__file__))


def next_trading_day(s):
    d = datetime.strptime(s, "%Y%m%d")
    while True:
        d += timedelta(days=1)
        if d.weekday() < 5:
            return d.strftime("%Y%m%d")


def compute_for_date(T, force_fetch=False):
    df = os.path.join(HERE, f"data_{T}.json")
    if not os.path.exists(df):
        return None
    d = json.load(open(df, encoding="utf-8"))
    codes = {}
    for r in d.get("tianti") or []:
        code = str(r.get("code") or "").zfill(6)
        if code:
            codes[code] = r.get("name") or ""
    if not codes:
        return None
    t1 = next_trading_day(T)
    out = {}
    for code, name in sorted(codes.items()):
        bars = None
        if not force_fetch:
            kf = os.path.join(HERE, f"klines_{T}.json")
            if os.path.exists(kf):
                rec = (json.load(open(kf, encoding="utf-8")) or {}).get(code)
                if rec:
                    bars = rec.get("daily") or []
        if not bars:
            try:
                bars = fetch_daily(code, lmt=90)
            except Exception:
                bars = []
        byd = {b[0]: b for b in bars}
        bT = byd.get(T)
        b1 = byd.get(t1)
        if not bT or not b1:
            continue
        close_T = bT[4]
        open_T1 = b1[1]
        if not close_T:
            continue
        prem = (open_T1 - close_T) / close_T
        if abs(prem) > limit_ratio(code) + 0.01:
            continue
        out[code] = {
            "name": name,
            "open": open_T1,
            "close_t": close_T,
            "premium": round(prem, 4),
            "t1": t1,
        }
    if not out:
        print(f"[skip] {T} T+1={t1} 尚未开盘或无可用数据")
        return None
    with open(os.path.join(HERE, f"next_open_{T}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"[OK] next_open_{T}.json T+1={t1}: {len(out)} 只")
    return out


def main():
    args = sys.argv[1:]
    force = "--force" in args
    dates = [a for a in args if not a.startswith("--")]
    if dates:
        for T in dates:
            compute_for_date(T, force_fetch=force)
        return 0
    files = sorted(glob.glob(os.path.join(HERE, "data_*.json")), reverse=True)
    dates = [os.path.basename(f)[5:-5] for f in files]
    if dates:
        dates = dates[:-1]
    for T in dates:
        compute_for_date(T, force_fetch=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
