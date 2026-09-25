# -*- coding: utf-8 -*-
"""
情绪周期交易工作台 · 数据层渲染器
=================================
读取由盘后/竞价自动化拉取的【原始数据 JSON】，做确定性判定与聚合，
注入 workbench_template.html，输出自包含的个人工作台 HTML。

输入 JSON 结构（由 agent 在自动化中组装）：
{
  "date": "2026-08-14",
  "mode": "after-close" | "bidding",
  "limit_up": [ tdx_screener(message="涨停") 返回的 data 数组 ],
  "market_overview": { westock data_market_overview(type=summary) 的 row },
  "updown": { westock data_market_overview(type=updown) 的 row },
  "bidding": [ {code, chg(竞价涨幅%), vol_ratio, bid_amount_yi}, ... ],   // 仅 bidding 模式
  "review": {mode_in:[], mode_out:[], pnl_note:"", mistake:""},            // 可选，用户复盘
  "discipline": [ "..." ]                                                   // 可选覆盖
}

用法:
  python stock_workbench.py input.json [输出路径]
  python stock_workbench.py            # 默认读同目录 input.json -> workbench.html + workbench_latest.html
"""
import json, sys, os, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, "workbench_template.html")

# 主线题材关键词（用于节点票/弱转强识别）
MAIN_THEMES = {
    "CPO概念", "光通信", "芯片", "半导体", "算力租赁", "人工智能", "AI",
    "创新药", "CXO概念", "医药", "存储芯片", "液冷服务器", "机器人概念", "储能",
}
# 题材广度噪声词（不计入主线排行）
NOISE = {
    "活跃小盘非融", "摩根中国A股基金持股", "微盘精选", "微小盘股", "高商誉",
    "预计转亏", "业绩预亏", "ST板块", "新零售", "电商概念", "国企改革",
    "股权转让", "中标", "人民币贬值受益", "专项贷款", "高盛持股",
}

# ───────────────────────── 次日竞价溢价(T+1) ─────────────────────────
from datetime import date as _dt, timedelta as _td

def next_trading_day(date_str):
    """'YYYY-MM-DD' -> 下一个交易日(跳过周末)。用于定位 T+1 竞价数据。"""
    d = _dt.fromisoformat(str(date_str)[:10])
    while True:
        d = d + _td(days=1)
        if d.weekday() < 5:          # 0=周一 .. 4=周五
            return d.isoformat()

def load_auction(base_date, here):
    """载入 T+1 的竞价溢价数据(若存在)，返回 ({code:{open,premium,close_T}}, t1_date)。

    premium 以小数存储(0.073 = +7.3%)；模板渲染时 *100 转百分比。
    """
    t1 = next_trading_day(base_date).replace("-", "")
    p = os.path.join(here, f"auction_{t1}.json")
    if os.path.exists(p):
        try:
            d = json.load(open(p, encoding="utf-8"))
            return {str(k): v for k, v in (d.get("data") or {}).items()}, d.get("t1")
        except Exception as e:
            print(f"     [竞价溢价] 载入失败: {e}")
            return {}, None
    return {}, None


def load_next_open(base_date, here):
    """载入由 fetch_next_open.py 预计算的『真实 T+1 集合竞价开盘溢价』。

    数据来源：通达信(mootdx) 日K，精确取 T+1 当日那根 bar 的开盘价 vs T 日收盘价，
    premium 以小数存储(0.073 = +7.3%)，模板渲染时 *100 转百分比。
    这是最权威的真实数据，优先于 auction / inline 兜底。
    """
    p = os.path.join(here, f"next_open_{base_date.replace('-', '')}.json")
    if os.path.exists(p):
        try:
            d = json.load(open(p, encoding="utf-8"))
            return {str(k): v for k, v in d.items()}, d.get("t1")
        except Exception as e:
            print(f"     [次日溢价] next_open 载入失败: {e}")
            return {}, None
    return {}, None


def fill_premium_from_inline(lu, dates_inline, base_date):
    """兜底：从 data_{T+1}.json 取 T+1 当日那根 K 的开盘(正确取 日期==T+1 的 bar)。

    仅在 next_open_*.json 与 auction 都缺失时作为最后兜底（覆盖不全，仅限 T+1 仍在涨停池的票）。
    返回回填数量。
    """
    t1 = next_trading_day(base_date).replace("-", "")
    nxt = dates_inline.get(f"data_{t1}.json")
    if not nxt:
        return 0
    by_code = {}
    def _scan(obj):
        if isinstance(obj, dict):
            code = obj.get("code")
            k = obj.get("kline")
            if code and isinstance(k, dict):
                d = k.get("daily") or []
                # 正确取 T+1 那根：日期==T+1 的 bar（升序，从后往前找）
                hit = None
                for bar in reversed(d):
                    if bar[0] == t1:
                        hit = bar; break
                if hit and str(code) not in by_code:
                    by_code[str(code)] = {"open": hit[1], "close": hit[4]}
            for v in obj.values(): _scan(v)
        elif isinstance(obj, list):
            for v in obj: _scan(v)
    _scan(nxt)
    n = 0
    for r in lu:
        if r.get("next_premium") is not None:
            continue
        nb = by_code.get(str(r.get("code")))
        if not nb or not nb.get("open"):
            continue
        k = r.get("kline") or {}
        d = (k.get("daily") or [])
        if not d:
            continue
        # T 日收盘 = 日期==T 那根收盘
        close_T = None
        for bar in reversed(d):
            if bar[0] == base_date.replace("-", ""):
                close_T = bar[4]; break
        if not close_T:
            continue
        prem = (nb["open"] - close_T) / close_T
        r["next_premium"] = round(prem, 4)
        r["next_open"] = nb["open"]
        n += 1
    return n


def scan_all_data_files(here):
    """扫所有 data_*.json 返回 {filename: DATA}，供 fill_premium 用。
    注意：当前正在生成的 data_{date}.json 也要算上（脚本是单日期维度，本函数对历史日期不起作用）。"""
    import glob as _glob
    out = {}
    for _p in _glob.glob(os.path.join(here, "data_*.json")):
        try:
            with open(_p, encoding="utf-8") as _f:
                out[os.path.basename(_p)] = json.load(_f)
        except Exception:
            pass
    return out

# ───────────────────────── 解析 ─────────────────────────
def fnum(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d

def parse_limit_up(rows):
    out = []
    for r in rows:
        lbc = int(fnum(r.get("连续涨停天数", 0)))
        feng = fnum(r.get("封单金额0#", 0)) / 1e8          # 元 -> 亿
        amt = fnum(r.get("涨停成交额(万)", 0)) / 1e4        # 万 -> 亿
        reason = (r.get("涨停原因") or "").strip()
        board = (r.get("板型") or "").strip()
        open_times = int(fnum(r.get("涨停打开次数", 0)))
        main_hit = any(t in reason for t in MAIN_THEMES)
        is_hs = ("换手板" in board) or open_times >= 1 or ("T字板" in board)
        # 天梯里的弱转强蓝标：换手/分歧 + 主线 + 非首板
        weak_strong = bool(is_hs and main_hit and lbc >= 1)
        out.append({
            "code": r.get("sec_code"),
            "name": r.get("sec_name"),
            "chg": fnum(r.get("chg", 0)),
            "lbc": lbc,
            "desc": r.get("几天几板", ""),
            "reason": reason,
            "board": board,
            "fengdan": round(feng, 2),
            "amount": round(amt, 2),
            "open_times": open_times,
            "first": r.get("首次涨停时间", ""),
            "last": r.get("最近涨停时间", ""),
            "fc_ratio": fnum(r.get("封成比", 0)),
            "weak_strong": weak_strong,
            "signal": ("换手" if is_hs else "硬板"),
        })
    return out

def agg_themes(lu):
    """按题材聚合，返回每段带【涨停个股清单 + 核心辨识度 + 平均次日溢价】。

    核心辨识度(同一题材内比较)：
      👑 身位最高  = 连板数 max (且 ≥1板)
      ⚡ 封板最早  = 首次涨停时间 min
      💰 封单最大  = 封单金额 max
    """
    c = Counter()
    theme_stocks = {}
    for r in lu:
        for t in re.split(r"[.、]", r["reason"] or ""):
            t = t.strip()
            if t and t not in NOISE:
                c[t] += 1
                theme_stocks.setdefault(t, []).append(r)
    out = []
    for name, stocks in theme_stocks.items():
        max_lbc = max((s["lbc"] for s in stocks), default=0)
        # 最早涨停时间：空时间视为最晚
        def _tt(s):
            f = (s.get("first") or "").strip()
            return f if f else "99:99:99"
        earliest = min(stocks, key=_tt) if stocks else None
        max_fd = max((s.get("fengdan", 0) for s in stocks), default=0)
        stock_list = []
        for s in stocks:
            core = []
            if max_lbc >= 1 and s["lbc"] == max_lbc:
                core.append("👑身位")
            if earliest and str(s["code"]) == str(earliest["code"]):
                core.append("⚡最早")
            if max_fd > 0 and abs(s.get("fengdan", 0) - max_fd) < 1e-9:
                core.append("💰封单")
            stock_list.append({
                "code": s["code"], "name": s["name"], "lbc": s["lbc"],
                "fengdan": s.get("fengdan", 0), "first": s.get("first", ""),
                "board": s.get("board", ""), "core": core,
                "next_premium": s.get("next_premium"),   # 小数 或 None
                "has_k": bool(s.get("kline")),
                "board_label": s.get("board_label"), "is_fanbao": s.get("is_fanbao"),
            })
        pres = [s["next_premium"] for s in stock_list if s["next_premium"] is not None]
        avg_pre = round(sum(pres) / len(pres), 4) if pres else None
        out.append({
            "name": name, "zt_count": c[name], "pct": None,
            "avg_premium": avg_pre, "stocks": stock_list,
        })
    return out

# ───────────────────────── 情绪周期判定 ─────────────────────────
def judge(zt, dt, max_lbc, zha_rate, promote_rate, mo, up_ratio=None, low5=None, high5=None):
    """周期判定 — 仅基于涨停池+跌停池内生信号(zt/dt/zha_rate/promote_rate/max_lbc)。
    mo/up_ratio/low5/high5 仍兼容，但允许 None（历史周数据无涨跌家数）。
    """
    sent = mo.get("SENTIMENT_STATUS", "") if mo else ""
    val  = mo.get("VALUATION_STATUS", "") if mo else ""
    trend_long = mo.get("TREND_LONG_DIRECTION_STATUS", "") if mo else ""
    has_breadth = up_ratio is not None and low5 is not None and high5 is not None

    zha_pct = f"{zha_rate*100:.0f}%" if zha_rate is not None else "—"
    pr_pct  = f"{promote_rate*100:.0f}%" if promote_rate is not None else "—"
    bk = f"、涨跌比{up_ratio:.2f}" if has_breadth and up_ratio != 1.0 else ""

    # ④ 主跌期：跌停多+涨停少 / 或跌停绝对值大
    if dt >= 12 or (zt < 30 and dt >= 5) or (dt >= 8 and zt < dt*5):
        return {
            "stage": "④ 主跌期",
            "action": "空仓 / 极小仓试错",
            "signal": (f"跌停{dt}只 vs 涨停{zt}只、炸板率{zha_pct}{bk}"
                       f"——亏钱效应主导，接力补涨皆危险。"),
            "todo": ["切新题材一日游(仅前排)", "老题材连跌两天尾盘再博反弹",
                     "不抢盘中反弹", "单笔亏≥2%当日停手", "别乱试抖音新战法"],
        }
    # ② 主升高潮期：涨停极多 + 龙头极高 + 跌停少
    if zt >= 80 and max_lbc >= 7 and dt <= 5:
        return {
            "stage": "② 主升高潮期",
            "action": "可推仓至50%上限（高潮日谨防次日分化）",
            "signal": (f"涨停{zt}只、最高{max_lbc}板、跌停{dt}只、晋级率{pr_pct}、炸板率{zha_pct}"
                       f"——主线全面高潮，新周期主升确认。{('情绪:'+sent) if sent else ''}"),
            "todo": ["干真龙头(打板/竞价/隔日)", "五连板以上挖主线低位",
                     "不频繁切换、不丢龙头", "高潮次日谨防分化", "按仓位规则出手"],
        }
    # ② 主升期(初中段)：涨停多 + 龙头确认高度 + 跌停少
    if zt >= 60 and max_lbc >= 5 and dt <= 5:
        return {
            "stage": "② 主升期(初中段)",
            "action": "可推仓至50%上限",
            "signal": (f"涨停{zt}只、最高{max_lbc}板、跌停{dt}只、晋级率{pr_pct}、炸板率{zha_pct}"
                       f"——新主线确认+赚钱效应外溢，模式内窗口开启。"),
            "todo": ["干真龙头(打板/竞价/隔日)", "五连板以上挖主线低位",
                     "不频繁切换、不丢龙头", "按仓位规则出手", "单笔亏≥2%当日停手"],
        }
    # ③ 高位震荡期/退潮前：龙头极高 / 跌停显著增多 / 涨停数高+跌停5+
    if max_lbc >= 7 or dt >= 8 or (zt >= 50 and dt >= 5):
        return {
            "stage": "③ 高位震荡期 / 退潮前兆",
            "action": "落袋控仓(≤30%)",
            "signal": (f"涨停{zt}只、最高{max_lbc}板、跌停{dt}只、炸板率{zha_pct}——龙头已高、"
                       f"中位亏钱效应起，落袋为安，等低位补涨或切换。"),
            "todo": ["高位不重仓接力", "低位补涨(龙头不死前提下)", "不博穿越",
                     "控仓≤30%", "单笔亏≥2%当日停手"],
        }
    # ② 局部主升：涨停40+ + 龙头4板+ + 跌停极少
    if zt >= 40 and max_lbc >= 4 and dt <= 3:
        return {
            "stage": "② 局部主升(主线未全开)",
            "action": "可推仓至40%上限",
            "signal": (f"涨停{zt}只、最高{max_lbc}板、跌停{dt}只、炸板率{zha_pct}——"
                       f"局部主线活跃但未普涨，赚钱效应集中在少数题材。"),
            "todo": ["聚焦已确认的主线核心", "打板/低吸均可", "中位跟风观望", "控仓≤40%"],
        }
    # ③ 高位震荡 / 确认中（涨停30-50之间）
    if zt >= 30:
        return {
            "stage": "③ 高位震荡 / 确认中",
            "action": "控仓(≤30%)",
            "signal": (f"涨停{zt}只、最高{max_lbc}板、跌停{dt}只、炸板率{zha_pct}、晋级率{pr_pct}"
                       f"——方向未明，控仓试错，等周期确认。"),
            "todo": ["低位试错新题材", "不追高接力", "控仓≤30%", "等升阶硬条件再推仓"],
        }
    # ① 低位试错期
    return {
        "stage": "① 低位试错期",
        "action": "小仓试错(≤20%)",
        "signal": (f"涨停仅{zt}只、最高{max_lbc}板、跌停{dt}只、炸板率{zha_pct}"
                   f"——老题材冰点、新题材轮动。没有主线方向。"),
        "todo": ["打首板/切换新题材一日游", "低位补涨(老题材)",
                 "不追高、不接力高位", "小仓试错≤20%"],
    }

# ───────────────────────── 节点票 / 弱转强 ─────────────────────────
def pick_nodes(lu):
    nodes = []
    max_lbc = max((r["lbc"] for r in lu), default=0)
    for r in lu:
        reason = r["reason"]
        main_hit = any(t in reason for t in MAIN_THEMES)
        is_hs = ("换手板" in r["board"]) or r["open_times"] >= 1 or ("T字板" in r["board"])
        if not ((is_hs and main_hit and r["lbc"] >= 1) or r["lbc"] == max_lbc):
            continue
        theme0 = reason.split(".")[0] if reason else "—"
        if r["lbc"] == max_lbc:
            sig = "高度龙·换手" if is_hs else "高度龙·一字"
        elif r["open_times"] >= 3 and is_hs:
            sig = "大分歧回封·弱转强"
        elif is_hs:
            sig = "换手确认·弱转强"
        else:
            sig = "主线核心"
        why = (f"{theme0}｜{r['board'] or '硬板'}｜{r['desc']}｜"
               f"封单{r['fengdan']}亿/成交{r['amount']}亿｜次日看竞价高开确认弱转强")
        nodes.append({
            "name": r["name"], "code": r["code"], "signal": sig, "why": why,
            "lbc": r["lbc"],
            "board_label": r.get("board_label"), "is_fanbao": r.get("is_fanbao"),
        })
    nodes.sort(key=lambda n: -n["lbc"])
    return nodes[:8]

# ───────────────────────── 开盘策略(竞价) ─────────────────────────
def build_opening(nodes, bidding, mo, up_ratio):
    bmap = {str(b.get("code")): b for b in (bidding or [])}
    watch = []
    for n in nodes:
        b = bmap.get(str(n["code"]))
        if not b:
            continue
        chg = fnum(b.get("chg", 0))           # 竞价涨幅 %
        vr = fnum(b.get("vol_ratio", 0))
        ba = fnum(b.get("bid_amount_yi", 0))
        n["price"] = chg / 100.0               # 渲染用 fraction
        n["vol_ratio"] = vr
        n["bid_amount"] = round(ba, 2)
        if chg >= 5 and vr >= 3:
            note = "竞价爆量高开 → 弱转强确认，可试仓(按仓位规则)"
        elif chg > 0:
            note = "高开但量比不足 → 等回封再定，不追"
        else:
            note = "平/低开 → 弱，放弃，等盘中转强"
        watch.append({"name": n["name"], "code": n["code"], "note": note})
    if up_ratio < 1:
        strat = ("广度弱(跌多涨少)＋估值高估：开盘【不追】高开秒板，只做竞价爆量且板块续强的"
                 "真核心换手票；中位跟风、一字加速一律不碰。单笔亏≥2%当日停手。")
    else:
        strat = "广度强：聚焦龙头与弱转强换手，按仓位规则推至上限，不频繁切换。"
    return {"strategy": strat, "watch": watch}

def board_struct(daily, ratio, tk):
    """用日K回算真实连板结构。
    返回 (cur, prev)：
      cur  = 目标日(tk)当日向前连续涨停天数（当日必为涨停，遇非涨停日即停，断板日不算入）
      prev = 跳过断板日后，向前数上一段连续涨停天数（即断板当日连板数）
    例：5连板→断板→反包  => (1, 5)，标注为 '5+1'
    """
    if not daily or len(daily) < 2:
        return 0, 0
    idx = None
    for i, b in enumerate(daily):
        if b[0] == tk:
            idx = i
            break
    if idx is None:
        idx = len(daily) - 1
    thr = 1 + ratio - 0.006
    # cur：当日向前连续涨停
    cur = 0
    i = idx
    while i > 0 and daily[i][4] / daily[i-1][4] >= thr:
        cur += 1
        i -= 1
    # prev：跳过断板日，向前数上一段连续涨停
    prev = 0
    j = idx - cur
    if j > 0 and daily[j][4] / daily[j-1][4] < thr:
        k = j - 1
        while k > 0 and daily[k][4] / daily[k-1][4] >= thr:
            prev += 1
            k -= 1
    return cur, prev


# ───────────────────────── 主流程 ─────────────────────────
def main():
    inp_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "input.json")
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    with open(inp_path, encoding="utf-8") as f:
        inp = json.load(f)

    date = inp.get("date") or "未知"
    mode = inp.get("mode", "after-close")
    lu = parse_limit_up(inp.get("limit_up", []))
    for r in lu:
        r["theme"] = (r["reason"].split(".")[0] if r.get("reason") else "—")
    mo = inp.get("market_overview", {}) or {}
    updown = inp.get("updown", {}) or {}

    zt = len(lu)
    max_lbc = max((r["lbc"] for r in lu), default=0)
    red = fnum(updown.get("CNT_RED", 0)); green = fnum(updown.get("CNT_GREEN", 0))
    has_breadth = bool(red or green or fnum(updown.get("CNT_LOW5", 0)) or fnum(updown.get("CNT_HIGH5", 0)))
    up_ratio = (red / green) if green else 1.0
    low5 = fnum(updown.get("CNT_LOW5", 0)); high5 = fnum(updown.get("CNT_HIGH5", 0))

    # 跌停数：优先 input.limit_down_count（东财兜底已注入），再回退 updown.CNT_REACH_DNLIMIT，最后东财实时跌停池兜底
    dt = int(inp.get("limit_down_count") or fnum(updown.get("CNT_REACH_DNLIMIT", 0)))
    if not dt:
        try:
            import urllib.request, ssl as _ssl
            _ctx = _ssl.create_default_context(); _ctx.check_hostname=False; _ctx.verify_mode=_ssl.CERT_NONE
            _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
            _url = f"https://push2ex.eastmoney.com/getTopicDTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=200&sort=fund%3Aasc&date={date.replace('-','')}"
            _req = urllib.request.Request(_url, headers={"User-Agent":_UA, "Referer":"https://quote.eastmoney.com/"})
            _raw = urllib.request.urlopen(_req, timeout=15, context=_ctx).read()
            _d = json.loads(_raw.decode("utf-8", "ignore"))
            _pool = (_d.get("data") or {}).get("pool") or []
            if _pool:
                dt = len(_pool)
                inp["limit_down_count"] = dt
                inp["limit_down_stocks"] = [{"code":p.get("c"), "name":p.get("n"), "pct":round((float(p.get("zdp") or 0))/100, 4)} for p in _pool[:20]]
                print(f"[limit_down eastmoney fallback] {dt} stocks on {date}", file=sys.stderr)
        except Exception as e:
            print(f"[limit_down eastmoney fallback failed] {e}", file=sys.stderr)

    # 封板率 / 炸板率 / 晋级率 / 成交额
    # 炸板 = 涨停打开次数 ≥ 1（即开过板，无论回封与否）
    zha = sum(1 for r in lu if int(fnum(r.get("open_times", 0))) >= 1)
    zt_rate = round(zt / (zt + zha), 4) if (zt + zha) else None  # 模板处 * 100 转%
    zha_rate = round(zha / (zt + zha), 4) if (zt + zha) else None  # 炸板率
    # 高板接力密度：今日 2板以上票数 / 总涨停（template 渲染时 * 100 转%）
    lb2 = sum(1 for r in lu if int(fnum(r.get("lbc", 0))) >= 2)
    promote_rate = round(lb2 / zt, 4) if zt else None

    nodes = pick_nodes(lu)
    # 全市场成交额(亿)：优先 updown.AMOUNT_TOTAL，没有就 None
    amount_e = None
    for src in (updown, mo):
        for k in ("AMOUNT_TOTAL", "TOTAL_AMOUNT", "AMOUNT", "TURNOVER", "TOTAL_TURNOVER"):
            v = fnum(src.get(k))
            if v:
                amount_e = round(v / 1e8, 2)  # 默认以"亿为单位"：>1e6 视为万，转换
                break
        if amount_e is not None:
            break

    # 载入盘后预取的 K线（由 fetch_klines.py 生成 klines_<date>.json）
    kline_path = os.path.join(HERE, f"klines_{date.replace('-','')}.json")
    klines = {}
    if os.path.exists(kline_path):
        try:
            with open(kline_path, encoding="utf-8") as f:
                klines = json.load(f)
            print(f"     [K线] 已载入 {len(klines)} 只个股预取数据")
        except Exception as e:
            print(f"     [K线] 载入失败: {e}")
    for r in lu:
        k = klines.get(str(r["code"]))
        if k:
            r["kline"] = {
                "daily": k.get("daily", []),
                "intraday": k.get("intraday", []),
                "prev_close": k.get("prev_close"),
                "limit_price": k.get("limit_price"),
            }
            if k.get("turnover_yi"):
                r["amount"] = k["turnover_yi"]
    for n in nodes:
        k = klines.get(str(n["code"]))
        if k:
            n["kline"] = {
                "daily": k.get("daily", []),
                "intraday": k.get("intraday", []),
                "prev_close": k.get("prev_close"),
                "limit_price": k.get("limit_price"),
            }
            if k.get("turnover_yi"):
                n["amount"] = k["turnover_yi"]

    # —— 重算连板：识别断板+反包，标注为「断板当日板数+1」——
    tk = date.replace("-", "")
    for r in lu:
        k = klines.get(str(r["code"]))
        daily = (k or {}).get("daily", [])
        r["lbc_raw"] = r.get("lbc")  # 同花顺原值留底，便于核对
        if daily:
            cur, prev = board_struct(daily, (k or {}).get("limit_ratio", 0.1), tk)
        else:
            cur, prev = r.get("lbc", 0), 0
        if prev >= 1:
            r["lbc"] = cur
            r["is_fanbao"] = True
            r["board_label"] = f"{prev}+{cur}"
        else:
            # 短线客视角：连续涨停板数（只看 close-to-close 连续），不再用同花顺"累计板数"
            # 同花顺 "连续涨停天数" 字段含"跨日累计"（如 5天3板会把早期单日涨停也算进），与短线客对"几板"的语义不一致
            if cur >= 1:
                r["lbc"] = cur
                r["is_fanbao"] = False
                r["board_label"] = "首板" if cur == 1 else f"{cur}板"
            else:
                # 日 K 没找到涨停信号（罕见，多为缺数据）；回退同花顺原值
                r["lbc"] = r["lbc_raw"]
                r["is_fanbao"] = False
                r["board_label"] = "首板" if r["lbc"] == 1 else f"{r['lbc']}板"
    # 依赖 lbc 的指标重算（覆盖旧值）
    max_lbc = max((r["lbc"] for r in lu), default=0)
    lb2 = sum(1 for r in lu if int(fnum(r.get("lbc", 0))) >= 2)
    promote_rate = round(lb2 / zt, 4) if zt else None
    cycle = judge(zt, dt, max_lbc, zha_rate, promote_rate, mo,
                  up_ratio if has_breadth else None,
                  low5 if has_breadth else None,
                  high5 if has_breadth else None)
    # 节点票同步真实连板 / 标注
    for n in nodes:
        src = next((x for x in lu if str(x["code"]) == str(n["code"])), None)
        if src:
            n["lbc"] = src["lbc"]
            n["board_label"] = src["board_label"]
            n["is_fanbao"] = src["is_fanbao"]
            n["lbc_raw"] = src["lbc_raw"]

    # 次日溢价(T+1)：集合竞价开盘相对 T 日收盘的真实涨跌幅
    # 优先级：next_open_*.json(通达信真实开盘) > auction_*.json > inline 兜底 > 待 T+1 竞价
    nxt, t1b = load_next_open(date, HERE)
    if nxt:
        for r in lu:
            nv = nxt.get(str(r["code"]))
            if nv:
                r["next_premium"] = nv.get("premium")
                r["next_open"] = nv.get("open")
        print(f"     [次日溢价] 真实 T+1 开盘价 命中 {len(nxt)} 只 (T+1={t1b})")
    else:
        auction, t1_date = load_auction(date, HERE)
        if auction:
            for r in lu:
                a = auction.get(str(r["code"]))
                if a:
                    r["next_premium"] = a.get("premium")
                    r["next_open"] = a.get("open")
            print(f"     [竞价溢价] auction 命中 {len(auction)} 只 (T+1={t1_date})")
        else:
            # 最后兜底：从 data_{T+1}.json 取 T+1 当日那根开盘（仅限 T+1 仍在涨停池的票）
            try:
                _all_inline = scan_all_data_files(HERE)
                _n = fill_premium_from_inline(lu, _all_inline, date)
                if _n:
                    print(f"     [次日溢价] inline 兜底补回 {_n} 只")
            except Exception as _e:
                print(f"     [次日溢价] inline 兜底跳过: {_e}")
            print(f"     [次日溢价] 暂无 T+1 数据 (待 {next_trading_day(date)} 09:25 后自动回填)")

    # 题材聚合必须在 kline / next_premium 挂载之后，才能带出 has_k 与溢价
    themes = agg_themes(lu)

    market = {
        "limit_up": zt,
        "limit_down": dt or None,
        "up": int(red) or None,
        "down": int(green) or None,
        "amount": amount_e,
        "zt_rate": zt_rate,
        "zha_rate": zha_rate,        # 炸板率
        "promote_rate": promote_rate,  # 2板以上占比
        "max_lbc": max_lbc,           # 最高板
        "zt_dt_ratio": round(zt / max(dt, 1), 2) if zt else None,  # 涨跌停家数比
    }

    # 跌停池详情（前 8 只）
    limit_down_stocks = inp.get("limit_down_stocks", []) or []

    DATA = {
        "date": date,
        "next_day": next_trading_day(date),   # T+1 日期，用于"待T+1竞价"占位
        "mode": {
            "after-close": "盘后收盘复盘",
            "midday": "午间收盘复盘",
            "bidding": "次日开盘竞价策略",
        }.get(mode, "盘中复盘"),
        "cycle": cycle,
        "market": market,
        "tianti": sorted(lu, key=lambda r: -r["lbc"]),
        "themes": themes,
        "nodes": nodes,
        "limit_down_stocks": limit_down_stocks[:8],
        "review": inp.get("review", {}) or {},
        "opening": build_opening(nodes, inp.get("bidding", []), mo, up_ratio) if mode == "bidding" else {},
        "discipline": inp.get("discipline"),
    }

    with open(TPL, encoding="utf-8") as f:
        tpl = f.read()
    # 导出独立数据文件（供日期切换时 fetch，避免多日期重复打包渲染代码）
    data_file = os.path.join(HERE, f"data_{date.replace('-','')}.json")
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(DATA, f, ensure_ascii=False)
    # 扫描本目录所有 data_*.json，生成可复盘日期清单（降序，最新在前）
    # 同时把每份 DATA 完整内嵌进 HTML（dates_inline），保证 file:// 双击也能切换
    import glob as _glob
    dates = []
    dates_inline = {}
    for _p in sorted(_glob.glob(os.path.join(HERE, "data_*.json")), reverse=True):
        try:
            with open(_p, encoding="utf-8") as _f:
                _d = json.load(_f)
            _dd = _d.get("date", "")
            _mode = _d.get("mode", "")
            _label = _dd + (f" · {_mode}" if _mode else "")
            _fn = os.path.basename(_p)
            dates.append({"date": _dd, "file": _fn, "label": _label})
            dates_inline[_fn] = _d
        except Exception:
            pass
    # —— 外置数据：重数据写进 wb_data.js / wb_history.js（硬盘上），HTML 只留代码，运行时 <script src> 读入 ——
    # 历史分时预内嵌（file:// 下点任意K离线秒开对应日分时）
    hist_min = {}
    hist_path = os.path.join(HERE, "history_minutes.json")
    if os.path.exists(hist_path):
        try:
            _raw = json.load(open(hist_path, encoding="utf-8"))
            # 收集 6 天涨停池里实际涨停过的个股及对应日期（用于 wb_history.js 压缩）
            _codes = set()
            _code_dates = {}
            def _walk(o, cur_date):
                if isinstance(o, dict):
                    if "code" in o:
                        cd = str(o["code"])
                        _codes.add(cd)
                        if cur_date:
                            _code_dates.setdefault(cd, set()).add(cur_date)
                    for v in o.values(): _walk(v, cur_date)
                elif isinstance(o, list):
                    for v in o: _walk(v, cur_date)
            for _k, _d in dates_inline.items():
                _d8 = _k[len("data_"):-len(".json")] if _k.startswith("data_") and _k.endswith(".json") else ""
                _walk(_d, _d8)
            # 从 6 天 K 线 daily 反推历史涨停日（close-to-close 涨幅 ≥9.9%），
            # 把"不在 6 天涨停池里、但日K 显示曾涨停"的日期也补进 wanted（如 002552 的 8/4）
            def _scan_klines(o):
                if isinstance(o, dict):
                    if "code" in o and isinstance(o.get("kline"), dict):
                        code = str(o["code"])
                        daily = o["kline"].get("daily") or []
                        closes = [(b[0], b[4]) for b in daily if b and len(b) >= 6]
                        for i in range(1, len(closes)):
                            prev_c = closes[i-1][1]
                            cur_c = closes[i][1]
                            if prev_c > 0 and abs((cur_c - prev_c) / prev_c) >= 0.099:
                                _code_dates.setdefault(code, set()).add(str(closes[i][0]).replace("-",""))
                    for v in o.values(): _scan_klines(v)
                elif isinstance(o, list):
                    for v in o: _scan_klines(v)
            for _d in dates_inline.values():
                _scan_klines(_d)
            # 每个票只保留"6 天涨停池中实际涨停过的日期 ±1 天"的分时（用户主要是看涨停日那天的分时）
            from datetime import datetime as _dt, timedelta as _td
            pruned = 0
            kept_pairs = 0
            for c in list(_codes):
                if c not in _raw: continue
                wanted = set()
                for d in _code_dates.get(c, set()):
                    if not d or len(d) != 8: continue
                    try:
                        dt = _dt.strptime(d, "%Y%m%d")
                        for off in (-1, 0, 1):  # 涨停日前后各 1 天，够看"前一天分时"、"当天分时"
                            wanted.add((dt + _td(days=off)).strftime("%Y%m%d"))
                    except Exception:
                        pass
                src = _raw[c]
                if not wanted:
                    keep_dates = list(src.keys())[-4:]  # 兜底
                else:
                    keep_dates = [d for d in src.keys() if d in wanted]
                if not keep_dates:
                    hist_min[c] = {}
                    continue
                hist_min[c] = {d: src[d] for d in keep_dates}
                kept_pairs += len(keep_dates)
                pruned += len(src) - len(keep_dates)
            print(f"     [历史分时] wb_history.js 保留 {len(hist_min)} 只，共 {kept_pairs} (code,date) 对；裁掉 {pruned} 对")
        except Exception as _e:
            print(f"     [历史分时] 跳过: {_e}")
    # 轻量数据（5天复盘）：wb_data.js
    from datetime import datetime as _dtm
    build_ts = _dtm.now().strftime("%Y-%m-%d %H:%M")
    data_js = ("window.WB_DATA=" + json.dumps(DATA, ensure_ascii=False) + ";\n"
               "window.WB_DATES=" + json.dumps(dates, ensure_ascii=False) + ";\n"
               "window.WB_DATES_INLINE=" + json.dumps(dates_inline, ensure_ascii=False) + ";\n"
               "window.WB_BUILD=" + json.dumps(build_ts, ensure_ascii=False) + ";\n")
    with open(os.path.join(HERE, "wb_data.js"), "w", encoding="utf-8") as f:
        f.write(data_js)
    # 重量数据（历史分时）：wb_history.js（独立文件，UI 先渲染、历史后台解析）
    hist_js = "window.WB_HIST_MIN=" + json.dumps(hist_min, ensure_ascii=False) + ";\n"
    with open(os.path.join(HERE, "wb_history.js"), "w", encoding="utf-8") as f:
        f.write(hist_js)
    print(f"     [外置] wb_data.js / wb_history.js 已写出（HTML 不再内联，体积归零）")

    if not out_path:
        out_path = os.path.join(HERE, f"workbench_{date.replace('-','')}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(tpl)   # 模板已改为读取 window.WB_*，无需 replace 注入
    # 始终同步最新版
    latest = os.path.join(HERE, "workbench_latest.html")
    with open(latest, "w", encoding="utf-8") as f:
        f.write(tpl)
    # --nodes: 仅输出节点票代码，供竞价自动化抓取用
    if "--nodes" in sys.argv:
        print(json.dumps([{"code": n["code"], "name": n["name"]} for n in nodes],
                          ensure_ascii=False))
        return
    print(f"[OK] 已生成: {out_path}")
    print(f"     日期={date} 模式={mode} 涨停={zt} 最高板={max_lbc} 涨跌比={up_ratio:.2f} 节点票={len(nodes)}")
    print(f"     周期判定: {cycle['stage']} ｜ 动作: {cycle['action']}")

if __name__ == "__main__":
    main()
