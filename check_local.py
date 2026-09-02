import re, json
# 直接读 workbench_v2.html 本地最新文件
for f in [r'D:/炒股/workbench_v2.html', r'D:/炒股/workbench_mobile_v2.html', r'D:/炒股/workbench_mobile.html']:
    txt = open(f, encoding='utf-8').read()
    m = re.search(r'window\.WB_DATA\s*=\s*', txt)
    if not m:
        print(f, 'NO WB_DATA'); continue
    s = m.end()
    obj, end = json.JSONDecoder().raw_decode(txt, s)
    if isinstance(obj, str): obj = json.loads(obj)
    tianti = obj.get('tianti', [])
    np_count = sum(1 for r in tianti if r.get('next_premium') is not None)
    nd_count = sum(1 for r in tianti if r.get('next_open') is not None)
    sample = next((r for r in tianti if r.get('next_premium') is not None), None)
    print(f'{f.split(chr(92))[-1]}: tianti={len(tianti)} next_premium有值={np_count} next_open有值={nd_count}')
    if sample: print(f'  样本: {sample.get("name")} ({sample.get("code")}) next_premium={sample.get("next_premium")} next_open={sample.get("next_open")}')
    # themes
    themes = obj.get('themes', [])
    if themes:
        sample_t = next((s for s in themes[0].get('stocks',[]) if s.get('next_premium') is not None), None)
        np_count_t = sum(1 for t in themes for s in t.get('stocks',[]) if s.get('next_premium') is not None)
        print(f'  themes={len(themes)} 题材样本[{themes[0].get("name")}]: stocks={len(themes[0].get("stocks",[]))}')
        if sample_t: print(f'    样本: {sample_t.get("name")} next_premium={sample_t.get("next_premium")} next_open={sample_t.get("next_open")}')
        print(f'    全题材next_premium有值总数={np_count_t}')
