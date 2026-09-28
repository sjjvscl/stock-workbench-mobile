import re, json

html = open("auction_ths.html", encoding="utf-8").read()
m = re.search(r'<script id="auctionData" type="application/json">(.*?)</script>', html, re.S)
data = json.loads(m.group(1))
payload = data["payloads"]["20260924"]

modes = payload["modes"]
print("modes 类型:", type(modes), "长度:", len(modes) if isinstance(modes, list) else "n/a")
if isinstance(modes, list):
    for i, md in enumerate(modes):
        if isinstance(md, dict):
            print(f"\n--- modes[{i}] keys={list(md.keys())[:15]}")
            # 找组的字段
            for gk in ("groups","themes","items","stocks","merged"):
                if gk in md:
                    v = md[gk]
                    print(f"    {gk}: type={type(v).__name__} len={len(v) if hasattr(v,'__len__') else 'n/a'}")
        else:
            print(f"modes[{i}] = {type(md).__name__}: {repr(md)[:100]}")

# 尝试从第一个 mode 取一个 sample group
print("\n=== 取 modes[0] 第一个组 sample ===")
md0 = modes[0] if isinstance(modes, list) else None
if isinstance(md0, dict):
    for gk in ("groups","themes","items","stocks","merged"):
        if gk in md0 and isinstance(md0[gk], list) and md0[gk]:
            g0 = md0[gk][0]
            print(f"{gk}[0] type={type(g0).__name__} keys={list(g0.keys())[:20] if isinstance(g0,dict) else 'n/a'}")
            if isinstance(g0, dict):
                # 找股票数组
                for sk in ("stocks","items","list"):
                    if sk in g0 and isinstance(g0[sk], list) and g0[sk]:
                        s0 = g0[sk][0]
                        print(f"  {gk}[0].{sk}[0] keys={list(s0.keys())[:25] if isinstance(s0,dict) else type(s0)}")
                        print(f"  sample={json.dumps(s0, ensure_ascii=False)[:200]}")
                        break
            break
