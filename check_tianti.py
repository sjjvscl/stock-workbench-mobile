import urllib.request, json, time
t0 = time.time()
req = urllib.request.Request("https://sjjvscl.github.io/stock-workbench-mobile/index.html", headers={"User-Agent":"Mozilla/5.0"})
data = urllib.request.urlopen(req, timeout=60).read()
dt = time.time() - t0
html = data.decode("utf-8", "ignore")
print(f"下载: {len(data)/1048576:.2f}MB, 耗时: {dt:.1f}s")

# 提取 WB_DATES 最后一个日期（DATES_INLINE 是数据日，date 是数据日）
# 先查 build 字段
import re
m = re.search(r'window\.WB_BUILD\s*=\s*', html)
if m:
    s = m.end()
    dec = json.JSONDecoder()
    obj, _ = dec.raw_decode(html, s)
    if isinstance(obj, str):
        # WB_BUILD 可能是字符串化的 JSON
        try:
            obj2 = json.loads(obj)
            print(f"WB_BUILD(date={obj2.get('date')} next_day={obj2.get('next_day')} build_time={obj2.get('build_time')})")
        except:
            print(f"WB_BUILD(原始): {obj[:120]}")
    else:
        print(f"WB_BUILD(date={obj.get('date')} next_day={obj.get('next_day')} build_time={obj.get('build_time')})")

# 抽样 tianti 第一只的实际 next_premium
m = re.search(r'window\.WB_DATA\s*=\s*', html)
if m:
    s = m.end()
    dec = json.JSONDecoder()
    obj, _ = dec.raw_decode(html, s)
    if isinstance(obj, str): obj = json.loads(obj)
    tianti = obj.get('tianti', [])[:5]
    print("\n天梯前5只 next_premium 抽样：")
    for r in tianti:
        np = r.get('next_premium')
        nd = r.get('next_open')
        print(f"  {r.get('name')} ({r.get('code')}) 板数={r.get('lbc')}  next_premium={np}  next_open={nd}")

# 查 themes[0].stocks[] 的 next_premium（题材列表）
themes = obj.get('themes', [])
if themes:
    print(f"\n题材数={len(themes)} 题材[0]={themes[0].get('name')} 股票数={len(themes[0].get('stocks',[]))}")
    for s_ in themes[0]['stocks'][:3]:
        print(f"  {s_.get('name')} next_premium={s_.get('next_premium')} next_open={s_.get('next_open')}")
