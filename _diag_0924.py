import re, json

html = open("auction_ths.html", encoding="utf-8").read()
m = re.search(r'<script id="auctionData" type="application/json">(.*?)</script>', html, re.S)
data = json.loads(m.group(1))
payload = data["payloads"]["20260924"]

def shape(o, depth=0, maxd=4):
    pad = "  "*depth
    if isinstance(o, dict):
        ks = list(o.keys())[:12]
        print(f"{pad}dict keys={ks}")
        if depth < maxd:
            for k in ks[:4]:
                print(f"{pad}.{k}:")
                shape(o[k], depth+1, maxd)
    elif isinstance(o, list):
        print(f"{pad}list len={len(o)}")
        if o and depth < maxd:
            shape(o[0], depth+1, maxd)
    else:
        s = repr(o)
        print(f"{pad}{type(o).__name__}: {s[:80]}")

print("=== payload 顶层结构 ===")
shape(payload, 0, 3)
