# -*- coding: utf-8 -*-
"""build_v2.py: 从数据文件提取 WB_* 变量，注入 v2_template.html，生成 workbench_v2.html。

默认数据源为 D:/炒股/workbench_mobile_v2.html（build_fast.py 每天收盘后更新的 V1 主文件），
输出到 D:/炒股/workbench_v2.html（deploy_github.py 的部署源）。
可用命令行覆盖：build_v2.py [源HTML] [输出HTML]
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TPL = HERE / "v2_template.html"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "workbench_mobile_v2.html"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "workbench_v2.html"
OUT_LITE = OUT.with_name("workbench_v2_lite.html")
# 全市场个股 → 所属行业（异业票校验用）。由 fetch_industry_map.py 生成；缺失时注入空表不报错。
IND_MAP = ROOT / "_industry_map.json"
# 每日 data_YYYYMMDD.json 所在目录（refresh_cloud.py 的 SOURCE）。
# ⑨ 次日买点预期池的 B 组要跨日比对「昨日最高板今日是否断板」，前端只有当日的 WB_DATA，
# 所以在这里补一份极小的断板清单注入进去。目录不存在时静默降级为空表。
DATA_DIR = Path(r"C:/Users/Administrator/WorkBuddy/2026-08-15-15-20-08/stock_workbench")
# 开盘啦「涨停天梯」归档目录（fetch_kpl_ladder.py 写入）。⑧ 之前先看这里：
# ⑦ 题材角色的分组要按开盘啦板块走（用户 2026-09-23 定的口径），但归档只有 build 阶段读得到，
# 前端拿不到，所以在这里合并进 WB_DATA["kpl"]。缺归档时静默降级，⑦ 回落现有 THEME_RULES 分组。
KPL_DIR = ROOT / "开盘啦天梯"
# 爆量涨停选股器产出目录（D:/炒股/screener/run_all.py 写入 out/screen_<YYYYMMDD>.json）。
# 选股器是独立脚本，按扫描日归档；build 阶段只取与构建数据日一致的那一份，
# 日期对不上就注入 null，⑮ 自动降级成提示行，绝不拿别的日期冒充当天。
SCREEN_DIR = ROOT / "screener" / "out"
# 注入前端只需这些字段。其余（tags / all_groups / imag_hits / theme_driver / first_time /
# last_time / feng_ratio / is_new_listing …）前端用不上，裁掉后单日注入体量约 5 KB。
SCREEN_STOCK_FIELDS = (
    "code", "name", "bnum", "high_days", "limit_up_type", "reason", "theme",
    "close", "turnover", "float_mv_yi", "amt_yi", "amt_max120_yi", "ratio",
    "vr5", "vr20", "hist_high", "order_amount_yi", "open_num",
    "theme_today_n", "theme_uniq20", "theme_hits5", "theme_hits20", "imagination",
    "qnotes", "score", "tier", "rank", "is_leader", "earliest",
    "score_surge", "score_heat", "score_space", "score_quality",
)
SCREEN_THEME_FIELDS = ("name", "today", "hits5", "hits20", "uniq")


def build_kpl_info(cur_date: str):
    """把当日开盘啦板块读成 {date, plates:[{name,code,zt,codes}], byCode:{code:name}}。

    ⚠ 板块成交额没有注入：开盘啦 App 上那个数字是「整个板块」（含未涨停成员）的成交额，
      它的区块接口只给我们涨停股，算出来的合计能差三倍以上，宁可不显示也不要给错数。
    """
    if not cur_date:
        return None
    f = KPL_DIR / f"{str(cur_date).replace('-', '')}.json"
    if not f.exists():
        return None
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 开盘啦归档读取失败({e})，⑦ 回落规则表分组", file=sys.stderr)
        return None
    plates, by_code = [], {}
    for p in raw.get("plates") or []:
        name = str(p.get("name") or "").strip()
        codes = [str(c) for c in (p.get("codes") or []) if c]
        if not name or not codes:
            continue
        plates.append({"name": name, "code": str(p.get("code") or ""), "codes": codes})
        for c in codes:
            by_code.setdefault(c, name)
    if not plates:
        return None
    return {"date": raw.get("date") or cur_date, "plates": plates, "byCode": by_code}


def build_break_info(cur_date: str):
    """算出「昨日 2 板以上今日断板」的票，供 ⑨ 买点池 B 组（断板补涨 / 低位试错）使用。

    断板是跨日概念，前端拿不到昨日涨停池，必须在 build 阶段算。
    只带出极少量字段（代码/名称/昨日板位/原始题材标签/reason），前端再用 themeGroupName()
    映射到今日的归并题材组，这样口径与 ⑥⑦ 完全一致。

    任何一步失败都返回空列表，绝不让 build 挂掉。
    """
    try:
        files = sorted(DATA_DIR.glob("data_*.json"))
        if len(files) < 2:
            return []
        prev = json.loads(files[-2].read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 断板信息读取失败({e})，⑨ 买点池 B 组降级为空", file=sys.stderr)
        return []

    # 防线：data 目录里的最新一天必须就是本次构建的数据日，否则说明数据目录与源 HTML 不同步，
    # 拿错一天的断板清单比没有更糟，直接放弃。
    try:
        newest = json.loads(files[-1].read_text(encoding="utf-8")).get("date")
        if cur_date and newest and newest != cur_date:
            print(f"[warn] data 目录最新日 {newest} != 构建数据日 {cur_date}，跳过断板注入", file=sys.stderr)
            return []
    except Exception:
        pass

    pmax = (prev.get("market") or {}).get("max_lbc") or 0
    today_codes = {str(t.get("code")) for t in (json.loads(files[-1].read_text(encoding="utf-8")).get("tianti") or [])}
    out = []
    for t in (prev.get("tianti") or []):
        lbc = t.get("lbc") or 0
        if lbc < 2:
            continue                       # 只关心 2 板以上的断板，首板断板太杂
        c = str(t.get("code"))
        if c in today_codes:
            continue                       # 今日仍涨停 = 没断
        out.append({
            "code": c, "name": t.get("name"), "lbc": lbc,
            "is_top": bool(lbc == pmax),   # 是否昨日最高板（空间板）
            "reason": t.get("reason") or "", "theme": t.get("theme") or "",
        })
    out.sort(key=lambda x: (-x["lbc"], x["code"]))
    return out[:14]


def build_screener_info(cur_date: str) -> str:
    """读 screener/out/screen_<date>.json，投影成前端需要的精简结构，返回 JSON 字符串。

    日期以 WB_DATA 的 date 为准（选股器按扫描日归档）。文件缺失、解析失败、日期不一致
    一律返回 "null"，⑮ 显示提示行，不影响其它板块，也绝不让 build 挂掉。
    """
    if not cur_date:
        return "null"
    d8 = str(cur_date).replace("-", "")
    f = SCREEN_DIR / f"screen_{d8}.json"
    if not f.exists():
        print(f"选股器：无 {f.name}，⑮ 提示「未扫描」")
        return "null"
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 选股器结果读取失败({e})，⑮ 提示「未扫描」", file=sys.stderr)
        return "null"
    got = str(raw.get("date") or "").replace("-", "")
    if got and got != d8:
        print(f"[warn] 选股器结果日期 {got} != 构建数据日 {d8}，跳过注入", file=sys.stderr)
        return "null"

    def proj(o, fields):
        return {k: o.get(k) for k in fields if o.get(k) is not None}

    stocks = [proj(s, SCREEN_STOCK_FIELDS) for s in (raw.get("stocks") or [])]
    if not stocks:
        print("选股器：结果为空，⑮ 提示「未扫描」")
        return "null"
    out = {
        "date": raw.get("date") or cur_date,
        "generated": raw.get("generated") or "",
        "market": raw.get("market") or {},
        "params": raw.get("params") or {},
        "stocks": stocks,
        "theme_top": [proj(t, SCREEN_THEME_FIELDS) for t in (raw.get("theme_top") or [])],
    }
    js = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    n_pick = sum(1 for s in stocks if s.get("tier") != "不入选")
    print(f"选股器：{len(stocks)} 只爆量（达标入选 {n_pick} 只）· 题材榜 {len(out['theme_top'])} 个 · 注入 {len(js)/1024:.1f} KB")
    return js


def extract_var(text: str, name: str) -> str:
    """用 JSON 解码器精确截取 window.<name>= 后的 JSON 原文（不重新序列化，保证体积/转义不变）。"""
    i = text.find("window." + name + "=")
    if i < 0:
        raise ValueError(f"not found: window.{name}=")
    start = i + len("window." + name + "=")
    stripped = text[start:].lstrip()
    off = len(text[start:]) - len(stripped)
    obj, end = json.JSONDecoder().raw_decode(stripped)
    if obj is None:
        raise ValueError(f"empty json: {name}")
    return stripped[:end]


def extract_build(text: str) -> str:
    m = re.search(r'window\.WB_BUILD="([^"]*)"', text)
    if not m:
        return ""
    return m.group(1)


def main():
    src_text = SRC.read_text(encoding="utf-8")
    tpl_text = TPL.read_text(encoding="utf-8")

    wb_data = extract_var(src_text, "WB_DATA")
    wb_dates = extract_var(src_text, "WB_DATES")
    wb_dates_inline = extract_var(src_text, "WB_DATES_INLINE")
    wb_build = extract_build(src_text)

    # 校验 JSON 合法性（防止提取错误）
    for nm, s in (("WB_DATA", wb_data), ("WB_DATES", wb_dates), ("WB_DATES_INLINE", wb_dates_inline)):
        try:
            json.loads(s)
        except Exception as e:
            print(f"JSON invalid: {nm}: {e}", file=sys.stderr)
            sys.exit(1)

    # 行业表：只保留当日有数据的代码（WB_DATA 里出现的所有 code），几百条即可，体积可忽略
    ind_all = {}
    if IND_MAP.exists():
        try:
            ind_all = json.loads(IND_MAP.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[warn] 行业表读取失败({e})，异业校验降级为空", file=sys.stderr)
            ind_all = {}
    used_codes = set(re.findall(r'"code"\s*:\s*"(\d{6})"', wb_data))
    ind = {c: ind_all[c] for c in used_codes if c in ind_all}
    ind_json = json.dumps(ind, ensure_ascii=False, sort_keys=True)
    print(f"行业表：全市场 {len(ind_all)} 只，当日命中 {len(ind)} 只")

    # 断板清单（⑧ 买点池 B 组用）
    try:
        cur_date = json.loads(wb_data).get("date")
    except Exception:
        cur_date = None
    brk = build_break_info(cur_date)
    brk_json = json.dumps(brk, ensure_ascii=False, separators=(",", ":"))
    n_top = sum(1 for b in brk if b.get("is_top"))
    print(f"断板清单：{len(brk)} 只（其中昨日最高板 {n_top} 只）")

    # 爆量涨停选股器结果（⑮ 用）
    scr_json = build_screener_info(cur_date)

    # 开盘啦板块：⑦ 题材角色的分组口径（2026-09-23 起）。注入进 WB_DATA 而不是新增占位符，
    # 这样其它走同一模板的产物（workbench_latest.html 等）不用改，没有 kpl 字段时前端自动回落。
    kpl = build_kpl_info(cur_date)
    if kpl:
        try:
            obj = json.loads(wb_data)
            obj["kpl"] = kpl
            wb_data = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            print(f"开盘啦板块：{len(kpl['plates'])} 个，覆盖 {len(kpl['byCode'])} 只涨停（⑦ 按它分组）")
        except Exception as e:
            print(f"[warn] 开盘啦板块注入失败({e})，⑦ 回落规则表分组", file=sys.stderr)
    else:
        print("开盘啦板块：无当日归档，⑦ 回落 THEME_RULES 分组")

    # 占位符替换
    out = tpl_text.replace("__WB_DATA_JSON__", wb_data)
    out = out.replace("__WB_DATES_JSON__", wb_dates)
    out = out.replace("__WB_DATES_INLINE_JSON__", wb_dates_inline)
    out = out.replace("__WB_INDUSTRY_JSON__", ind_json)
    out = out.replace("__WB_BREAK_JSON__", brk_json)
    out = out.replace("__WB_SCREENER_JSON__", scr_json)
    out = out.replace('__WB_BUILD_STR__', wb_build.replace('"', '\\"'))

    # 检查占位符是否全部替换
    remaining = [p for p in ["__WB_DATA_JSON__", "__WB_DATES_JSON__", "__WB_DATES_INLINE_JSON__",
                             "__WB_INDUSTRY_JSON__", "__WB_BREAK_JSON__", "__WB_SCREENER_JSON__",
                             "__WB_BUILD_STR__"] if p in out]
    if remaining:
        print(f"placeholder not replaced: {remaining}", file=sys.stderr)
        sys.exit(1)

    OUT.write_text(out, encoding="utf-8")
    print(f"OK -> {OUT}  ({OUT.stat().st_size/1024/1024:.1f} MB)")
    print(f"WB_BUILD: {wb_build}")

    # ---- 轻量版：剔除历史日期内嵌的分钟分时（占体积 ~76%），日K与最新日分时全部保留 ----
    build_lite(tpl_text, wb_data, wb_dates, wb_dates_inline, wb_build, ind_json, brk_json, scr_json)


def strip_intraday(obj):
    """递归剔除 kline.intraday（分钟分时），保留 daily/prev_close/limit_price。"""
    if isinstance(obj, dict):
        k = obj.get("kline")
        if isinstance(k, dict):
            k.pop("intraday", None)
        for v in obj.values():
            strip_intraday(v)
    elif isinstance(obj, list):
        for v in obj:
            strip_intraday(v)


def build_lite(tpl_text, wb_data, wb_dates, wb_dates_inline, wb_build, ind_json="{}", brk_json="[]", scr_json="null"):
    """生成 workbench_v2_lite.html：历史日期的分时改为按需加载（hist/ 懒加载 + 联网兜底）。
    关键：当前日（WB_DATA.date）的内嵌副本必须保留完整分时——
    否则用户切到历史日再切回当前日时，applyDate 用的是内嵌副本，KMAP 重注册时分时=0。"""
    try:
        inline = json.loads(wb_dates_inline)
    except Exception as e:
        print(f"lite skip (inline json invalid): {e}", file=sys.stderr)
        return
    # 取当前日（WB_DATA.date）= 需保留完整分时的"最新日"
    try:
        latest_date = json.loads(wb_data).get("date")
    except Exception:
        latest_date = None
    for _k, day in inline.items():
        if isinstance(day, dict):
            if latest_date and day.get("date") == latest_date:
                continue   # 当前日副本不剥：切回当天时跌停/涨停/节点票当日分时可用
            strip_intraday(day)
    lite_data = wb_data  # 最新日保留完整分时（复盘当天要看分时）
    lite_inline = json.dumps(inline, ensure_ascii=False, separators=(",", ":"))
    out = tpl_text.replace("__WB_DATA_JSON__", lite_data)
    out = out.replace("__WB_DATES_JSON__", wb_dates)
    out = out.replace("__WB_DATES_INLINE_JSON__", lite_inline)
    out = out.replace("__WB_INDUSTRY_JSON__", ind_json)
    out = out.replace("__WB_BREAK_JSON__", brk_json)
    out = out.replace("__WB_SCREENER_JSON__", scr_json)
    out = out.replace('__WB_BUILD_STR__', wb_build.replace('"', '\\"'))
    out = out.replace(
        "<title>情绪周期交易工作台 V2 · 弱转强节点票 · 机械触发</title>",
        "<title>情绪周期交易工作台 V2 · 轻量版（秒开）</title>",
    )
    OUT_LITE.write_text(out, encoding="utf-8")
    print(f"OK -> {OUT_LITE}  ({OUT_LITE.stat().st_size/1024/1024:.1f} MB, 轻量版)")


if __name__ == "__main__":
    main()
