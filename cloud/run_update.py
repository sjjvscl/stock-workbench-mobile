# -*- coding: utf-8 -*-
"""GitHub Actions 云端更新入口：morning = 竞价溢价；evening = 盘后全量刷新。"""

import glob
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def run(script, *args):
    cmd = [PY, str(HERE / script), *args]
    print("RUN", " ".join(cmd), flush=True)
    r = subprocess.run(
        cmd,
        cwd=str(HERE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.strip().splitlines()[-20:]:
        print("  |", line, flush=True)
    if r.returncode != 0:
        raise RuntimeError(f"{script} failed rc={r.returncode}: {out[-800:]}")
    return out


def latest_closed_trading_day():
    now = datetime.utcnow() + timedelta(hours=8)
    d = now.date()
    if d.weekday() >= 5 or (now.hour, now.minute) < (15, 30):
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def today_weekday_date():
    d = (datetime.utcnow() + timedelta(hours=8)).date()
    if d.weekday() >= 5:
        return None
    return d.strftime("%Y%m%d")


def latest_data_date():
    files = glob.glob(str(HERE / "data_*.json"))
    dates = sorted(Path(f).name[5:-5] for f in files)
    return dates[-1] if dates else None


def refresh_day(date8, mode):
    print(f"{mode.upper()} target", date8, flush=True)
    run("fetch_ths_history.py", date8)
    inp = HERE / f"input_{date8}.json"
    if not inp.exists():
        return False
    data = json.loads(inp.read_text(encoding="utf-8"))
    if not data.get("limit_up"):
        print("limit_up empty, skip", flush=True)
        return False
    if mode == "midday":
        data["mode"] = "midday"
        inp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    run("fetch_klines_http.py", date8)
    run("fetch_next_open_http.py")
    run("stock_workbench.py", f"input_{date8}.json")
    run("build_mobile.py", "--full", date8)
    return True


def evening():
    return refresh_day(latest_closed_trading_day(), "after-close")


def midday():
    date8 = today_weekday_date()
    if not date8:
        print("weekend, skip midday", flush=True)
        return False
    return refresh_day(date8, "midday")


def morning():
    date8 = latest_data_date()
    if not date8:
        print("no data files, skip morning", flush=True)
        return False
    print("MORNING target", date8, flush=True)
    run("fetch_next_open_http.py", "--force", date8)
    run("build_mobile.py", "--premium", date8)
    return True


def main():
    mode = None
    for a in sys.argv[1:]:
        if a in ("morning", "midday", "evening"):
            mode = a
    if not mode:
        cn = datetime.utcnow() + timedelta(hours=8)
        if cn.hour < 10:
            mode = "morning"
        elif cn.hour < 15:
            mode = "midday"
        else:
            mode = "evening"
    print("MODE", mode, flush=True)
    if mode == "morning":
        ok = morning()
    elif mode == "midday":
        ok = midday()
    else:
        ok = evening()
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
