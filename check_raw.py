import urllib.request, json, re
# raw github 实时
req = urllib.request.Request("https://raw.githubusercontent.com/sjjvscl/stock-workbench-mobile/d0b4d07/index.html", headers={"User-Agent":"Mozilla/5.0"})
data = urllib.request.urlopen(req, timeout=60).read()
html = data.decode("utf-8","ignore")
print(f"raw d0b4d07 size: {len(data)/1048576:.2f}MB")

m = re.search(r'window\.WB_DATA\s*=\s*', html)
if not m: print("no WB_DATA"); raise SystemExit
s = m.end()
obj, end = json.JSONDecoder().raw_decode(html, s)
if isinstance(obj, str): obj = json.loads(obj)
tianti = obj.get('tianti', [])
np_count = sum(1 for r in tianti if r.get('next_premium') is not None)
print(f'tianti={len(tianti)} next_premium有值={np_count}')
sample = next((r for r in tianti if r.get('next_premium') is not None), None)
if sample: print(f'  样本: {sample.get("name")} next_premium={sample.get("next_premium")}')
