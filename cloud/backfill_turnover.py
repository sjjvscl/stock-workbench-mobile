# -*- coding: utf-8 -*-
"""回填历史 data_*.json / klines_*.json 的个股成交额（腾讯分时累计金额）。"""

import glob
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from fetch_klines_http import fetch_intraday_tencent

HERE = os.path.dirname(os.path.abspath(__file__))


def total_turnover(code, date):
    try:
        pts = fetch_intraday_tencent(code, date)
        if pts:
            return pts[-1][5]
    except Exception:
        pass
    return None


def backfill_date(T):
    df = os.path.join(HERE, f"data_{T}.json")
    if not os.path.exists(df):
        return 0
    data = json.load(open(df, encoding="utf-8"))
    rows = data.get("tianti") or []
    codes = [str(r.get("code") or "").zfill(6) for r in rows if not r.get("amount")]
    if not codes:
        return 0
    amounts = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(total_turnover, c, T): c for c in codes}
        for fut in as_completed(futs):
            c = futs[fut]
            try:
                v = fut.result()
            except Exception:
                v = None
            if v:
                amounts[c] = round(v / 1e8, 2)
    changed = 0
    for r in rows:
        c = str(r.get("code") or "").zfill(6)
        if c in amounts:
            r["amount"] = amounts[c]
            changed += 1
    if changed:
        with open(df, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        kf = os.path.join(HERE, f"klines_{T}.json")
        if os.path.exists(kf):
            kl = json.load(open(kf, encoding="utf-8"))
            for code, v in amounts.items():
                if code in kl:
                    kl[code]["turnover_yi"] = v
            with open(kf, "w", encoding="utf-8") as f:
                json.dump(kl, f, ensure_ascii=False)
        print(f"{T} updated {changed}/{len(rows)}", flush=True)
    return changed


def main():
    dates = [a for a in sys.argv[1:]] or sorted(
        os.path.basename(f)[5:-5]
        for f in glob.glob(os.path.join(HERE, "data_*.json"))
    )
    total = 0
    for T in dates:
        total += backfill_date(T)
    print(f"backfill done, total {total}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
