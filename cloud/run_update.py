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
    now = datetime.now()
    d = now.date()
    if d.weekday() >= 5 or (now.hour, now.minute) < (15, 30):
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def latest_data_date():
    files = glob.glob(str(HERE / "data_*.json"))
    dates = sorted(Path(f).name[5:-5] for f in files)
    return dates[-1] if dates else None


def evening():
    date8 = latest_closed_trading_day()
    print("EVENING target", date8, flush=True)
    run("fetch_ths_history.py", date8)
    inp = HERE / f"input_{date8}.json"
    if not inp.exists():
        return False
    data = json.loads(inp.read_text(encoding="utf-8"))
    if not data.get("limit_up"):
        print("limit_up empty, skip", flush=True)
        return False
    run("fetch_klines_http.py", date8)
    run("fetch_next_open_http.py")
    run("stock_workbench.py", f"input_{date8}.json")
    run("build_mobile.py", "--full", date8)
    return True


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
        if a in ("morning", "evening"):
            mode = a
    if not mode:
        mode = "morning" if datetime.utcnow().hour < 6 else "evening"
    print("MODE", mode, flush=True)
    ok = morning() if mode == "morning" else evening()
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
