# -*- coding: utf-8 -*-
"""补齐 hist/*.js 中缺失的历史分时（腾讯优先，东财兜底）。"""

import glob
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from fetch_klines_http import fetch_intraday

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HIST_DIR = os.path.join(ROOT, "hist")


def collect_expected():
    expected = {}
    for fn in sorted(glob.glob(os.path.join(HERE, "data_*.json"))):
        try:
            d = json.load(open(fn, encoding="utf-8"))
        except Exception:
            continue

        def walk(o):
            if isinstance(o, dict):
                if "code" in o and isinstance(o.get("kline"), dict):
                    code = str(o["code"]).zfill(6)
                    daily = o["kline"].get("daily") or []
                    dates = [str(x[0])[:8] for x in daily[-15:] if x and len(x) >= 1]
                    expected.setdefault(code, set()).update(dates)
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(d)
    return expected


def load_hist(code):
    p = os.path.join(HIST_DIR, f"{code}.js")
    if not os.path.exists(p):
        return {}, False
    body = open(p, encoding="utf-8").read().strip()
    prefix = "window.HIST_BY_CODE="
    if not body.startswith(prefix):
        return {}, True
    try:
        return json.loads(body[len(prefix):].rstrip().rstrip(";")), True
    except Exception:
        return {}, True


def save_hist(code, obj):
    p = os.path.join(HIST_DIR, f"{code}.js")
    with open(p, "w", encoding="utf-8") as f:
        f.write("window.HIST_BY_CODE=" + json.dumps(obj, ensure_ascii=False) + ";")


def main():
    expected = collect_expected()
    tasks = []
    for code, dates in sorted(expected.items()):
        obj, exists = load_hist(code)
        have = set(obj.get(code, {}).keys())
        for d in sorted(dates):
            if d not in have:
                tasks.append((code, d))
    print(f"missing pairs {len(tasks)}", flush=True)
    done = ok = 0
    grouped = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_intraday, c, d): (c, d) for c, d in tasks}
        for fut in as_completed(futs):
            c, d = futs[fut]
            try:
                pts = fut.result()
            except Exception:
                pts = []
            if pts:
                grouped.setdefault(c, {})[d] = pts
                ok += 1
            done += 1
            if done % 100 == 0:
                print(f"  ...{done}/{len(tasks)} ok={ok}", flush=True)
    for code, by_date in grouped.items():
        obj, exists = load_hist(code)
        obj.setdefault(code, {}).update(by_date)
        save_hist(code, obj)
    print(f"hist backfill done ok={ok} files={len(grouped)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
