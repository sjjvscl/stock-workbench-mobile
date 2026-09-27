# -*- coding: utf-8 -*-
"""把 v2_template.html 转成 pro_template.html（优化版：合并重复板块 + 按使用时机分组 + 全局账户参数）。

为什么用变换脚本而不是手改模板：
  v2_template.html 有 3300 行，改动点 40 多处，手改一定会漏、而且以后 v2 再改就没法同步。
  这里每一条都以 assert 断言锚点命中次数，任何一处失配立刻抛错停下，不会产出半个坏模板。
  重跑幂等，改完再跑一次即可同步。

产物：D:/炒股/.github_deploy/pro_template.html
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "v2_template.html"
OUT = HERE / "pro_template.html"

h = SRC.read_text(encoding="utf-8")
LOG = []


def rep(anchor, new, cnt=1, tag=""):
    """精确替换；命中次数不等于 cnt 立刻报错（防止锚点写虚、改错地方）。"""
    global h
    n = h.count(anchor)
    assert n == cnt, f"[{tag}] 锚点命中 {n} 次，期望 {cnt} 次：{anchor[:80]!r}"
    h = h.replace(anchor, new, cnt)
    LOG.append(f"  ✓ {tag}")


def cut(start, end, tag=""):
    """截出 h 中从 start 到 end（含）的片段并从 h 中移除。"""
    global h
    assert h.count(start) == 1, f"[{tag}] start 命中 {h.count(start)} 次"
    i = h.index(start)
    j = h.index(end, i)
    assert j > i, f"[{tag}] end 在 start 之前"
    j += len(end)
    seg = h[i:j]
    h = h[:i] + h[j:]
    LOG.append(f"  ✓ {tag}（截出 {len(seg)} 字符）")
    return seg


# ============================================================================
# 1. 标题
# ============================================================================
rep("<title>情绪周期交易工作台 V2 · 弱转强节点票 · 机械触发</title>",
    "<title>情绪周期交易工作台 PRO · 弱转强节点票 · 机械触发</title>",
    tag="标题")

# ============================================================================
# 2. 增量 CSS（全部新增类名，不动 V2 既有样式；V2 已调试好的视觉一律保留）
# ============================================================================
PRO_CSS = r"""
  /* ================= PRO 优化版增量样式 =================
     原则：只新增类名，不覆盖 V2 既有类，这样 V2 调试好的视觉零风险。
     板块顺序用 CSS order 控制而不是搬 DOM，避免破坏既有渲染函数取不到的节点。 */
  .pro-body{display:flex;flex-direction:column}
  body[data-mode="pre"] [data-pro="rev"]{display:none!important}
  body[data-mode="rev"] [data-pro="pre"]{display:none!important}

  /* 1) 模式条：把「什么时候用」放在最前面，而不是把 16 个模块平铺 */
  .mode-bar{position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:8px;flex-wrap:wrap;
    background:rgba(238,241,246,.97);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
    padding:8px 0;margin-bottom:2px;border-bottom:1px solid rgba(0,0,0,.05)}
  .mode-sw{display:inline-flex;background:#dfe5ee;border-radius:11px;padding:3px;gap:3px}
  .mode-sw button{border:0;background:transparent;font:inherit;font-size:12.5px;font-weight:700;color:#4c5666;
    padding:6px 15px;border-radius:8px;cursor:pointer;line-height:1.2}
  .mode-sw button.active{background:#fff;color:var(--blue);box-shadow:var(--shadow)}
  .mode-sw button .n{font-size:10px;font-weight:600;opacity:.65;margin-left:3px}
  .mode-hint{font-size:11.5px;color:var(--muted)}
  .pro-btn{border:1px solid var(--border);background:#fff;border-radius:8px;padding:5px 10px;
    font:inherit;font-size:12px;font-weight:600;cursor:pointer;color:var(--text);white-space:nowrap}
  .pro-btn:hover{background:var(--bluebg);border-color:#bcd6ef;color:var(--blue)}
  .pro-btn.cur{border-color:var(--blue);color:var(--blue);background:var(--bluebg)}
  .acct-btn b{color:var(--red)}
  .acct-panel{display:none;gap:10px;flex-wrap:wrap;align-items:flex-end;background:#fff;border:1px solid var(--border);
    border-radius:10px;padding:9px 12px;margin:0 0 8px;box-shadow:var(--shadow)}
  .acct-panel.show{display:flex}
  .acct-panel label{display:flex;flex-direction:column;gap:3px;font-size:11px;color:var(--muted);font-weight:600}
  .acct-panel input{width:118px;font:inherit;font-size:13.5px;font-weight:700;padding:4px 7px;
    border:1px solid var(--border);border-radius:6px;background:#fafbfd}
  .acct-note{flex:1 1 100%;font-size:11.5px;color:var(--muted);line-height:1.6}

  /* 2) 全局搜索：回车跳第一个命中的板块并高亮 */
  .pro-search{flex:1 1 200px;min-width:150px;display:flex;gap:6px;align-items:center}
  .pro-search input{flex:1;font:inherit;font-size:12.5px;padding:6px 10px;border:1px solid var(--border);
    border-radius:8px;background:#fff}
  .pro-search .hit{font-size:11.5px;color:var(--muted);white-space:nowrap}
  .pro-hit{outline:2px solid var(--amber);outline-offset:2px;border-radius:var(--radius)}

  /* 3) 做 / 不做 双栏：把「结论」和「数据」分开，盘前只扫结论 */
  .dodont{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
  .dd{border-radius:10px;padding:9px 12px;border:1px solid var(--border)}
  .dd-do{background:var(--redbg);border-color:#f2c9c5}
  .dd-dont{background:#f4f6f8}
  .dd-h{font-size:12px;font-weight:800;margin-bottom:5px}
  .dd-do .dd-h{color:var(--red)}
  .dd-dont .dd-h{color:#5a6472}
  .dd li{font-size:12.5px;line-height:1.75;list-style:none;margin:2px 0}
  .dd li::before{content:"· ";font-weight:800}
  @media(max-width:720px){.dodont{grid-template-columns:1fr}}

  /* 3b) 执行清单：把「今天做这些」做成可打勾，勾选状态按日期持久化。
     直接对着「盘中忘记既定手法」这个痛点，光看清单不够，要能勾掉。 */
  .dd-tool{display:flex;align-items:center;gap:8px;margin-left:auto}
  .dd-h-row{display:flex;align-items:center;gap:8px}
  .dd-count{font-size:11px;font-weight:600;color:var(--muted)}
  .dd-reset{font-size:11px;font-weight:600;color:var(--muted);cursor:pointer;
    border:1px solid var(--border);background:transparent;border-radius:6px;padding:1px 7px}
  .dd-reset:hover{color:var(--text)}
  .dd-do li.do-li{display:flex;gap:6px;align-items:flex-start;cursor:pointer;
    border-radius:6px;padding:1px 4px;margin:1px -4px}
  .dd-do li.do-li::before{content:none}   /* 勾选行不要那个项目符号 */
  .dd-do li.do-li:hover{background:#ffffff88}
  .do-box{flex:0 0 13px;width:13px;height:13px;margin-top:3px;border-radius:4px;
    border:1.5px solid #d9a8a2;background:#fff;position:relative}
  .dd-do li.do-li.done .do-box{border-color:var(--red);background:var(--red)}
  .dd-do li.do-li.done .do-box::after{content:"";position:absolute;left:3.5px;top:0.5px;
    width:3.5px;height:7px;border:solid #fff;border-width:0 1.7px 1.7px 0;transform:rotate(42deg)}
  .dd-do li.do-li.done .do-t{text-decoration:line-through;opacity:.5}
  /* 矩阵缺行时必须显式说明，不许静默按别的阶段兜底 */
  .dd-fallback{font-size:11px;color:#8a6d00;background:#fff8e1;border:1px solid #f0e0a8;
    border-radius:6px;padding:4px 8px;margin-top:6px;line-height:1.6}
  body.dark .dd-fallback{background:#332b13;border-color:#5a4a1c;color:#e8d79a}
  body.dark .do-box{background:#2a3140;border-color:#6b5150}

  /* 4) 题材双视角 tab、纪律折叠、模块分组标题 */
  .th-pane[hidden]{display:none!important}
  .grp-head{display:flex;align-items:center;gap:8px;margin:16px 0 8px;font-size:12.5px;font-weight:800;color:#4c5666}
  .grp-head::before{content:"";width:4px;height:14px;border-radius:2px;background:var(--blue)}
  .grp-head .gm{font-weight:600;color:var(--muted);font-size:11.5px}
  .disc-more{display:none}
  .disc-more.show{display:block}
  .disc-toggle{font-size:11.5px;font-weight:700;color:var(--blue);cursor:pointer;user-select:none;
    background:var(--bluebg);border:1px solid #c5d9f5;border-radius:6px;padding:2px 9px;display:inline-block;margin-top:6px}

  /* 5) 表头吸顶在窄屏意义不大，改为数据卡流动 */
  @media(max-width:720px){
    .mode-bar{top:46px}
    .mode-hint{display:none}
    .quick-nav{top:92px}
  }

  /* 6) 深色模式（晚间复盘用；只重定义变量，不动组件样式） */
  body.dark{
    --bg:#141821;--card:#1c212c;--text:#e6eaf1;--muted:#93a0b2;
    --border:#2c3444;--red:#ff6b5e;--redbg:#3a2320;--green:#4ecf93;--greenbg:#1c3529;
    --amber:#e6a94a;--amberbg:#3a2f1c;--blue:#6aa8ee;--bluebg:#1e2c40;
    --purple:#9c8ef0;--purplebg:#292441;
    --shadow:0 1px 3px rgba(0,0,0,.4);
  }
  body.dark .mode-bar{background:rgba(20,24,33,.97)}
  body.dark .mode-sw{background:#242b38}
  body.dark .mode-sw button.active{background:#2f3948;color:var(--blue)}
  body.dark .pro-btn,body.dark .acct-panel,body.dark .pro-search input,
  body.dark .stat,body.dark .pill,body.dark .sd,
  body.dark .dd-dont{background:#1c212c;color:var(--text)}
  body.dark .dd-do{background:#3a2320}
  body.dark tr:hover td{background:#222936}
  body.dark th{background:var(--card)}
  body.dark .quick-nav{background:rgba(20,24,33,.96)}
  body.dark .quick-nav a{background:#232a37;color:var(--text)}
  body.dark .bottom-nav{background:rgba(28,33,44,.97)}
"""
rep("</style>", PRO_CSS + "</style>", tag="增量 CSS")

# ============================================================================
# 3. 模式条 + 账户面板：插在纪律条之后、topbar 之前
# ============================================================================
MODE_BAR = r"""  <!-- PRO：模式条（盘前 / 复盘）· 账户设定 · 全局搜索 -->
  <div class="mode-bar">
    <span class="mode-sw" id="modeSw">
      <button data-m="pre" class="active" onclick="setProMode('pre')">盘前 · 今天怎么打<span class="n" id="cntPre"></span></button>
      <button data-m="rev" onclick="setProMode('rev')">复盘 · 昨天发生了什么<span class="n" id="cntRev"></span></button>
    </span>
    <span class="mode-hint" id="modeHint">按使用时机分组，同一批数据不再重复出现</span>
    <button class="pro-btn acct-btn" onclick="toggleAcct()">账户 ¥<b id="acctLabel">150,000</b></button>
    <button class="pro-btn" onclick="toggleDark()" id="darkBtn">深色</button>
    <button class="pro-btn" onclick="copyDaily()">复制今日要点</button>
    <span class="pro-search">
      <input id="proQ" type="search" placeholder="搜股票名 / 代码，回车定位板块" autocomplete="off"
             onkeydown="if(event.key==='Enter')proFind()">
      <span class="hit" id="proQHit"></span>
    </span>
  </div>
  <div class="acct-panel" id="acctPanel">
    <label>账户总资金(¥)<input id="acctCap" type="number" step="1000" oninput="applyAcct()"></label>
    <label>单笔风险(%)<input id="acctRisk" type="number" step="0.5" oninput="applyAcct()"></label>
    <label>止损幅度(%)<input id="acctStop" type="number" step="0.5" oninput="applyAcct()"></label>
    <button class="pro-btn" onclick="resetAcct()">恢复默认</button>
    <div class="acct-note" id="acctNote"></div>
  </div>

"""
rep("  <div class=\"topbar\">", MODE_BAR + "  <div class=\"topbar\">", tag="模式条与账户面板")

# ============================================================================
# 4. 正文包进 .pro-body，并把每个板块打上 data-pro（模式）与 order（显示顺序）
# ============================================================================
rep("  <!-- ① 3 秒决策头版 -->",
    "  <div class=\"pro-body\" id=\"proBody\">\n  <div class=\"grp-head\" data-pro=\"pre\" style=\"order:0\">盘前 · 今天怎么打"
    "<span class=\"gm\">开盘前到 10:10 用这几个；其余板块切到「复盘」看</span></div>\n\n  <!-- 今日定调 -->",
    tag="正文容器开始 + 盘前分组标题")

rep("  <div class=\"card scan-card\" id=\"sOverview\" style=\"margin-bottom:12px\">",
    "  <div class=\"card scan-card\" id=\"sOverview\" data-pro=\"pre\" style=\"order:1;margin-bottom:12px\">",
    tag="今日定调 order1")
rep("  <div class=\"card\" id=\"sFocus\" style=\"margin-bottom:12px\">",
    "  <div class=\"card\" id=\"sFocus\" data-pro=\"pre\" style=\"order:2;margin-bottom:12px\">",
    tag="今日重点 order2")
rep("  <div class=\"card\" id=\"sBattle\" style=\"margin-bottom:12px;border-left:4px solid var(--blue)\">",
    "  <div class=\"card\" id=\"sBattle\" data-pro=\"pre\" style=\"order:3;margin-bottom:12px;border-left:4px solid var(--blue)\">",
    tag="作战卡 order3")

# 复盘分组标题插在 sCycle 之前
rep("  <!-- ② 周期阶梯 + 市场全景 -->",
    "  <div class=\"grp-head\" data-pro=\"rev\" style=\"order:10\">复盘 · 昨天发生了什么"
    "<span class=\"gm\">收盘后到次日开盘前用这些，逐层看下来</span></div>\n\n  <!-- 情绪周期阶梯 + 市场全景 -->",
    tag="复盘分组标题")
rep("  <div class=\"grid g-main\" id=\"sCycle\" style=\"margin-bottom:12px\">",
    "  <div class=\"grid g-main\" id=\"sCycle\" data-pro=\"rev\" style=\"order:11;margin-bottom:12px\">",
    tag="周期全景 order11")
rep("  <div class=\"grid g-main\" id=\"sTianti\" style=\"margin-bottom:12px\">",
    "  <div class=\"grid g-main\" id=\"sTianti\" data-pro=\"rev\" style=\"order:13;margin-bottom:12px\">",
    tag="天梯 order13")
rep("  <div class=\"card\" id=\"sScreener\" style=\"margin-bottom:12px\">",
    "  <div class=\"card\" id=\"sScreener\" data-pro=\"rev\" style=\"order:15;margin-bottom:12px\">",
    tag="选股器 order15")
# ⑰ 席位溢价：复盘用（龙虎榜是盘后数据，席位手法判定也只在事后才成立），排在选股器之后
rep("  <div class=\"card\" id=\"sSeats\" style=\"margin-bottom:12px\">",
    "  <div class=\"card\" id=\"sSeats\" data-pro=\"rev\" style=\"order:16;margin-bottom:12px\">",
    tag="席位溢价 order16")
rep("  <!-- 复盘 + 纪律 -->\n  <div class=\"grid g-main\" style=\"margin-bottom:12px\">",
    "  <!-- 复盘 + 纪律 -->\n  <div class=\"grid g-main\" data-pro=\"rev\" style=\"order:17;margin-bottom:12px\">",
    tag="复盘纪律 order17")

# ============================================================================
# 5. 结构性合并：重建 sBuyPool / sNodes / sPos / sRisk / sPlan 五个板块的排布
#    （原排布把「复盘用」的节点票和「盘前用」的仓位混在同一个 grid 里，
#      导致模式切换没法只靠 CSS 过滤，必须重新分组）
# ============================================================================
old_region = cut("  <!-- 次日买点预期池", "  </div>\n\n  <!-- 复盘 + 纪律 -->", tag="截出买点池/节点/仓位/风险/计划五块")

# 把参与重排的五个子块从旧区域里抠出来（用它们的 id 定位，互不依赖顺序）
def grab(seg, start, end, tag):
    i = seg.index(start)
    j = seg.index(end, i) + len(end)
    LOG.append(f"  ✓ 取出 {tag}")
    return seg[i:j]

blk_buypool = grab(old_region, '<div class="card" id="sBuyPool"', '</div>\n  </div>', "sBuyPool")
blk_nodes = grab(old_region, '<div class="card" id="sNodes">', '<div id="nodes"></div>\n    </div>', "sNodes")
blk_pos = grab(old_region, '<div class="card" id="sPos">', '<div id="posResult" style="margin-top:8px"></div>\n    </div>', "sPos")
blk_risk = grab(old_region, '<div class="card" id="sRisk">', '<div id="riskScan"></div>\n    </div>', "sRisk")
blk_plan = grab(old_region, '<div class="card" id="sPlan">', '<div id="scriptBox"></div>\n    </div>', "sPlan")

# 2) 买点池 + 节点票触发器 → 一个 grid（都是「盘后筛、次日打」，放一起看）
blk_buypool = blk_buypool.replace('id="sBuyPool" style="margin-bottom:12px"', 'id="sBuyPool"')
blk_buypool = blk_buypool.replace("⑧ 次日买点预期池", "次日买点池").replace("⑨ ", "")
blk_nodes = blk_nodes.replace("⑨ 节点票 / 弱转强机械触发器", "节点票 / 弱转强触发器")
NEW_REV = (
    "  <!-- 明日买点池 + 节点票触发器（同一件事的两个视角，放一块） -->\n"
    "  <div class=\"grid g-main\" data-pro=\"rev\" style=\"order:14;margin-bottom:12px\">\n"
    "    " + blk_buypool + "\n"
    "    " + blk_nodes + "\n"
    "  </div>\n\n"
)

# 3) 仓位决策 + 风险扫描 → 一个 grid（下单前要一起看的两个数）
blk_pos = blk_pos.replace("⑩ 仓位决策矩阵", "仓位决策")
blk_pos = blk_pos.replace("（周期 × 身位 → 建议仓位%）", "（周期 × 身位 → 建议仓位% · 金额按账户总资金实时换算）")
blk_pos = blk_pos.replace("风险计算器 <span class=\"sub\">（5W本金视角）</span>",
                          "单笔风险计算器 <span class=\"sub\">（按你的账户总资金，不再写死）</span>")
blk_pos = blk_pos.replace('value="50000" oninput="calcPos()"', 'oninput="calcPos()"')   # 值由 applyAcct() 填
blk_risk = blk_risk.replace("⑪ 风险扫描", "风险扫描")
blk_risk = blk_risk.replace("（开板/反包/烂板 → 明日回避清单）",
                            "（开板/反包/烂板 → 明日回避清单，即「不做清单」）")
NEW_PRE1 = (
    "  <!-- 仓位与风控（矩阵 + 计算器 + 风险扫描，下单前一起看） -->\n"
    "  <div class=\"grid g-main\" data-pro=\"pre\" style=\"order:4;margin-bottom:12px\">\n"
    "    " + blk_pos + "\n"
    "    " + blk_risk + "\n"
    "  </div>\n\n"
)

# 4) 竞价执行序 → 独占一行（原 checklist 与 ⑯ 作战卡重叠，只留独有的执行序）
blk_plan = blk_plan.replace("⑫ 明日计划", "竞价执行序")
blk_plan = blk_plan.replace("（竞价确认后回来执行）", "（9:25 前 3 分钟按顺序走一遍，不即兴）")
blk_plan = blk_plan.replace('<div id="planList"></div>\n', '')          # 节点票已由 ⑨ 完整展示，去重
blk_plan = blk_plan.replace('id="sPlan"', 'id="sPlan" data-pro="pre" style="order:5;margin-bottom:12px"')
NEW_PRE2 = "  <!-- 竞价执行序 -->\n  " + blk_plan + "\n\n"

rep('  <div class="grid g-main" data-pro="rev" style="order:17;margin-bottom:12px">',
    NEW_REV + NEW_PRE1 + NEW_PRE2 + "  <!-- 复盘 + 纪律 -->\n"
    '  <div class="grid g-main" data-pro="rev" style="order:17;margin-bottom:12px">',
    tag="重排买点池/节点/仓位/风险/计划五块")

# ============================================================================
# 6. ⑥⑦ 合并成「题材主线」双视角 tab
#    原来两个 card 并排、展示同一批票的两个切面，等于同一份数据占两块版面。
#    合并办法：把两块的内容抽成两个 pane，装进一个新 card，用 tab 切换。
# ============================================================================
seg = cut('    <div class="card" id="sThemes">',
          '      <div id="roles"></div>\n    </div>', tag="截出题材两个 card")
# ⑥ 的内核只剩 themes 容器
pane_themes = '    <div class="th-pane" id="sThemes">\n      <div id="themes"></div>\n    </div>'
# ⑦ 的内核是图例 + roles 容器
i = seg.index('<div class="role-legend">')
j = seg.index('<div id="roles"></div>') + len('<div id="roles"></div>')
inner_roles = seg[i:j]
pane_roles = ('    <div class="th-pane" id="sRoles" hidden>\n'
              + "\n".join("      " + ln for ln in inner_roles.split("\n")) + "\n"
              + '    </div>')

HUB = (
    "  <!-- 题材主线：板块视角 / 角色视角，同一批票的两种看法，合并成一个板块 -->\n"
    '  <div class="card" id="sThemeHub" data-pro="rev" style="order:12;margin-bottom:12px">\n'
    '    <h2>题材主线 <span class="sub">（分组口径：<b id="rolesGroupSrc">题材归并</b> · 龙头大哥 / 板块中军 / 小弟 · 市值口径=流通市值）</span>\n'
    '      <span class="tt-mode" id="thTab">\n'
    '        <button data-t="theme" class="active" onclick="setThemeTab(\'theme\')">板块视角</button>\n'
    '        <button data-t="role" onclick="setThemeTab(\'role\')">角色视角</button>\n'
    '      </span>\n'
    '    </h2>\n'
    '    <div class="grp-head" style="margin:0 0 8px">题材只在这里出现一次'
    '<span class="gm">板块视角看数量与身位，角色视角看龙头 / 中军 / 小弟的分工</span></div>\n'
    + pane_themes + "\n" + pane_roles + "\n"
    '  </div>\n\n'
)
# ⑤ 现在独占一行（原 g-main 两列布局里空出一列不好看），并把题材 hub 排在它前面
rep('  <div class="grid g-main" id="sTianti" data-pro="rev" style="order:13;margin-bottom:12px">',
    HUB + '  <div class="grid" id="sTianti" data-pro="rev" style="order:13;margin-bottom:12px">',
    tag="题材双视角合并 + 天梯独占一行")
assert h.count('id="rolesGroupSrc"') == 1, f"rolesGroupSrc 出现 {h.count('id=\"rolesGroupSrc\"')} 次"
assert h.count('id="sThemes"') == 1 and h.count('id="sRoles"') == 1, "题材 pane id 不唯一"
assert h.count('id="themes"') == 1 and h.count('id="roles"') == 1, "题材容器 id 不唯一"

# ============================================================================
# 7. 编号清理：①~⑯ 是历史上一个个加模块累加出来的编号，本身没有语义，
#    重排之后编号会误导（"⑯"排在第 3 位）。只改 <h2> 标题里的，代码注释不动。
# ============================================================================
for old, new, tag in [
    ("<h2>① 3 秒决策速览</h2>",
     "<h2>今日定调 <span class=\"sub\">（3 秒看完：今天能不能做、最多做多少、做哪些）</span></h2>", "编号1"),
    ("<h2>② 情绪周期定位 ", "<h2>情绪周期定位 ", "编号2"),
    ("<h2>③ 市场全景</h2>", "<h2>市场全景</h2>", "编号3"),
    ("<h2>④ 今日重点清单 <span class=\"sub\">（身位龙 + 弱转强 + 主线核心，点击看K线）</span></h2>",
     "<h2>今日重点 <span class=\"sub\">（身位龙 + 弱转强 + 主线核心，点名字看K线）</span></h2>", "编号4"),
    ("<h2>⑤ 连板天梯 ", "<h2>连板天梯 ", "编号5"),
    ("<!-- ⑤ 连板天梯 + 主线题材 -->", "<!-- 连板天梯（题材已独立成「题材主线」板块） -->", "注释5"),
    ("<h2>⑬ 收盘复盘 ", "<h2>收盘复盘 ", "编号13"),
    ("<h2>⑭ 纪律卡 ", "<h2>纪律与一致性 ", "编号14"),
    ("<h2>⑮ 爆量涨停选股器 ", "<h2>爆量涨停选股器 ", "编号15"),
    ("<h2>⑯ 盘前作战卡 ", "<h2>盘前作战卡 ", "编号16"),
    ("<h2>⑰ 龙虎榜席位近期溢价 ", "<h2>龙虎榜席位近期溢价 ", "编号17"),
]:
    rep(old, new, tag=tag)

# 校验：<body> 到第一个 <script> 之间的正文标记里，不应再残留任何 ①~⑯ 编号
# （<style> 与 <script> 里的注释保留原编号，那是给维护者看的，不影响界面）
_body_start = h.index("<body>")
_body_end = h.index("<script", _body_start)
_body_html = h[_body_start:_body_end]
_circled = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰"
_left = [c for c in _circled if f"{c} " in _body_html]
assert not _left, f"正文仍残留编号：{_left}"

# ============================================================================
# 8. 资金参数全局化：现在 50000 与四档金额写死在 5 处，改本金要改 5 个地方
# ============================================================================
JS_ACCOUNT = r"""/* ===== PRO：账户参数全局单一来源 =====
   本金此前以字面量写死在展示层与作战卡共 5 处，改本金需要满文件搜索替换。
   现在全部改为由这一份 ACCOUNT 推导，定位与金额文案不留字面量；localStorage 持久化。 */
const ACCT_DEFAULT = { cap:150000, risk:2, stop:5 };
let ACCOUNT = Object.assign({}, ACCT_DEFAULT);
try{
  const s = localStorage.getItem("wb_pro_acct");
  if(s){ const o = JSON.parse(s); if(o && o.cap>0) ACCOUNT = Object.assign({}, ACCT_DEFAULT, o); }
}catch(_){}
const fmtMoney = v => "¥" + Math.round(v).toLocaleString("zh-CN");
function capMoneyTxt(pctFrom, pctTo){
  const a = ACCOUNT.cap * pctFrom/100, b = pctTo!=null ? ACCOUNT.cap*pctTo/100 : null;
  return b==null ? ("≤ " + fmtMoney(a)) : (fmtMoney(a) + " ~ " + fmtMoney(b));
}
function toggleAcct(){ const p = el("acctPanel"); if(p) p.classList.toggle("show"); }
function resetAcct(){ ACCOUNT = Object.assign({}, ACCT_DEFAULT); writeAcct(); }
function applyAcct(){
  const g = id => { const e = el(id); return e ? parseFloat(e.value) : NaN; };
  const cap = g("acctCap"), risk = g("acctRisk"), stop = g("acctStop");
  if(cap>0) ACCOUNT.cap = cap;
  if(risk>0) ACCOUNT.risk = risk;
  if(stop>0) ACCOUNT.stop = stop;
  writeAcct();
}
function writeAcct(){
  try{ localStorage.setItem("wb_pro_acct", JSON.stringify(ACCOUNT)); }catch(_){}
  paintAcct();
  // 金额相关的板块全部重算，保证「一处改、处处变」
  const pc = el("posCapital"); if(pc) pc.value = ACCOUNT.cap;
  const pr = el("posRisk");    if(pr) pr.value = ACCOUNT.risk;
  const ps = el("posStop");    if(ps) ps.value = ACCOUNT.stop;
  if(typeof calcPos === "function") calcPos();
  if(typeof renderPosMatrix === "function") renderPosMatrix();
  if(typeof renderBattle === "function") renderBattle();
}
function paintAcct(){
  const set = (id,v)=>{ const e = el(id); if(e) e.textContent = v; };
  set("acctLabel", Math.round(ACCOUNT.cap).toLocaleString("zh-CN"));
  const ac = el("acctCap"), ar = el("acctRisk"), as = el("acctStop");
  if(ac) ac.value = ACCOUNT.cap; if(ar) ar.value = ACCOUNT.risk; if(as) as.value = ACCOUNT.stop;
  const note = el("acctNote");
  if(note){
    const unit = ACCOUNT.cap/10000;
    note.innerHTML = `总资金 <b>${fmtMoney(ACCOUNT.cap)}</b>（${unit.toFixed(1)} 万）。`
      + `单笔风险 ${ACCOUNT.risk}% = 单笔最多亏 <b>${fmtMoney(ACCOUNT.cap*ACCOUNT.risk/100)}</b>；`
      + `止损 ${ACCOUNT.stop}% 时按规则可买 <b>${fmtMoney(ACCOUNT.cap*ACCOUNT.risk/100/(ACCOUNT.stop/100))}</b>`
      + `（占本金 ${fmt(ACCOUNT.cap*ACCOUNT.risk/100/(ACCOUNT.stop/100)/ACCOUNT.cap*100,1)}%）。`
      + `<br>改这里，仓位矩阵、风险计算器、作战卡的金额限制会一起变。`;
  }
}

/* ===== PRO：模式切换 / 题材双视角 / 折叠 / 搜索 / 复制 / 深色 ===== */
const PRO_MODE_KEY = "wb_pro_mode";
function setProMode(m){
  document.body.setAttribute("data-mode", m);
  try{ localStorage.setItem(PRO_MODE_KEY, m); }catch(_){}
  document.querySelectorAll("#modeSw button").forEach(b=>b.classList.toggle("active", b.dataset.m===m));
  const hint = el("modeHint");
  const nPre = document.querySelectorAll('[data-pro="pre"]').length;
  const nRev = document.querySelectorAll('[data-pro="rev"]').length;
  if(hint){
    hint.textContent = m==="pre"
      ? `盘前：${nPre} 个板块，按「定调 → 重点 → 作战卡 → 仓位风控 → 执行序」排好`
      : `复盘：${nRev} 个板块，按「周期 → 题材 → 天梯 → 买点池 → 选股器 → 复盘纪律」排好`;
  }
  // 切模式时把当前模式的第一个板块滚到顶部，省得手动找
  const first = document.querySelector(`[data-pro="${m}"]`);
  if(first && !first.classList.contains("grp-head")) first.scrollIntoView({block:"start"});
  buildNav(m);
}
function buildNav(m){
  const items = m==="pre"
    ? [["#sOverview","定调"],["#sFocus","重点"],["#sBattle","作战卡"],["#sPos","仓位风控"],["#sPlan","执行序"]]
    : [["#sCycle","周期全景"],["#sThemeHub","题材"],["#sTianti","天梯"],["#sBuyPool","买点池"],
       ["#sNodes","节点票"],["#sScreener","选股器"],["#sSeats","席位溢价"],
       ["#sReview","复盘"],["#sDiscipline","纪律"]];
  const html = items.map(([h,t])=>`<a href="${h}">${t}</a>`).join("");
  document.querySelectorAll(".quick-nav").forEach(n=>n.innerHTML = html);
  document.querySelectorAll(".bottom-nav").forEach(n=>{
    n.innerHTML = items.slice(0,5).map(([h,t])=>`<a href="${h}">${t}</a>`).join("");
  });
}
function setThemeTab(t){
  const a = el("sThemes"), b = el("sRoles");
  if(!a||!b) return;
  a.hidden = (t!=="theme"); b.hidden = (t!=="role");
  document.querySelectorAll("#thTab button").forEach(x=>x.classList.toggle("active", x.dataset.t===t));
  try{ localStorage.setItem("wb_pro_thtab", t); }catch(_){}
}
function toggleDisc(){
  const d = el("discMore"); if(!d) return;
  d.classList.toggle("show");
  const t = el("discToggle");
  if(t) t.textContent = d.classList.contains("show") ? "收起" : "展开全部纪律";
}
function toggleDark(){
  const on = !document.body.classList.contains("dark");
  document.body.classList.toggle("dark", on);
  try{ localStorage.setItem("wb_pro_dark", on ? "1" : "0"); }catch(_){}
  const b = el("darkBtn"); if(b) b.textContent = on ? "浅色" : "深色";
}
function proFind(){
  const q = (el("proQ").value||"").trim();
  const hit = el("proQHit");
  document.querySelectorAll(".pro-hit").forEach(e=>e.classList.remove("pro-hit"));
  if(!q){ if(hit) hit.textContent=""; return; }
  const cards = document.querySelectorAll(".pro-body .card, .pro-body .grid");
  const found = [];
  cards.forEach(c=>{ if(c.offsetParent !== null && (c.textContent||"").includes(q)) found.push(c); });
  if(!found.length){ if(hit) hit.textContent = "没找到"; return; }
  found[0].scrollIntoView({block:"start"});
  found.slice(0,6).forEach(c=>c.classList.add("pro-hit"));
  if(hit) hit.textContent = `命中 ${found.length} 个板块，已跳到第 1 个`;
  setTimeout(()=>document.querySelectorAll(".pro-hit").forEach(e=>e.classList.remove("pro-hit")), 4000);
}
function copyDaily(){
  const m = DATA.market||{}, cy = DATA.cycle||{}, nd = DATA.next_day||"次日";
  const top = (DATA.tianti||[]).slice().sort((a,b)=>(b.lbc||0)-(a.lbc||0))[0]||{};
  const k = stageKeyForMatrix(String(cy.stage||""));
  const cap = (POS_MATRIX[k]||POS_MATRIX["分歧期"]);
  const L = [];
  L.push(`【${DATA.date||""} 收盘 → ${nd} 盘前】`);
  L.push(`周期 ${cy.stage||"—"}｜涨停 ${m.limit_up??"—"} 跌停 ${m.limit_down??"—"} 晋级率 ${m.promote_rate!=null?fmt(m.promote_rate*100,0)+"%":"—"}`);
  L.push(`最高板 ${top.name||"—"}（${top.lbc||0}板）｜仓位上限 身位龙${cap.leader}% 弱转强${cap.ws}%（本金 ${Math.round(ACCOUNT.cap/10000)}万）`);
  const ns = (DATA.nodes||[]).slice(0,4).map(n=>n.name).filter(Boolean);
  L.push(`弱转强节点：${ns.length?ns.join("、"):"无"}`);
  if(window.WB_VOLPOOL && window.WB_VOLPOOL.pool){
    const zt = {}; (DATA.tianti||[]).forEach(t=>zt[String(t.code)]=1);
    const hit = window.WB_VOLPOOL.pool.filter(x=>zt[String(x.code)]).slice(0,5).map(x=>x.name);
    L.push(`放高量池交叉命中：${hit.length?hit.join("、"):"无"}`);
  }
  L.push(`纪律：单笔亏≥${ACCOUNT.risk}%（${fmtMoney(ACCOUNT.cap*ACCOUNT.risk/100)}）当日停手；不补仓不换股`);
  const text = L.join("\n");
  const done = ()=>{ const b = document.querySelector('.pro-btn[onclick="copyDaily()"]');
    if(b){ const o=b.textContent; b.textContent="✓ 已复制"; setTimeout(()=>b.textContent=o,1500); } };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(()=>fallbackCopy(text,done));
  } else fallbackCopy(text,done);
}
function proInit(){
  // 模式
  let m = "pre";
  try{ const s = localStorage.getItem(PRO_MODE_KEY); if(s==="pre"||s==="rev") m = s; }catch(_){}
  setProMode(m);
  // 深色
  try{ if(localStorage.getItem("wb_pro_dark")==="1"){ document.body.classList.add("dark");
    const b=el("darkBtn"); if(b) b.textContent="浅色"; } }catch(_){}
  // 题材视角
  let tt = "theme";
  try{ const s = localStorage.getItem("wb_pro_thtab"); if(s==="role") tt = "role"; }catch(_){}
  setThemeTab(tt);
  // 账户
  paintAcct();
  const pc = el("posCapital"); if(pc) pc.value = ACCOUNT.cap;
  const pr = el("posRisk"); if(pr) pr.value = ACCOUNT.risk;
  const ps = el("posStop"); if(ps) ps.value = ACCOUNT.stop;
}

/* ---------- 主渲染 ---------- */"""

rep("/* ---------- 主渲染 ---------- */", JS_ACCOUNT, tag="注入 ACCOUNT 与 PRO 逻辑")

# 接进 renderAll：末位追加 proInit()
rep("  renderBattle();\n  calcPos();\n  renderRuleBar();\n  fillInlineMinutes();\n}",
    "  renderBattle();\n  calcPos();\n  renderRuleBar();\n  fillInlineMinutes();\n"
    "  proInit();   /* PRO：模式/账户/题材视角/深色，必须在最后，依赖前面已渲染的节点 */\n}",
    tag="renderAll 接入 proInit")

# 作战卡四档金额改为按 ACCOUNT 换算
rep('cap="0 ~ 10%"; capMoney="0 ~ 5000 元"; }',
    'cap="0 ~ 10%"; capMoney=capMoneyTxt(0,10); }', tag="金额档1")
rep('cap="≤ 20%"; capMoney="≤ 10000 元"; }',
    'cap="≤ 20%"; capMoney=capMoneyTxt(20); }', tag="金额档2")
rep('cap="≤ 50%"; capMoney="≤ 25000 元"; }',
    'cap="≤ 50%"; capMoney=capMoneyTxt(50); }', tag="金额档3")
rep('cap="≤ 30%"; capMoney="≤ 15000 元"; }',
    'cap="≤ 30%"; capMoney=capMoneyTxt(30); }', tag="金额档4")
rep('（5W本金 → ${capMoney}）</span>', '（本金 ${Math.round(ACCOUNT.cap/10000)} 万 → ${capMoney}）</span>', tag="本金文案1")
rep('`<b>${cap}</b>（5W本金 → ${capMoney}），单票不超过 10%，先小仓试错，确认转强再加。`',
    '`<b>${cap}</b>（本金 ${Math.round(ACCOUNT.cap/10000)} 万 → ${capMoney}），单票不超过 10%（${fmtMoney(ACCOUNT.cap*0.10)}），先小仓试错，确认转强再加。`',
    tag="本金文案2")
rep('单票不超过 10%（5000 元）', '单票不超过 10%（${fmtMoney(ACCOUNT.cap*0.10)}）', tag="本金文案3")
rep('<span class="muted">单票≤50%，5W本金建议单票≤25%更稳</span>',
    '<span class="muted">单票≤50%；本金 ${Math.round(ACCOUNT.cap/10000)} 万建议单票≤25%（${fmtMoney(ACCOUNT.cap*0.25)}）更稳</span>',
    tag="本金文案4")
rep('对5W本金风险过大', '对 ${Math.round(ACCOUNT.cap/10000)} 万本金风险过大', tag="本金文案5")

# ============================================================================
# 9. 去重：⑪ 里重复的跌停池（③ 已有完整版）、⑫ 里重复的节点票列表
# ============================================================================
rep("""  const lds = DATA.limit_down_stocks||[];
  if(lds.length){
    html += `<div class="risk-row" style="border-left-color:var(--red)"><div class="risk-main"><b>跌停池 ${lds.length} 只</b><span class="tag tag-sig" style="background:var(--redbg);color:var(--red)">亏钱效应</span></div><div class="risk-meta">${lds.slice(0,10).map(s=>`${s.name||""} ${s.code||""}`).join(" · ")}</div></div>`;
  }
""", "  /* PRO：跌停池已在「市场全景」完整展示，这里不再重复列一遍 */\n",
    tag="去重跌停池")

rep("""  el("planList").innerHTML = ns.slice(0,8).map(n=>`
    <div class="plan-item">
      <div><b>${n.name||"—"}</b> <span class="muted">${n.code||""}</span></div>
      <div class="plan-meta">${n.board_label||(n.lbc? n.lbc+"板":"首板")} · ${n.signal||"弱转强"}</div>
    </div>`).join("") || '<div class="empty">暂无弱转强节点票，明日以主线核心/最高板观察为主</div>';
""", "  /* PRO：节点票列表已由「节点票 / 弱转强触发器」完整展示，这里只留执行序 */\n",
    tag="去重节点票列表")

# 纪律卡：顶部纪律条已有前 4 条常驻，正文默认折叠，避免同一份数据占两块首屏
rep('  el("discipline").innerHTML = d.map(x=>`<li>${x}</li>`).join("");',
    """  // PRO：顶部纪律条常驻前 4 条，这里把全文折叠起来，首屏只留一致性评分
  const head = d.slice(0,4), more = d.slice(4);
  el("discipline").innerHTML = head.map(x=>`<li>${x}</li>`).join("")
    + (more.length ? `<div class="disc-more" id="discMore">${more.map(x=>`<li>${x}</li>`).join("")}</div>`
       + `<span class="disc-toggle" id="discToggle" onclick="toggleDisc()">展开全部 ${d.length} 条纪律</span>` : "");""",
    tag="纪律折叠")

# ============================================================================
# 10. 做 / 不做 双栏：插在今日定调卡内（结论与数据分离，盘前只扫结论）
# ============================================================================
rep('    <div class="scan-todo" id="scanTodo"></div>\n  </div>',
    '    <div class="scan-todo" id="scanTodo"></div>\n'
    '    <div class="dodont" id="doDont"></div>\n  </div>',
    tag="做/不做容器")

rep("""  el("scanTodo").innerHTML = (cyc.todo||[]).map(t=>`<span class="pill">${t}</span>`).join("");
}""",
    """  el("scanTodo").innerHTML = (cyc.todo||[]).map(t=>`<span class="pill">${t}</span>`).join("");
  renderDoDont(cyc, m);
}
/* PRO 新增：把散在 ⑯ 避雷项、⑪ 风险扫描、⑧ 买点池里的结论收敛成两栏。
   盘前先看这两栏就够，细节再往下翻。
   左栏做成可打勾的执行清单：痛点之一是盘中忘记既定手法，
   只把清单摆出来没用，要能一条条勾掉，且刷新、重渲染都不丢。 */
const DONE_KEY = "wb_pro_done";
function doneSig(t){                       // 32 位散列，用文本当键，条目顺序变了也不串号
  let x = 0; const s = String(t);
  for(let i=0;i<s.length;i++){ x = (x*31 + s.charCodeAt(i))|0; }
  return (x>>>0).toString(36);
}
function loadDone(){
  try{
    const o = JSON.parse(localStorage.getItem(DONE_KEY)||"{}");
    return (o && typeof o==="object" && !Array.isArray(o)) ? o : {};
  }catch(_){ return {}; }
}
function saveDone(o){ try{ localStorage.setItem(DONE_KEY, JSON.stringify(o)); }catch(_){} }
function doneBucket(){
  const d = String((DATA||{}).date||"nodate");
  const all = loadDone();
  return {all:all, d:d, b:(all[d] || (all[d]={}))};
}
function toggleDone(li){
  const sg = li.getAttribute("data-sig"); if(!sg) return;
  const st = doneBucket();
  if(st.b[sg]) delete st.b[sg]; else st.b[sg] = 1;
  const ks = Object.keys(st.all).sort();
  if(ks.length > 5) ks.slice(0, ks.length-5).forEach(k=>delete st.all[k]);  // 只留最近 5 天
  saveDone(st.all);
  li.classList.toggle("done");
  paintDoneCount();
}
function paintDoneCount(){
  const box = el("doDont"); if(!box) return;
  const items = box.querySelectorAll("[data-sig]");
  const n = box.querySelectorAll("[data-sig].done").length;
  const c = el("doCount");
  if(c) c.textContent = n ? ("已勾 " + n + " / " + items.length + (n===items.length ? " ✓" : "")) : "";
}
function resetDone(){
  const st = doneBucket(); st.all[st.d] = {}; saveDone(st.all);
  const box = el("doDont"); if(!box) return;
  box.querySelectorAll("[data-sig].done").forEach(x=>x.classList.remove("done"));
  paintDoneCount();
}
function renderDoDont(cyc, m){
  const box = el("doDont"); if(!box) return;
  const doL = [], dontL = [];
  const k = stageKeyForMatrix(String(cyc.stage||""));
  const cap = (POS_MATRIX[k]||POS_MATRIX["分歧期"]);
  const top = (DATA.tianti||[]).slice().sort((a,b)=>(b.lbc||0)-(a.lbc||0))[0]||{};
  // 做
  if(cap.leader>0) doL.push(`身位龙 ${top.name||"未定"}（${top.lbc||0}板）：仓位上限 ${cap.leader}%`);
  if(cap.ws>0)     doL.push(`弱转强节点：仓位上限 ${cap.ws}%，只在 9:42~10:10 分歧回封段动手`);
  const ns = (DATA.nodes||[]).slice(0,3).map(n=>n.name).filter(Boolean);
  if(ns.length)    doL.push(`盯这三只的承接：${ns.join("、")}`);
  if(window.WB_VOLPOOL && window.WB_VOLPOOL.pool && window.WB_VOLPOOL.pool.length){
    const zt = {}; (DATA.tianti||[]).forEach(t=>zt[String(t.code)]=1);
    const hit = window.WB_VOLPOOL.pool.filter(x=>zt[String(x.code)]).slice(0,5).map(x=>x.name);
    if(hit.length) doL.push(`放高量池交叉命中（优先看）：${hit.join("、")}`);
  }
  // 不做
  if(cap.leader===0) dontL.push(`当前${cyc.stage||"周期"}：矩阵给的仓位是 0，只观察不出手`);
  dontL.push(`最高板 ${top.lbc||0} 板以上高位票一律不碰`);
  const risk = (DATA.tianti||[]).filter(r=>(r.open_times||0)>=2).slice(0,4).map(r=>r.name).filter(Boolean);
  if(risk.length) dontL.push(`开板≥2 次的弱封板不接力：${risk.join("、")}`);
  const lds = DATA.limit_down_stocks||[];
  if(lds.length>=2) dontL.push(`跌停 ${lds.length} 只，人气股跌停≥2 只时当日只卖不买`);
  dontL.push(`单笔亏≥${ACCOUNT.risk}%（${fmtMoney(ACCOUNT.cap*ACCOUNT.risk/100)}）当日停手，不补仓不摊平`);

  const bucket = doneBucket().b;
  const doList = doL.length ? doL : ["矩阵给的仓位为 0，今天不做"];
  const lis = doList.map(function(x){
    const sg = doneSig(x), on = bucket[sg] ? " done" : "";
    return `<li class="do-li${on}" data-sig="${sg}" onclick="toggleDone(this)">`
         + `<span class="do-box"></span><span class="do-t">${x}</span></li>`;
  }).join("");

  // 矩阵缺行时必须说清楚正在拿哪个阶段兜底，不许静默替换
  let fb = "";
  if(!k){
    fb = `<div class="dd-fallback">⚠ 「${cyc.stage||"当前阶段"}」在仓位矩阵里没有对应行，`
       + `本栏的仓位数字是按「分歧期」兜底的，请对照你自己的周期口径确认后再用。</div>`;
  }

  const doneN = doList.filter(x=>bucket[doneSig(x)]).length;
  box.innerHTML =
      `<div class="dd dd-do"><div class="dd-h-row"><div class="dd-h">✓ 今天做这些</div>`
    + `<div class="dd-tool"><span class="dd-count" id="doCount">`
    + (doneN ? ("已勾 " + doneN + " / " + doList.length + (doneN===doList.length ? " ✓" : "")) : "")
    + `</span><button class="dd-reset" onclick="resetDone()">清空勾选</button></div></div>`
    + `<ul style="margin:0;padding-left:0">${lis}</ul>${fb}</div>`
    + `<div class="dd dd-dont"><div class="dd-h">✗ 今天不做这些</div>`
    + `<ul style="margin:0;padding-left:0">${dontL.map(x=>`<li>${x}</li>`).join("")}</ul></div>`;
}""",
    tag="做/不做渲染")

# finish
h = h.replace("<div class=\"muted\" style=\"font-size:11px;text-align:center;margin-top:14px;color:#9aa6b2\">",
              "  </div><!-- /pro-body -->\n\n"
              "  <div class=\"muted\" style=\"font-size:11px;text-align:center;margin-top:14px;color:#9aa6b2\">",
              1)
h = h.replace("V2 工作台 · 数据格式与 V1 完全兼容（WB_DATA / WB_DATES_INLINE / hist 懒加载）· 红涨绿跌 · 手机可用",
              "PRO 工作台 · 板块按「盘前 / 复盘」分组，重复内容已合并 · 账户参数全局生效 · 数据格式与 V2 完全兼容", 1)
h = h.replace('window.WB_BUILD="', 'window.WB_PRO=1;\nwindow.WB_BUILD="', 1) if 'window.WB_BUILD="' in h else h

OUT.write_text(h, encoding="utf-8")
print("\n".join(LOG))
print(f"\nOK -> {OUT}  {OUT.stat().st_size/1024:.1f} KB（源 {SRC.stat().st_size/1024:.1f} KB）")
print(f"data-pro 数：pre={h.count('data-pro=\"pre\"')} rev={h.count('data-pro=\"rev\"')}")
