# -*- coding: utf-8 -*-
"""
auction_summary.py · 晨间·竞价速览页生成（极速、自包含）
========================================================
读「最新一个有次日溢价的 data_*.json」+ 对应的 next_open_*.json，
生成自包含的 auction.html（内联数据，无需 wb_data.js / wb_history.js），
体积仅几 KB，可秒级部署，供开盘前(9:27)快速看昨日涨停票的今日竞价溢价。

数据来源：
  - data_<T>.json 的 tianti：名称 / 连板 / 题材 / 弱转强标记
  - next_open_<T>.json：每只票的 T+1 开盘溢价 premium（真实通达信开盘价）
其中 T 是"最新一个已有 T+1 开盘价"的交易日（正常交易日晨间 = 前一交易日）。
"""
import json, os, glob, datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def latest_data_with_premium():
    """返回 (日期8位, data路径, next_open路径)，取最新一个【含真实溢价】的文件。"""
    files = sorted(glob.glob(os.path.join(HERE, "data_*.json")), reverse=True)
    for f in files:
        base = os.path.basename(f)
        d = base[len("data_"):-len(".json")]
        nof = os.path.join(HERE, f"next_open_{d}.json")
        if not os.path.exists(nof):
            continue
        try:
            j = json.load(open(nof, encoding="utf-8"))
        except Exception:
            continue
        # 跳过空文件 / 无 premium 字段的文件（如 T+1 尚未开盘时 fetch_next_open 不应写出，但保险起见过滤）
        if not isinstance(j, dict) or not any(
            isinstance(v, dict) and "premium" in v for v in j.values()
        ):
            continue
        return d, f, nof
    return None, None, None


def flag_of(p):
    if p is None:
        return "—"
    if p >= 0.05:
        return "强"
    if p >= 0:
        return "偏强"
    if p >= -0.03:
        return "偏弱"
    return "弱"


def build_rows(tianti, no):
    rows = []
    for t in tianti:
        code = str(t.get("code"))
        rec = no.get(code)
        if not rec:
            continue
        prem = rec.get("premium")
        if prem is None:
            continue
        lbc = t.get("lbc") or 0
        rows.append({
            "code": code,
            "name": t.get("name") or rec.get("name") or "",
            "lbc": lbc,
            "board": t.get("board_label") or (f"{lbc}板" if lbc else ""),
            "premium": prem,
            "flag": flag_of(prem),
            "theme": t.get("theme") or "",
            "reason": (t.get("reason") or "")[:40],
            "weak": t.get("weak_strong"),
            "signal": t.get("signal") or "",
            "hot": lbc >= 4,
        })
    rows.sort(key=lambda r: (-r["lbc"], -r["premium"]))
    return rows


def render(rows, data_date, t1_date):
    n = len(rows)
    strong = sum(1 for r in rows if r["flag"] in ("强", "偏强"))
    weak = sum(1 for r in rows if r["flag"] in ("偏弱", "弱"))
    hot = sum(1 for r in rows if r["hot"])

    def pct(p):
        return f"{p*100:+.2f}%"

    def color(p):
        # 中国习惯：涨=红 跌=绿
        if p is None:
            return "#888"
        return "#e23b3b" if p >= 0 else "#1aa260"

    trs = []
    for r in rows:
        hot_badge = '<span class="hot">高标</span>' if r["hot"] else ""
        sig = ""
        if r["weak"]:
            sig = '<span class="tag t-weak">弱转强</span>'
        elif r["signal"]:
            sig = f'<span class="tag">{r["signal"]}</span>'
        trs.append(f"""<tr class="{'row-hot' if r['hot'] else ''}">
<td class="c-code">{r['code']}<br><span class="c-name">{r['name']}</span></td>
<td class="c-board">{r['board']}{hot_badge}</td>
<td class="c-prem" style="color:{color(r['premium'])}">{pct(r['premium'])}</td>
<td class="c-flag f-{r['flag']}">{r['flag']}</td>
<td class="c-theme">{r['theme']}{sig}</td>
</tr>""")

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>竞价速览 {data_date}</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f6f8;color:#1a1a1a}}
.head{{background:#1f2733;color:#fff;padding:12px 14px}}
.head h1{{margin:0;font-size:17px}}
.head .sub{{font-size:12px;opacity:.8;margin-top:3px}}
.sum{{display:flex;gap:8px;padding:10px 12px;flex-wrap:wrap;background:#fff;border-bottom:1px solid #eee}}
.sum .b{{flex:1;min-width:70px;text-align:center;padding:6px 4px;border-radius:8px;background:#f3f5f8}}
.sum .b b{{display:block;font-size:18px}}
.sum .b span{{font-size:11px;color:#666}}
table{{width:100%;border-collapse:collapse;background:#fff;font-size:13px}}
th,td{{padding:8px 6px;border-bottom:1px solid #f0f0f0;text-align:left;vertical-align:top}}
th{{font-size:11px;color:#888;background:#fafafa;position:sticky;top:0}}
.c-code{{font-weight:600;line-height:1.3}}
.c-name{{font-size:11px;color:#888;font-weight:400}}
.c-board{{font-weight:600;white-space:nowrap}}
.c-prem{{font-weight:700;font-size:14px;white-space:nowrap}}
.c-flag{{font-size:12px;font-weight:600}}
.f-强{{color:#e23b3b}} .f-偏强{{color:#e8852b}} .f-偏弱{{color:#7a8a99}} .f-弱{{color:#1aa260}}
.c-theme{{font-size:11px;color:#666;max-width:38vw}}
.hot{{display:inline-block;font-size:10px;color:#fff;background:#e23b3b;border-radius:4px;padding:0 3px;margin-left:3px;vertical-align:middle}}
.tag{{display:inline-block;font-size:10px;background:#eef3ff;color:#3b6fe2;border-radius:4px;padding:0 3px;margin-top:2px}}
.t-weak{{background:#fff0e8;color:#e8852b}}
.row-hot{{background:#fff8f3}}
.foot{{font-size:11px;color:#999;padding:10px 14px;text-align:center}}
</style></head>
<body>
<div class="head"><h1>竞价速览 · {data_date[:4]}-{data_date[4:6]}-{data_date[6:]} 涨停池</h1>
<div class="sub">T+1 = {t1_date[:4]}-{t1_date[4:6]}-{t1_date[6:]} 集合竞价开盘溢价 · 生成于 {now}</div></div>
<div class="sum">
<div class="b"><b>{n}</b><span>昨日涨停</span></div>
<div class="b"><b style="color:#e23b3b">{strong}</b><span>强/偏强</span></div>
<div class="b"><b style="color:#1aa260">{weak}</b><span>偏弱/弱</span></div>
<div class="b"><b style="color:#e23b3b">{hot}</b><span>高标≥4板</span></div>
</div>
<table><thead><tr><th>代码/名称</th><th>连板</th><th>竞价溢价</th><th>信号</th><th>题材</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table>
<div class="foot">红=涨/强，绿=跌/弱（中国习惯）· 仅供盘前参考，非投资建议</div>
</body></html>"""
    return html


def main():
    d, df, nof = latest_data_with_premium()
    if not d:
        print("无可用 next_open，无法生成竞价速览")
        return False
    data = json.load(open(df, encoding="utf-8"))
    no = json.load(open(nof, encoding="utf-8"))
    tianti = data.get("tianti", [])
    rows = build_rows(tianti, no)
    if not rows:
        print(f"数据日 {d} 无含溢价的涨停票，跳过")
        return False
    t1 = no.get(next(iter(no.keys()), ""), {}).get("t1", "")
    html = render(rows, d, t1 or data.get("next_day", ""))
    out = os.path.join(HERE, "auction.html")
    open(out, "w", encoding="utf-8").write(html)
    print(f"auction.html 生成完成：数据日 {d}，共 {len(rows)} 只，T+1={t1}")
    return True


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 3)
