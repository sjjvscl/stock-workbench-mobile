# -*- coding: utf-8 -*-
"""
fetch_ths_history.py · 拉取历史某日涨停池并转为 stock_workbench 输入格式
=================================================================
数据源：同花顺零登录 limit_up_pool 接口（支持 ?date=YYYYMMDD 历史查询）
输出：input_<YYYYMMDD>.json（limit_up 用通达信中文格式，market_overview/updown 留空占位
      —— stock_workbench 对空 mo/updown 已容错，情绪判定退化为按涨停数）

用法:
  python fetch_ths_history.py 20260810,20260811,20260812,20260813,20260814
  python fetch_ths_history.py            # 默认拉最近一个交易周(8/10~8/14)
"""
import urllib.request, json, ssl, sys, os, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")
HDR = {"User-Agent": UA, "Referer": "https://data.10jqka.com.cn/datacenterph/limitup/"}


def jget(url):
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        raw = r.read()
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("gbk", "ignore"))


def ts2hm(ts):
    if not ts:
        return ""
    try:
        return datetime.datetime.fromtimestamp(int(ts)).strftime("%H:%M:%S")
    except Exception:
        return ""


def fetch_date(d):
    """分页拉某日全部涨停池，返回 info[] 列表"""
    allinfo, page = [], 1
    while True:
        url = (f"https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool"
               f"?page={page}&limit=200"
               f"&field=199112,10,9001,330329,330325,9002,330324,330332,133971,133970,1968584,3475914,9004"
               f"&filter=HS,GEM2STAR&order_field=330329&order_type=0&date={d}")
        try:
            data = jget(url)
        except Exception as e:
            print(f"    ! {d} 第{page}页失败: {e}")
            break
        info = (data.get("data") or {}).get("info") or []
        allinfo += info
        total = (data.get("data") or {}).get("page", {}).get("total", 0)
        if not info or len(allinfo) >= total:
            break
        page += 1
    return allinfo


def convert(info):
    """同花顺英文格式 -> 通达信中文格式(适配 parse_limit_up)"""
    out = []
    for r in info:
        hd = (r.get("high_days") or "")
        m = re.search(r"(\d+)天(\d+)板", hd)
        lbc = int(m.group(2)) if m else 1
        reason = (r.get("reason_type") or "").replace("+", ".")  # parse 用 . 分隔题材
        last = ts2hm(r.get("last_limit_up_time"))
        first = ts2hm(r.get("first_limit_up_time")) or last     # 无首封时用末封兜底
        out.append({
            "sec_code": r.get("code"),
            "sec_name": r.get("name"),
            "chg": float(r.get("change_rate") or 0),
            "连续涨停天数": lbc,
            "几天几板": hd,
            "涨停原因": reason,
            "板型": (r.get("limit_up_type") or ""),
            "封单金额0#": float(r.get("order_amount") or 0),
            "涨停成交额(万)": 0,         # 同花顺接口无此字段，留0
            "涨停打开次数": int(r.get("open_num") or 0),
            "首次涨停时间": first,
            "最近涨停时间": last,
            "封成比": 0,
        })
    return out


def main():
    if len(sys.argv) > 1:
        dates = sys.argv[1].split(",")
    else:
        dates = ["20260810", "20260811", "20260812", "20260813", "20260814"]
    for d in dates:
        info = fetch_date(d)
        lu = convert(info)
        date_str = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        out = {
            "date": date_str,
            "mode": "after-close",
            "limit_up": lu,
            "market_overview": {},   # 占位：stock_workbench 已容错
            "updown": {},            # 占位
        }
        op = os.path.join(HERE, f"input_{d}.json")
        with open(op, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f"[OK] {op}: 涨停 {len(lu)} 只 | 日期={date_str}")


if __name__ == "__main__":
    main()
