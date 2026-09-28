import re, json

html = open("auction_ths.html", encoding="utf-8").read()
m = re.search(r'<script id="auctionData" type="application/json">(.*?)</script>', html, re.S)
data = json.loads(m.group(1))
print("可选日期:", data.get("dates"))
print("默认日:", data.get("default"))

targets = ["雷科防务","天威视讯","贝瑞基因","华神科技","皓宸医疗","合富中国",
           "雪龙集团","襄阳轴承","长华集团","中马传动","洛轴股份","霍莱沃","盛景微"]

date8 = "20260924"
payload = data["payloads"][date8]

def find_items(p):
    items = []
    for key in ("merged","groups","themes","modes"):
        if key in p and isinstance(p[key], list):
            for g in p[key]:
                if isinstance(g, dict):
                    for s in g.get("stocks", g.get("items", [])):
                        items.append(s)
    return items

items = find_items(payload)
if not items and "stocks" in payload:
    items = payload["stocks"]

by_name = {}
for it in items:
    nm = it.get("name") or it.get("stock_name")
    if nm:
        by_name.setdefault(nm, it)

print("\n=== 0924 merged 视角：截图 13 只票溢价核验 ===")
all_ok = True
for t in targets:
    it = by_name.get(t)
    if not it:
        print(f"  [缺失] {t} 未在 payload 中找到")
        all_ok = False
        continue
    prem = it.get("next_premium", it.get("premium"))
    print(f"  {t:6s}  next_premium={prem}")
    if prem is None:
        all_ok = False
print("\n全部 13 只均有溢价数字:", all_ok)
