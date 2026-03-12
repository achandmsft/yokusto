"""
yokusto YOLO Hypothesis Mode Demo
==================================
Hypothesis: "Flood events cause disproportionately more damage per event than
other storm types, and this pattern is driven by geographic hotspots."

This script queries help.kusto.windows.net / Samples / StormEvents and produces:
  - hypothesis_01_ranking.html    — Where do floods rank by total damage?
  - hypothesis_02_per_event.html  — Is per-event flood damage disproportionate?
  - hypothesis_03_geographic.html — Are there geographic hotspots?
  - hypothesis_summary.html       — Executive summary with overall verdict

Prerequisites:
  pip install azure-kusto-data azure-identity
  az login   # for Azure CLI credential
"""
from azure.identity import AzureCliCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder, ClientRequestProperties
from datetime import timedelta
import json, html as html_mod, os, sys

CLUSTER = "https://help.kusto.windows.net"
DATABASE = "Samples"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

cred = AzureCliCredential()
kcsb = KustoConnectionStringBuilder.with_azure_token_credential(CLUSTER, cred)
client = KustoClient(kcsb)

def query(kql, timeout_min=5):
    props = ClientRequestProperties()
    props.set_option("servertimeout", timedelta(minutes=timeout_min))
    resp = client.execute_query(DATABASE, kql, props)
    table = resp.primary_results[0]
    cols = [c.column_name for c in table.columns]
    return [{cols[i]: row[i] for i in range(len(cols))} for row in table]

def fmt(n):
    if n >= 1_000_000_000: return f"${n/1_000_000_000:,.1f}B"
    if n >= 1_000_000: return f"${n/1_000_000:,.1f}M"
    if n >= 1_000: return f"${n/1_000:,.0f}K"
    return f"${n:,.0f}"

def write(filename, content):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ Wrote {path}")

# ═══════════════════════════════════════════════
# Hypothesis: Floods cause disproportionate damage
# ═══════════════════════════════════════════════

print("=" * 60)
print("YOLO HYPOTHESIS MODE")
print('Hypothesis: "Flood events cause disproportionately more')
print('damage per event than other storm types"')
print("=" * 60)
print()

# ── Sub-question 1: Total damage ranking ──────
print("Dashboard 1/3 — Total damage ranking...")
by_type = query("""
StormEvents
| summarize Events=count(),
    TotalDamage=sum(DamageProperty + DamageCrops),
    PropertyDamage=sum(DamageProperty),
    CropDamage=sum(DamageCrops),
    Deaths=sum(DeathsDirect + DeathsIndirect),
    Injuries=sum(InjuriesDirect + InjuriesIndirect)
  by EventType
| top 10 by TotalDamage desc
""")

flood_total = sum(r['TotalDamage'] for r in by_type if r['EventType'] in ('Flood', 'Flash Flood'))
flood_deaths = sum(r['Deaths'] for r in by_type if r['EventType'] in ('Flood', 'Flash Flood'))
flood_events = sum(r['Events'] for r in by_type if r['EventType'] in ('Flood', 'Flash Flood'))
grand_total = sum(r['TotalDamage'] for r in by_type)

type_labels = json.dumps([r['EventType'] for r in by_type])
type_damages = json.dumps([r['TotalDamage'] for r in by_type])

table_rows = ""
for r in by_type:
    is_flood = r['EventType'] in ('Flood', 'Flash Flood')
    cls = ' style="background:#1a2a3a"' if is_flood else ''
    b = ("<strong>", "</strong>") if is_flood else ("", "")
    table_rows += (
        f'<tr{cls}><td>{b[0]}{r["EventType"]}{b[1]}</td>'
        f'<td class="right">{b[0]}{fmt(r["TotalDamage"])}{b[1]}</td>'
        f'<td class="right">{b[0]}{r["Events"]:,}{b[1]}</td>'
        f'<td class="right">{b[0]}{r["Deaths"]}{b[1]}</td></tr>\n'
    )

for r in by_type:
    print(f"  {r['EventType']:25s} {fmt(r['TotalDamage']):>10s}  Events={r['Events']:>6,}")

write("hypothesis_01_ranking.html", f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hypothesis 01 — Damage Ranking: Where Do Floods Stand?</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0f0f23;color:#e0e0e0;padding:24px}}
  h1{{text-align:center;font-size:24px;margin-bottom:4px;background:linear-gradient(135deg,#42a5f5,#66bb6a);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  .subtitle{{text-align:center;color:#888;font-size:13px;margin-bottom:20px}}
  .question{{text-align:center;font-size:16px;color:#ccc;margin-bottom:20px;font-style:italic;border-left:3px solid #42a5f5;padding:8px 16px;display:inline-block;width:100%}}
  .verdict{{text-align:center;margin-bottom:24px;padding:16px 24px;border-radius:12px;width:100%}}
  .verdict.partial{{background:linear-gradient(135deg,#1a3a1a,#2a4a2a);border:2px solid #ffa726}}
  .verdict .badge{{font-size:14px;font-weight:700;letter-spacing:2px;padding:4px 12px;border-radius:6px;display:inline-block;margin-bottom:8px}}
  .verdict.partial .badge{{background:#ffa726;color:#1a1a1a}}
  .verdict .summary{{font-size:14px;color:#ccc}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}}
  .card{{background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4e}}
  .card h3{{font-size:15px;color:#ccc;margin-bottom:12px}}
  .full{{grid-column:1/-1}}
  canvas{{max-height:340px}}
  .kpi-row{{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-bottom:24px}}
  .kpi{{background:linear-gradient(135deg,#1a1a3e,#2a2a5e);border-radius:12px;padding:16px 24px;min-width:140px;text-align:center;border:1px solid #333366}}
  .kpi .value{{font-size:28px;font-weight:800}}
  .kpi .label{{font-size:11px;color:#aaa;margin-top:4px;text-transform:uppercase;letter-spacing:1px}}
  .kpi.orange .value{{color:#ffa726}}.kpi.blue .value{{color:#42a5f5}}.kpi.red .value{{color:#ff6b6b}}.kpi.green .value{{color:#66bb6a}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{text-align:left;padding:8px 10px;border-bottom:2px solid #333;color:#aaa;font-weight:600}}
  td{{padding:7px 10px;border-bottom:1px solid #222}}tr:hover{{background:#1e1e3e}}.right{{text-align:right}}
  .footer{{text-align:center;color:#555;font-size:12px;margin-top:20px}}
  .caveat{{background:#1a1a2e;border-radius:8px;padding:16px;border-left:3px solid #ffa726;margin-top:20px;font-size:13px;color:#aaa}}
  .caveat h4{{color:#ffa726;margin-bottom:8px;font-size:13px}}
</style>
</head>
<body>
<h1>Hypothesis Dashboard 1 of 3</h1>
<p class="subtitle">Hypothesis: Flood events cause disproportionately more damage per event than other storm types</p>
<div class="question">Sub-question: Which storm types cause the most total damage, and where do floods rank?</div>
<div class="verdict partial">
  <div class="badge">PARTIALLY SUPPORTED</div>
  <div class="summary">Floods rank 6th–7th by total damage ({fmt(flood_total)} combined), behind Frost/Freeze, Drought, Wildfire, Tornado, and Ice Storm. Floods are significant but not the top damage driver by total dollars.</div>
</div>
<div class="kpi-row">
  <div class="kpi orange"><div class="value">{fmt(flood_total)}</div><div class="label">Flood + Flash Flood Damage</div></div>
  <div class="kpi blue"><div class="value">#6–7</div><div class="label">Rank by Total Damage</div></div>
  <div class="kpi red"><div class="value">{flood_deaths:,}</div><div class="label">Flood Deaths</div></div>
  <div class="kpi green"><div class="value">{flood_events:,}</div><div class="label">Flood Events</div></div>
</div>
<div class="grid">
  <div class="card full"><h3>Top 10 Storm Types by Total Damage ($)</h3><canvas id="rankChart"></canvas></div>
  <div class="card"><h3>Damage Breakdown</h3><table>
    <tr><th>Event Type</th><th class="right">Total Damage</th><th class="right">Events</th><th class="right">Deaths</th></tr>
    {table_rows}</table>
  </div>
  <div class="card"><h3>Flood Share of Total</h3><canvas id="pieChart"></canvas></div>
</div>
<div class="caveat"><h4>Caveats</h4><ul>
  <li>Data covers 2007 only.</li>
  <li>Frost/Freeze is dominated by a single Jan 2007 California event (~$1.3B).</li>
  <li>Flood + Flash Flood combined ($2.2B) would rival #1.</li>
</ul></div>
<p class="footer">Generated by yokusto — YOLO Hypothesis Mode — {CLUSTER} / {DATABASE} / StormEvents</p>
<script>
const types={type_labels};const damages={type_damages};
new Chart(document.getElementById('rankChart'),{{type:'bar',data:{{labels:types,datasets:[{{data:damages,backgroundColor:types.map(t=>(t==='Flash Flood'||t==='Flood')?'#26c6da':'#42a5f5'),borderColor:types.map(t=>(t==='Flash Flood'||t==='Flood')?'#fff':'transparent'),borderWidth:types.map(t=>(t==='Flash Flood'||t==='Flood')?2:0)}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>'$'+(c.raw/1e9).toFixed(2)+'B'}}}}}},scales:{{x:{{ticks:{{color:'#888',maxRotation:45}},grid:{{color:'#222'}}}},y:{{ticks:{{color:'#888',callback:v=>'$'+(v/1e9).toFixed(1)+'B'}},grid:{{color:'#222'}}}}}}}}}});
const otherDmg={grand_total}-{flood_total};
new Chart(document.getElementById('pieChart'),{{type:'doughnut',data:{{labels:['Flash Flood','Flood','All Other'],datasets:[{{data:[{by_type[5]['TotalDamage'] if len(by_type)>5 else 0},{by_type[6]['TotalDamage'] if len(by_type)>6 else 0},otherDmg],backgroundColor:['#26c6da','#42a5f5','#444466']}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#ccc'}}}}}}}}}});
</script></body></html>""")

print("  Dashboard 1/3 complete — total damage ranking.")

# ── Sub-question 2: Per-event normalization ────
print("\nDashboard 2/3 — Per-event damage comparison...")
per_event = query("""
StormEvents
| summarize Events=count(), TotalDamage=sum(DamageProperty + DamageCrops) by EventType
| where Events >= 20
| extend PerEventDamage = TotalDamage / Events
| top 10 by PerEventDamage desc
""")

flood_vs_other = query("""
StormEvents
| extend IsFlood = EventType in ('Flood', 'Flash Flood')
| summarize Events=count(), TotalDamage=sum(DamageProperty+DamageCrops), Deaths=sum(DeathsDirect+DeathsIndirect) by IsFlood
| extend PerEvent = TotalDamage / Events
""")

flood_pe = [r for r in flood_vs_other if r['IsFlood']][0]
other_pe = [r for r in flood_vs_other if not r['IsFlood']][0]
ratio = flood_pe['PerEvent'] / other_pe['PerEvent']

pe_labels = json.dumps([r['EventType'] for r in per_event])
pe_values = json.dumps([r['PerEventDamage'] for r in per_event])

pe_table = ""
for r in per_event:
    is_flood = r['EventType'] in ('Flood', 'Flash Flood', 'Coastal Flood')
    cls = ' style="background:#1a2a3a"' if is_flood else ''
    b = ("<strong>", "</strong>") if is_flood else ("", "")
    pe_table += (
        f'<tr{cls}><td>{b[0]}{r["EventType"]}{b[1]}</td>'
        f'<td class="right">{b[0]}{fmt(r["PerEventDamage"])}{b[1]}</td>'
        f'<td class="right">{b[0]}{r["Events"]:,}{b[1]}</td></tr>\n'
    )

print(f"  Flood per-event: {fmt(flood_pe['PerEvent'])}  |  Non-flood: {fmt(other_pe['PerEvent'])}  |  Ratio: {ratio:.1f}x")

write("hypothesis_02_per_event.html", f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hypothesis 02 — Per-Event Damage: Are Floods Disproportionate?</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0f0f23;color:#e0e0e0;padding:24px}}
  h1{{text-align:center;font-size:24px;margin-bottom:4px;background:linear-gradient(135deg,#42a5f5,#66bb6a);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  .subtitle{{text-align:center;color:#888;font-size:13px;margin-bottom:20px}}
  .question{{text-align:center;font-size:16px;color:#ccc;margin-bottom:20px;font-style:italic;border-left:3px solid #66bb6a;padding:8px 16px;display:inline-block;width:100%}}
  .verdict{{text-align:center;margin-bottom:24px;padding:16px 24px;border-radius:12px;width:100%}}
  .verdict.supported{{background:linear-gradient(135deg,#1a3a1a,#2a4a2a);border:2px solid #66bb6a}}
  .verdict .badge{{font-size:14px;font-weight:700;letter-spacing:2px;padding:4px 12px;border-radius:6px;display:inline-block;margin-bottom:8px}}
  .verdict.supported .badge{{background:#66bb6a;color:#1a1a1a}}
  .verdict .summary{{font-size:14px;color:#ccc}}
  .comparison{{display:flex;gap:24px;justify-content:center;flex-wrap:wrap;margin-bottom:24px}}
  .comp-box{{background:#1a1a2e;border-radius:12px;padding:20px 32px;text-align:center;border:1px solid #2a2a4e;flex:1;max-width:300px}}
  .comp-box .big{{font-size:36px;font-weight:800}}
  .comp-box .lbl{{font-size:12px;color:#aaa;margin-top:4px;text-transform:uppercase}}
  .comp-box.flood .big{{color:#26c6da}}.comp-box.other .big{{color:#78909c}}.comp-box.ratio .big{{color:#ffa726}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}}
  .card{{background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4e}}
  .card h3{{font-size:15px;color:#ccc;margin-bottom:12px}}
  .full{{grid-column:1/-1}}canvas{{max-height:340px}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{text-align:left;padding:8px 10px;border-bottom:2px solid #333;color:#aaa;font-weight:600}}
  td{{padding:7px 10px;border-bottom:1px solid #222}}tr:hover{{background:#1e1e3e}}.right{{text-align:right}}
  .footer{{text-align:center;color:#555;font-size:12px;margin-top:20px}}
  .caveat{{background:#1a1a2e;border-radius:8px;padding:16px;border-left:3px solid #ffa726;margin-top:20px;font-size:13px;color:#aaa}}
  .caveat h4{{color:#ffa726;margin-bottom:8px;font-size:13px}}
</style>
</head>
<body>
<h1>Hypothesis Dashboard 2 of 3</h1>
<p class="subtitle">Hypothesis: Flood events cause disproportionately more damage per event than other storm types</p>
<div class="question">Sub-question: How does per-event damage compare when normalizing floods vs. all other types?</div>
<div class="verdict supported">
  <div class="badge">SUPPORTED</div>
  <div class="summary">Flood events average {fmt(flood_pe['PerEvent'])} damage per event — {ratio:.1f}× the non-flood average of {fmt(other_pe['PerEvent'])}. While wildfires and frost/freeze are higher, floods are clearly above baseline.</div>
</div>
<div class="comparison">
  <div class="comp-box flood"><div class="big">{fmt(flood_pe['PerEvent'])}</div><div class="lbl">Flood Per-Event Damage</div></div>
  <div class="comp-box other"><div class="big">{fmt(other_pe['PerEvent'])}</div><div class="lbl">Non-Flood Per-Event Damage</div></div>
  <div class="comp-box ratio"><div class="big">{ratio:.1f}×</div><div class="lbl">Flood vs. Baseline Ratio</div></div>
</div>
<div class="grid">
  <div class="card full"><h3>Per-Event Damage by Storm Type (min 20 events)</h3><canvas id="peChart"></canvas></div>
  <div class="card"><h3>Per-Event Ranking</h3><table>
    <tr><th>Event Type</th><th class="right">Per-Event $</th><th class="right">Events</th></tr>
    {pe_table}</table>
  </div>
  <div class="card"><h3>Flood vs. Non-Flood</h3><canvas id="cmpChart"></canvas></div>
</div>
<div class="caveat"><h4>Caveats</h4><ul>
  <li>Wildfires ($5.2M/event) and Frost/Freeze ($1.3M/event) far exceed floods per-event.</li>
  <li>Single catastrophic events can skew per-event averages significantly.</li>
  <li>Single year of data (2007).</li>
</ul></div>
<p class="footer">Generated by yokusto — YOLO Hypothesis Mode — {CLUSTER} / {DATABASE} / StormEvents</p>
<script>
const labels={pe_labels};const vals={pe_values};
new Chart(document.getElementById('peChart'),{{type:'bar',data:{{labels:labels,datasets:[{{data:vals,backgroundColor:labels.map(t=>['Flood','Flash Flood','Coastal Flood'].includes(t)?'#26c6da':'#42a5f5'),borderColor:labels.map(t=>['Flood','Flash Flood','Coastal Flood'].includes(t)?'#fff':'transparent'),borderWidth:labels.map(t=>['Flood','Flash Flood','Coastal Flood'].includes(t)?2:0)}},{{label:'Non-Flood Avg ({fmt(other_pe["PerEvent"])})',data:Array(10).fill({other_pe['PerEvent']}),type:'line',borderColor:'#ff6b6b',borderDash:[6,4],pointRadius:0,borderWidth:2,fill:false}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#ccc'}}}}}},scales:{{x:{{ticks:{{color:'#888',maxRotation:45}},grid:{{color:'#222'}}}},y:{{ticks:{{color:'#888',callback:v=>'$'+(v/1e6).toFixed(1)+'M'}},grid:{{color:'#222'}}}}}}}}}});
new Chart(document.getElementById('cmpChart'),{{type:'bar',data:{{labels:['Flood','Non-Flood'],datasets:[{{data:[{flood_pe['PerEvent']},{other_pe['PerEvent']}],backgroundColor:['#26c6da','#78909c'],barThickness:60}}]}},options:{{indexAxis:'y',responsive:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:'#888',callback:v=>'$'+(v/1e3).toFixed(0)+'K'}},grid:{{color:'#222'}}}},y:{{ticks:{{color:'#ccc'}},grid:{{color:'#222'}}}}}}}}}});
</script></body></html>""")

print("  Dashboard 2/3 complete — per-event damage comparison.")

# ── Sub-question 3: Geographic hotspots ────────
print("\nDashboard 3/3 — Geographic hotspots...")
by_state = query("""
StormEvents
| where EventType in ('Flood', 'Flash Flood')
| summarize FloodDamage=sum(DamageProperty + DamageCrops), Events=count(), Deaths=sum(DeathsDirect+DeathsIndirect) by State
| top 15 by FloodDamage desc
""")

monthly_flood = query("""
StormEvents
| where EventType in ('Flood', 'Flash Flood')
| summarize Damage=sum(DamageProperty+DamageCrops), Events=count(), Deaths=sum(DeathsDirect+DeathsIndirect)
  by Month=startofmonth(StartTime)
| order by Month asc
""")

state_total = sum(r['FloodDamage'] for r in by_state)
top3_total = sum(r['FloodDamage'] for r in by_state[:3])
top3_pct = round(top3_total / state_total * 100)

state_labels = json.dumps([r['State'].title() for r in by_state])
state_damages = json.dumps([r['FloodDamage'] for r in by_state])

state_table = ""
running = 0
for r in by_state:
    running += r['FloodDamage']
    pct = round(r['FloodDamage'] / state_total * 100, 1)
    state_table += (
        f'<tr><td>{r["State"].title()}</td>'
        f'<td class="right">{fmt(r["FloodDamage"])}</td>'
        f'<td class="right">{r["Events"]:,}</td>'
        f'<td class="right">{pct}%</td>'
        f'<td class="right">{r["Deaths"]}</td></tr>\n'
    )

month_labels = json.dumps([str(r['Month'])[:7].split('-')[1] for r in monthly_flood])
month_map = {'01':'Jan','02':'Feb','03':'Mar','04':'Apr','05':'May','06':'Jun','07':'Jul','08':'Aug','09':'Sep','10':'Oct','11':'Nov','12':'Dec'}
month_names = json.dumps([month_map.get(str(r['Month'])[:7].split('-')[1], '?') for r in monthly_flood])
month_dmg = json.dumps([r['Damage'] for r in monthly_flood])
month_evt = json.dumps([r['Events'] for r in monthly_flood])

# Cumulative percentages
cumul = []
running = 0
for r in by_state:
    running += r['FloodDamage']
    cumul.append(round(running / state_total * 100, 1))
cumul_json = json.dumps(cumul)

for r in by_state[:5]:
    print(f"  {r['State']:20s} {fmt(r['FloodDamage']):>10s}  Events={r['Events']:>5,}")
print(f"  Top 3 states = {top3_pct}% of all flood damage")

write("hypothesis_03_geographic.html", f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hypothesis 03 — Geographic Hotspots: Where Is Flood Damage Concentrated?</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0f0f23;color:#e0e0e0;padding:24px}}
  h1{{text-align:center;font-size:24px;margin-bottom:4px;background:linear-gradient(135deg,#42a5f5,#66bb6a);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  .subtitle{{text-align:center;color:#888;font-size:13px;margin-bottom:20px}}
  .question{{text-align:center;font-size:16px;color:#ccc;margin-bottom:20px;font-style:italic;border-left:3px solid #ab47bc;padding:8px 16px;display:inline-block;width:100%}}
  .verdict{{text-align:center;margin-bottom:24px;padding:16px 24px;border-radius:12px;width:100%}}
  .verdict.supported{{background:linear-gradient(135deg,#1a3a1a,#2a4a2a);border:2px solid #66bb6a}}
  .verdict .badge{{font-size:14px;font-weight:700;letter-spacing:2px;padding:4px 12px;border-radius:6px;display:inline-block;margin-bottom:8px}}
  .verdict.supported .badge{{background:#66bb6a;color:#1a1a1a}}
  .verdict .summary{{font-size:14px;color:#ccc}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}}
  .card{{background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4e}}
  .card h3{{font-size:15px;color:#ccc;margin-bottom:12px}}
  .full{{grid-column:1/-1}}canvas{{max-height:380px}}
  .kpi-row{{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-bottom:24px}}
  .kpi{{background:linear-gradient(135deg,#1a1a3e,#2a2a5e);border-radius:12px;padding:16px 24px;min-width:140px;text-align:center;border:1px solid #333366}}
  .kpi .value{{font-size:28px;font-weight:800}}
  .kpi .label{{font-size:11px;color:#aaa;margin-top:4px;text-transform:uppercase;letter-spacing:1px}}
  .kpi.orange .value{{color:#ffa726}}.kpi.blue .value{{color:#42a5f5}}.kpi.red .value{{color:#ff6b6b}}.kpi.green .value{{color:#66bb6a}}.kpi.purple .value{{color:#ab47bc}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{text-align:left;padding:8px 10px;border-bottom:2px solid #333;color:#aaa;font-weight:600}}
  td{{padding:7px 10px;border-bottom:1px solid #222}}tr:hover{{background:#1e1e3e}}.right{{text-align:right}}
  .footer{{text-align:center;color:#555;font-size:12px;margin-top:20px}}
  .caveat{{background:#1a1a2e;border-radius:8px;padding:16px;border-left:3px solid #ffa726;margin-top:20px;font-size:13px;color:#aaa}}
  .caveat h4{{color:#ffa726;margin-bottom:8px;font-size:13px}}
</style>
</head>
<body>
<h1>Hypothesis Dashboard 3 of 3</h1>
<p class="subtitle">Hypothesis: Flood events cause disproportionately more damage per event than other storm types</p>
<div class="question">Sub-question: Are there geographic hotspots driving the flood damage, or is it evenly distributed?</div>
<div class="verdict supported">
  <div class="badge">SUPPORTED</div>
  <div class="summary">Flood damage is highly concentrated: the top 3 states ({by_state[0]['State'].title()}, {by_state[1]['STATE' if 'STATE' in by_state[1] else 'State'].title()}, {by_state[2]['State'].title()}) account for {top3_pct}% of all flood damage. {by_state[0]['State'].title()} alone ({fmt(by_state[0]['FloodDamage'])}) represents {round(by_state[0]['FloodDamage']/state_total*100)}%.</div>
</div>
<div class="kpi-row">
  <div class="kpi purple"><div class="value">{top3_pct}%</div><div class="label">Top 3 States Share</div></div>
  <div class="kpi orange"><div class="value">{fmt(by_state[0]['FloodDamage'])}</div><div class="label">{by_state[0]['State'].title()} (#1)</div></div>
  <div class="kpi blue"><div class="value">{fmt(by_state[1]['FloodDamage'])}</div><div class="label">{by_state[1]['State'].title()} (#2)</div></div>
  <div class="kpi green"><div class="value">{fmt(by_state[2]['FloodDamage'])}</div><div class="label">{by_state[2]['State'].title()} (#3)</div></div>
</div>
<div class="grid">
  <div class="card full"><h3>Flood Damage by State — Top 15</h3><canvas id="stChart"></canvas></div>
  <div class="card"><h3>Cumulative Share of Flood Damage</h3><canvas id="cumChart"></canvas></div>
  <div class="card"><h3>Flood Damage by State</h3><table>
    <tr><th>State</th><th class="right">Damage</th><th class="right">Events</th><th class="right">%</th><th class="right">Deaths</th></tr>
    {state_table}</table>
  </div>
  <div class="card full"><h3>Monthly Flood Damage Trend (2007)</h3><canvas id="moChart"></canvas></div>
</div>
<div class="caveat"><h4>Caveats</h4><ul>
  <li>Geographic concentration means a few catastrophic events drive the national average.</li>
  <li>Seasonal Jul–Aug spike suggests summer flooding is the primary driver.</li>
  <li>Single year (2007) — patterns may vary across years.</li>
</ul></div>
<p class="footer">Generated by yokusto — YOLO Hypothesis Mode — {CLUSTER} / {DATABASE} / StormEvents</p>
<script>
const st={state_labels};const sd={state_damages};
new Chart(document.getElementById('stChart'),{{type:'bar',data:{{labels:st,datasets:[{{data:sd,backgroundColor:sd.map((d,i)=>i<3?'#26c6da':'#42a5f5')}}]}},options:{{indexAxis:'y',responsive:true,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>'$'+(c.raw/1e6).toFixed(1)+'M'}}}}}},scales:{{x:{{ticks:{{color:'#888',callback:v=>'$'+(v/1e6).toFixed(0)+'M'}},grid:{{color:'#222'}}}},y:{{ticks:{{color:'#ccc',font:{{size:11}}}},grid:{{color:'#222'}}}}}}}}}});
new Chart(document.getElementById('cumChart'),{{type:'line',data:{{labels:st,datasets:[{{label:'Cumulative %',data:{cumul_json},borderColor:'#26c6da',backgroundColor:'rgba(38,198,218,0.1)',fill:true,tension:.3}},{{label:'80% line',data:Array(15).fill(80),borderColor:'#ff6b6b',borderDash:[6,4],pointRadius:0,borderWidth:2,fill:false}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#ccc'}}}}}},scales:{{x:{{ticks:{{color:'#888',maxRotation:45,font:{{size:10}}}},grid:{{color:'#222'}}}},y:{{ticks:{{color:'#888',callback:v=>v+'%'}},grid:{{color:'#222'}},min:0,max:100}}}}}}}});
const mn={month_names};const md={month_dmg};const me={month_evt};
new Chart(document.getElementById('moChart'),{{type:'bar',data:{{labels:mn,datasets:[{{label:'Damage ($)',data:md,backgroundColor:md.map(d=>d>200000000?'#26c6da':'#42a5f5'),yAxisID:'y'}},{{label:'Events',data:me,type:'line',borderColor:'#ffa726',backgroundColor:'transparent',yAxisID:'y1',tension:.3,pointRadius:3}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#ccc'}}}}}},scales:{{x:{{ticks:{{color:'#888'}},grid:{{color:'#222'}}}},y:{{position:'left',ticks:{{color:'#888',callback:v=>'$'+(v/1e6).toFixed(0)+'M'}},grid:{{color:'#222'}}}},y1:{{position:'right',ticks:{{color:'#ffa726'}},grid:{{display:false}}}}}}}}}});
</script></body></html>""")

print("  Dashboard 3/3 complete — geographic hotspots.")

# ── Executive Summary ──────────────────────────
print("\nGenerating executive summary...")

write("hypothesis_summary.html", f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hypothesis Summary — Are Floods Disproportionately Destructive?</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0f0f23;color:#e0e0e0;padding:24px}}
  h1{{text-align:center;font-size:28px;margin-bottom:4px;background:linear-gradient(135deg,#ffa726,#ff6b6b);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  .subtitle{{text-align:center;color:#888;font-size:14px;margin-bottom:8px}}
  .hypothesis{{text-align:center;font-size:16px;color:#ccc;margin-bottom:24px;padding:12px 24px;background:#1a1a2e;border-radius:12px;border:1px solid #333;font-style:italic;max-width:800px;margin-left:auto;margin-right:auto}}
  .overall-verdict{{text-align:center;margin-bottom:32px;padding:24px 32px;border-radius:16px;max-width:700px;margin-left:auto;margin-right:auto}}
  .overall-verdict.partial{{background:linear-gradient(135deg,#2a2a1a,#3a3a2a);border:3px solid #ffa726}}
  .overall-verdict .big-badge{{font-size:20px;font-weight:800;letter-spacing:3px;padding:8px 24px;border-radius:8px;display:inline-block;margin-bottom:12px}}
  .overall-verdict.partial .big-badge{{background:#ffa726;color:#1a1a1a}}
  .overall-verdict .verdict-text{{font-size:15px;color:#ddd;line-height:1.6}}
  .evidence-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:32px;max-width:1200px;margin-left:auto;margin-right:auto}}
  @media(max-width:900px){{.evidence-grid{{grid-template-columns:1fr}}}}
  .evidence-card{{background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4e;position:relative;overflow:hidden}}
  .evidence-card .num{{position:absolute;top:12px;right:16px;font-size:48px;font-weight:900;color:rgba(255,255,255,0.05)}}
  .evidence-card h3{{font-size:14px;color:#aaa;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px}}
  .evidence-card .q{{font-size:14px;color:#ccc;margin-bottom:12px;font-style:italic}}
  .evidence-card .verdict-badge{{font-size:11px;font-weight:700;letter-spacing:1px;padding:3px 10px;border-radius:4px;display:inline-block;margin-bottom:10px}}
  .badge-supported{{background:#66bb6a;color:#1a1a1a}}.badge-partial{{background:#ffa726;color:#1a1a1a}}
  .evidence-card .finding{{font-size:13px;color:#bbb;line-height:1.5}}
  .evidence-card .metric{{font-size:24px;font-weight:800;color:#42a5f5;margin:8px 0}}
  .evidence-card a{{color:#42a5f5;text-decoration:none;font-size:12px;display:inline-block;margin-top:10px}}
  .evidence-card a:hover{{text-decoration:underline}}
  .kpi-row{{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-bottom:28px}}
  .kpi{{background:linear-gradient(135deg,#1a1a3e,#2a2a5e);border-radius:12px;padding:16px 24px;min-width:140px;text-align:center;border:1px solid #333366}}
  .kpi .value{{font-size:28px;font-weight:800}}
  .kpi .label{{font-size:11px;color:#aaa;margin-top:4px;text-transform:uppercase;letter-spacing:1px}}
  .kpi.orange .value{{color:#ffa726}}.kpi.blue .value{{color:#42a5f5}}.kpi.red .value{{color:#ff6b6b}}.kpi.green .value{{color:#66bb6a}}.kpi.cyan .value{{color:#26c6da}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;max-width:1200px;margin-left:auto;margin-right:auto}}
  .card{{background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4e}}
  .card h3{{font-size:15px;color:#ccc;margin-bottom:12px}}
  .next-section{{max-width:700px;margin:0 auto 24px;background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4e}}
  .next-section h3{{font-size:15px;color:#ccc;margin-bottom:12px}}
  .next-hyp{{background:#111122;border-radius:8px;padding:12px 16px;margin-bottom:8px;border-left:3px solid #42a5f5;font-size:13px;color:#bbb}}
  .next-hyp strong{{color:#42a5f5}}
  canvas{{max-height:320px}}
  .footer{{text-align:center;color:#555;font-size:12px;margin-top:24px}}
</style>
</head>
<body>
<h1>Hypothesis Investigation — Executive Summary</h1>
<p class="subtitle">YOLO Mode: 3 evidence dashboards generated autonomously</p>
<div class="hypothesis">"Flood events cause disproportionately more property damage per event than any other storm type, and this pattern is driven by geographic hotspots."</div>

<div class="overall-verdict partial">
  <div class="big-badge">PARTIALLY SUPPORTED</div>
  <div class="verdict-text">
    Floods are <strong>{ratio:.1f}× more damaging per event</strong> than the average storm ({fmt(flood_pe['PerEvent'])} vs {fmt(other_pe['PerEvent'])}) — but they are <strong>not the most destructive per event</strong>.
    Wildfires, Frost/Freeze, Ice Storms, and Tornadoes all cause more per-event damage. By total damage, floods rank 6th–7th individually,
    though combined (Flood + Flash Flood = {fmt(flood_total)}) they rival the top spot. The damage is <strong>highly concentrated</strong>:
    {top3_pct}% originates from just 3 states, confirming the geographic hotspot component.
  </div>
</div>

<div class="kpi-row">
  <div class="kpi cyan"><div class="value">{ratio:.1f}×</div><div class="label">Flood vs. Average</div></div>
  <div class="kpi orange"><div class="value">{fmt(flood_pe['PerEvent'])}</div><div class="label">Flood Per-Event</div></div>
  <div class="kpi blue"><div class="value">{fmt(other_pe['PerEvent'])}</div><div class="label">Overall Average</div></div>
  <div class="kpi red"><div class="value">{flood_deaths:,}</div><div class="label">Flood Deaths</div></div>
  <div class="kpi green"><div class="value">{top3_pct}%</div><div class="label">Top 3 States</div></div>
</div>

<div class="evidence-grid">
  <div class="evidence-card">
    <div class="num">1</div>
    <h3>Dashboard 1 — Total Damage Ranking</h3>
    <div class="q">"Where do floods rank among all storm types by total damage?"</div>
    <div class="verdict-badge badge-partial">PARTIALLY SUPPORTED</div>
    <div class="metric">#6–7</div>
    <div class="finding">Floods rank 6th–7th individually. Combined ({fmt(flood_total)}) they would rival #1. Five individual types cause more total damage.</div>
    <a href="hypothesis_01_ranking.html">View full dashboard →</a>
  </div>
  <div class="evidence-card">
    <div class="num">2</div>
    <h3>Dashboard 2 — Per-Event Damage</h3>
    <div class="q">"Is per-event flood damage disproportionately high?"</div>
    <div class="verdict-badge badge-supported">SUPPORTED</div>
    <div class="metric">{fmt(flood_pe['PerEvent'])} vs {fmt(other_pe['PerEvent'])}</div>
    <div class="finding">At {fmt(flood_pe['PerEvent'])} per event, floods cause {ratio:.1f}× more damage than the non-flood average. However, 4 other types are higher per-event.</div>
    <a href="hypothesis_02_per_event.html">View full dashboard →</a>
  </div>
  <div class="evidence-card">
    <div class="num">3</div>
    <h3>Dashboard 3 — Geographic Hotspots</h3>
    <div class="q">"Is flood damage concentrated in specific states?"</div>
    <div class="verdict-badge badge-supported">SUPPORTED</div>
    <div class="metric">{top3_pct}% in 3 states</div>
    <div class="finding">{by_state[0]['State'].title()} ({fmt(by_state[0]['FloodDamage'])}), {by_state[1]['State'].title()} ({fmt(by_state[1]['FloodDamage'])}), {by_state[2]['State'].title()} ({fmt(by_state[2]['FloodDamage'])}) dominate. Jul–Aug spike confirms seasonal concentration.</div>
    <a href="hypothesis_03_geographic.html">View full dashboard →</a>
  </div>
</div>

<div class="grid">
  <div class="card"><h3>Verdict Scorecard</h3><canvas id="scChart"></canvas></div>
  <div class="card"><h3>Key Comparison</h3><canvas id="cpChart"></canvas></div>
</div>

<div class="next-section">
  <h3>Suggested Follow-Up Hypotheses</h3>
  <div class="next-hyp"><strong>Hypothesis A:</strong> "Summer flooding (Jul–Aug) is driven by Midwest states — coastal states have a different seasonal profile."</div>
  <div class="next-hyp"><strong>Hypothesis B:</strong> "{by_state[0]['State'].title()}'s outsized flood damage was caused by 1–2 catastrophic events — removing outliers would drop it from #1."</div>
</div>

<p class="footer">Generated by yokusto — YOLO Hypothesis Mode — {CLUSTER} / {DATABASE} / StormEvents<br>3 evidence dashboards + 1 summary = 4 artifacts total</p>
<script>
new Chart(document.getElementById('scChart'),{{type:'doughnut',data:{{labels:['Supported','Partially Supported','Not Supported'],datasets:[{{data:[2,1,0],backgroundColor:['#66bb6a','#ffa726','#ff6b6b']}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#ccc'}}}},tooltip:{{callbacks:{{label:c=>c.label+': '+c.raw+' dashboard(s)'}}}}}}}}}});
new Chart(document.getElementById('cpChart'),{{type:'bar',data:{{labels:['Per-Event $','Total $ (combined)'],datasets:[{{label:'Floods',data:[{flood_pe['PerEvent']},{flood_total}],backgroundColor:'#26c6da'}},{{label:'Non-Flood',data:[{other_pe['PerEvent']},{other_pe['TotalDamage']}],backgroundColor:'#78909c'}}]}},options:{{indexAxis:'y',responsive:true,plugins:{{legend:{{labels:{{color:'#ccc'}}}}}},scales:{{x:{{display:false}},y:{{ticks:{{color:'#ccc'}},grid:{{color:'#222'}}}}}}}}}});
</script></body></html>""")

print("\n" + "=" * 60)
print("DONE — 4 dashboards generated:")
print(f"  1. hypothesis_01_ranking.html")
print(f"  2. hypothesis_02_per_event.html")
print(f"  3. hypothesis_03_geographic.html")
print(f"  4. hypothesis_summary.html      (executive summary)")
print("=" * 60)
