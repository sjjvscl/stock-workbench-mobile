# -*- coding: utf-8 -*-
"""把 cloud 目录生成的数据合入仓库根目录的 index.html 与 hist/。"""

import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_RE = re.compile(
    r"<script>window\.WB_DATA=.*?window\.WB_BUILD=\"[^\"]*\";\s*</script>",
    re.S,
)


def replace_wb_data(index_path):
    wb = HERE / "wb_data.js"
    if not wb.exists():
        print("skip: cloud/wb_data.js missing")
        return False
    text = index_path.read_text(encoding="utf-8")
    wb_text = wb.read_text(encoding="utf-8").strip()
    wb_text = re.sub(
        r"window\.WB_DATES_INLINE=.*?;\nwindow\.WB_BUILD=",
        "window.WB_DATES_INLINE={};\nwindow.WB_BUILD=",
        wb_text,
        flags=re.S,
    )
    m = re.search(r"window\.WB_DATA=(.*?);\nwindow\.WB_DATES=", wb_text, re.S)
    if m:
        data = json.loads(m.group(1))

        def strip_intraday(o):
            if isinstance(o, dict):
                if isinstance(o.get("kline"), dict):
                    o["kline"].pop("intraday", None)
                for v in o.values():
                    strip_intraday(v)
            elif isinstance(o, list):
                for v in o:
                    strip_intraday(v)

        strip_intraday(data)
        wb_text = (
            wb_text[:m.start(1)]
            + json.dumps(data, ensure_ascii=False)
            + wb_text[m.end(1):]
        )
    new = DATA_RE.sub("<script>" + wb_text + "</script>", text)
    if new == text:
        print("skip: WB_DATA block unchanged")
        return False
    index_path.write_text(new, encoding="utf-8")
    print("index.html WB_DATA updated")
    return True


def copy_date_files():
    n = 0
    for src in sorted(HERE.glob("data_*.json")):
        shutil.copy2(src, ROOT / src.name)
        n += 1
    print(f"date files copied: {n}")


def merge_hist(date8):
    kf = HERE / f"klines_{date8}.json"
    if not kf.exists():
        print("skip: no klines file", kf.name)
        return
    klines = json.loads(kf.read_text(encoding="utf-8"))
    hist_dir = ROOT / "hist"
    hist_dir.mkdir(exist_ok=True)
    n = 0
    for code, rec in klines.items():
        intraday = rec.get("intraday") or []
        if not intraday:
            continue
        hp = hist_dir / f"{code}.js"
        if hp.exists():
            body = hp.read_text(encoding="utf-8").strip()
            prefix = "window.HIST_BY_CODE="
            if body.startswith(prefix):
                try:
                    obj = json.loads(body[len(prefix):].rstrip().rstrip(";"))
                except Exception:
                    obj = {}
            else:
                obj = {}
        else:
            obj = {}
        obj.setdefault(code, {})[date8] = intraday
        hp.write_text(
            "window.HIST_BY_CODE=" + json.dumps(obj, ensure_ascii=False) + ";",
            encoding="utf-8",
        )
        n += 1
    print(f"hist merge: {n} files touched for {date8}")


def apply_premium(date8):
    pf = HERE / f"next_open_{date8}.json"
    if not pf.exists():
        print("skip: no next_open file", pf.name)
        return False
    pm = json.loads(pf.read_text(encoding="utf-8"))
    ip = ROOT / "index.html"
    text = ip.read_text(encoding="utf-8")
    i_data = text.find("window.WB_DATA=")
    i_dates = text.find("window.WB_DATES=", i_data)
    i_inline = text.find("window.WB_DATES_INLINE=", i_dates)
    i_build = text.find("window.WB_BUILD=", i_inline)
    j_build = text.find("</script>", i_build)
    if i_data < 0 or i_dates < 0 or i_inline < 0 or i_build < 0 or j_build < 0:
        print("skip: WB block not found")
        return False
    data_str = text[i_data + len("window.WB_DATA="): text.rfind(";", i_data, i_dates)]
    inline_str = text[i_inline + len("window.WB_DATES_INLINE="): text.rfind(";", i_inline, i_build)]
    data = json.loads(data_str)
    inline = json.loads(inline_str)
    touched = 0
    for r in data.get("tianti") or []:
        code = str(r.get("code") or "")
        p = pm.get(code)
        if p:
            r["next_premium"] = p.get("premium")
            r["next_open"] = p.get("open")
            touched += 1
    key = f"data_{date8}.json"
    day = inline.get(key)
    if isinstance(day, dict):
        for r in day.get("tianti") or []:
            code = str(r.get("code") or "")
            p = pm.get(code)
            if p:
                r["next_premium"] = p.get("premium")
                r["next_open"] = p.get("open")
                touched += 1
    if not touched:
        print("skip: no premium matched")
        return False
    new_block = (
        "window.WB_DATA=" + json.dumps(data, ensure_ascii=False) + ";\n"
        "window.WB_DATES=" + text[i_dates + len("window.WB_DATES="): text.rfind(";", i_dates, i_inline)] + ";\n"
        "window.WB_DATES_INLINE=" + json.dumps(inline, ensure_ascii=False) + ";\n"
        "window.WB_BUILD=" + text[i_build + len("window.WB_BUILD="): j_build]
    )
    text = text[:i_data] + new_block + text[j_build:]
    ip.write_text(text, encoding="utf-8")
    print(f"index.html premium updated: {touched} 只")
    return True


def main():
    args = sys.argv[1:]
    if "--premium" in args:
        date8 = next((a for a in args if len(a) == 8), None)
        return 0 if date8 and apply_premium(date8) else 3
    if "--full" in args:
        date8 = next((a for a in args if len(a) == 8), None)
        if not date8:
            return 3
        changed = replace_wb_data(ROOT / "index.html")
        copy_date_files()
        merge_hist(date8)
        apply_premium(date8)
        return 0 if changed else 0
    print("usage: build_mobile.py --full <YYYYMMDD> | --premium <YYYYMMDD>")
    return 2


if __name__ == "__main__":
    sys.exit(main())
