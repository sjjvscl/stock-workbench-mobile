import re, json

html = open("auction_ths.html", encoding="utf-8").read()
m = re.search(r'<script id="auctionData" type="application/json">(.*?)</script>', html, re.S)
data = json.loads(m.group(1))
payload = data["payloads"]["20260924"]

modes = payload["modes"]
print("modes 是 dict, keys =", list(modes.keys()))
for mk, mv in modes.items():
    print(f"\n--- modes[{mk!r}] type={type(mv).__name__}", end="")
    if isinstance(mv, list):
        print(f" len={len(mv)}")
        if mv:
            e0 = mv[0]
            print(f"    [0] type={type(e0).__name__} keys={list(e0.keys())[:15] if isinstance(e0,dict) else 'n/a'}")
            if isinstance(e0, dict):
                for sk in ("stocks","items","list","merged"):
                    if sk in e0 and isinstance(e0[sk], list) and e0[sk]:
                        s0 = e0[sk][0]
                        print(f"    [0].{sk}[0] = {json.dumps(s0, ensure_ascii=False)[:220]}")
                        break
    elif isinstance(mv, dict):
        print(f" keys={list(mv.keys())[:15]}")
    else:
        print(f" val={repr(mv)[:80]}")
