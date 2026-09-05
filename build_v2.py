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

    # 占位符替换
    out = tpl_text.replace("__WB_DATA_JSON__", wb_data)
    out = out.replace("__WB_DATES_JSON__", wb_dates)
    out = out.replace("__WB_DATES_INLINE_JSON__", wb_dates_inline)
    out = out.replace('__WB_BUILD_STR__', wb_build.replace('"', '\\"'))

    # 检查占位符是否全部替换
    remaining = [p for p in ["__WB_DATA_JSON__", "__WB_DATES_JSON__", "__WB_DATES_INLINE_JSON__", "__WB_BUILD_STR__"] if p in out]
    if remaining:
        print(f"placeholder not replaced: {remaining}", file=sys.stderr)
        sys.exit(1)

    OUT.write_text(out, encoding="utf-8")
    print(f"OK -> {OUT}  ({OUT.stat().st_size/1024/1024:.1f} MB)")
    print(f"WB_BUILD: {wb_build}")

    # ---- 轻量版：剔除历史日期内嵌的分钟分时（占体积 ~76%），日K与最新日分时全部保留 ----
    build_lite(tpl_text, wb_data, wb_dates, wb_dates_inline, wb_build)


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


def build_lite(tpl_text, wb_data, wb_dates, wb_dates_inline, wb_build):
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
    out = out.replace('__WB_BUILD_STR__', wb_build.replace('"', '\\"'))
    out = out.replace(
        "<title>情绪周期交易工作台 V2 · 弱转强节点票 · 机械触发</title>",
        "<title>情绪周期交易工作台 V2 · 轻量版（秒开）</title>",
    )
    OUT_LITE.write_text(out, encoding="utf-8")
    print(f"OK -> {OUT_LITE}  ({OUT_LITE.stat().st_size/1024/1024:.1f} MB, 轻量版)")


if __name__ == "__main__":
    main()
