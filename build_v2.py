# -*- coding: utf-8 -*-
"""build_v2.py: 从 index.html 提取数据变量，注入 v2_template.html，生成 workbench_v2.html。"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
TPL = HERE / "v2_template.html"
OUT = HERE / "workbench_v2.html"


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


if __name__ == "__main__":
    main()
