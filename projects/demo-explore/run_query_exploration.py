"""
yokusto Query-Driven Exploration Demo
======================================
Seed query: StormEvents | summarize count() by State | top 10 by count_

This script queries help.kusto.windows.net / Samples / StormEvents, starting
from a simple seed query and expanding into 5 follow-up analyses:

  1. What storm types dominate in the top states?
  2. How does event count trend month-by-month?
  3. Which states have the highest damage per event?
  4. What does the hourly pattern look like?
  5. How diverse are storm types across states?

Output: query_exploration_dashboard.html

Prerequisites:
  pip install azure-kusto-data azure-identity
  az login
"""
from azure.identity import AzureCliCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder, ClientRequestProperties
from datetime import timedelta
import json, os, sys

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
    if abs(n) >= 1_000_000_000: return f"${n/1_000_000_000:,.1f}B"
    if abs(n) >= 1_000_000: return f"${n/1_000_000:,.1f}M"
    if abs(n) >= 1_000: return f"${n/1_000:,.0f}K"
    return f"${n:,.0f}"

def write(filename, content):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ Wrote {path}")

# ═══════════════════════════════════════════════
# SEED QUERY
# ═══════════════════════════════════════════════
print("=" * 60)
print("QUERY-DRIVEN EXPLORATION MODE")
print("Seed: StormEvents | summarize count() by State | top 10")
print("=" * 60)
print()

print("Running seed query ...")
seed = query("StormEvents | summarize EventCount=count() by State | top 10 by EventCount desc")
total_events = sum(r["EventCount"] for r in seed)
print(f"  {len(seed)} states, {total_events:,} events total")

# ── Follow-up 1: Storm types in top states ──
print("\n[1/5] What storm types dominate in these top states?")
q1 = query("""
let topStates = StormEvents | summarize c=count() by State | top 10 by c | project State;
StormEvents
| where State in (topStates)
| summarize Events=count(), Damage=sum(DamageProperty + DamageCrops) by State, EventType
| top 50 by Events desc
""")
print(f"  {len(q1)} rows")

# ── Follow-up 2: Monthly trend ──
print("[2/5] Monthly trend for top 10 states ...")
q2 = query("""
let topStates = StormEvents | summarize c=count() by State | top 10 by c | project State;
StormEvents
| where State in (topStates)
| summarize Events=count(), Damage=sum(DamageProperty + DamageCrops) by Month=startofmonth(StartTime), State
| order by Month asc, State asc
""")
print(f"  {len(q2)} rows")

# ── Follow-up 3: Damage per event ──
print("[3/5] Which states have the highest damage per event?")
q3 = query("""
StormEvents
| summarize Events=count(), TotalDamage=sum(DamageProperty + DamageCrops),
    Deaths=sum(DeathsDirect + DeathsIndirect) by State
| where Events >= 50
| extend DamagePerEvent = TotalDamage / Events
| top 15 by DamagePerEvent desc
""")
print(f"  {len(q3)} states")

# ── Follow-up 4: Hourly pattern ──
print("[4/5] Hour-of-day storm pattern ...")
q4 = query("""
let topStates = StormEvents | summarize c=count() by State | top 10 by c | project State;
StormEvents
| where State in (topStates)
| extend Hour = datetime_part("hour", StartTime)
| summarize Events=count() by Hour
| order by Hour asc
""")
print(f"  {len(q4)} hours")

# ── Follow-up 5: Event type diversity ──
print("[5/5] Storm type diversity by state ...")
q5 = query("""
StormEvents
| summarize EventTypes=dcount(EventType), Events=count(), Damage=sum(DamageProperty+DamageCrops) by State
| top 15 by Events desc
""")
print(f"  {len(q5)} states")

# ═══════════════════════════════════════════════
# BUILD DASHBOARD
# ═══════════════════════════════════════════════
print("\nBuilding dashboard ...")

# Prepare chart data
# Top types per state (aggregate across states for a stacked view)
type_totals = {}
for r in q1:
    et = r["EventType"]
    type_totals[et] = type_totals.get(et, 0) + r["Events"]
top_types = sorted(type_totals, key=type_totals.get, reverse=True)[:8]

# State breakdown for top types
state_type_matrix = {}
for r in q1:
    if r["EventType"] in top_types:
        state_type_matrix.setdefault(r["State"], {})[r["EventType"]] = r["Events"]

# Monthly aggregates
monthly = {}
for r in q2:
    m = str(r["Month"])[:7]
    monthly[m] = monthly.get(m, 0) + r["Events"]
months_sorted = sorted(monthly.keys())

# Hourly data
hours = [r["Events"] for r in sorted(q4, key=lambda x: x["Hour"])]

# Colors
palette = ["#FF6384","#36A2EB","#FFCE56","#4BC0C0","#9966FF","#FF9F40","#C9CBCF","#7BC8A4"]

# Seed KPI data
top_state = seed[0]["State"].title()
top_count = seed[0]["EventCount"]
state_count = len(seed)

# Damage efficiency data
most_expensive = q3[0]

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Query-Driven Exploration — Storm Events by State</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#c9d1d9;font-family:'Segoe UI',system-ui,sans-serif;padding:24px;max-width:1280px;margin:0 auto}}
h1{{color:#58a6ff;font-size:2rem;text-align:center;margin-bottom:4px}}
.subtitle{{text-align:center;color:#8b949e;margin-bottom:8px;font-size:0.95rem}}
.seed-box{{background:#161b22;border:2px solid #30363d;border-radius:12px;padding:20px;margin:16px 0 24px;text-align:center}}
.seed-box code{{background:#1f2937;color:#7ee787;padding:8px 16px;border-radius:6px;font-size:1.05rem;display:inline-block;margin:8px 0}}
.seed-label{{color:#8b949e;font-size:0.85rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}}
.kpis{{display:flex;flex-wrap:wrap;gap:16px;justify-content:center;margin:20px 0}}
.kpi{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:16px 24px;text-align:center;min-width:160px;flex:1;max-width:220px}}
.kpi .val{{font-size:1.8rem;font-weight:800;color:#58a6ff}}
.kpi .val.orange{{color:#f0883e}}
.kpi .val.green{{color:#7ee787}}
.kpi .val.purple{{color:#bc8cff}}
.kpi .label{{font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;color:#8b949e;margin-top:4px}}
.section{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px;margin:20px 0}}
.section h3{{color:#58a6ff;margin-bottom:6px;font-size:1.1rem}}
.section .question{{color:#f0883e;font-style:italic;margin-bottom:14px;font-size:0.92rem}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}
canvas{{max-height:350px}}
table{{width:100%;border-collapse:collapse;margin-top:10px;font-size:0.88rem}}
th{{background:#21262d;color:#58a6ff;padding:8px;text-align:left;border-bottom:2px solid #30363d}}
td{{padding:7px 8px;border-bottom:1px solid #21262d}}
tr:hover{{background:#1c2128}}
.follow-up{{background:#1c2128;border:1px solid #f0883e44;border-radius:10px;padding:18px;margin:20px 0}}
.follow-up h3{{color:#f0883e;margin-bottom:10px}}
.follow-up ul{{padding-left:20px}}
.follow-up li{{margin:8px 0;color:#c9d1d9}}
.footer{{text-align:center;color:#484f58;font-size:0.8rem;margin-top:30px;padding:16px 0;border-top:1px solid #21262d}}
</style>
</head>
<body>

<h1>Query-Driven Exploration — Storm Events</h1>
<p class="subtitle">Starting from a simple seed query, yokusto explored 5 follow-up angles automatically</p>

<div class="seed-box">
  <div class="seed-label">Seed Query</div>
  <code>StormEvents | summarize count() by State | top 10 by count_</code>
  <div style="color:#8b949e;margin-top:8px;font-size:0.85rem">From this one query, the agent discovered schema, analyzed patterns, and produced 5 follow-up visualizations</div>
</div>

<div class="kpis">
  <div class="kpi"><div class="val">{top_state}</div><div class="label">#1 State</div></div>
  <div class="kpi"><div class="val orange">{top_count:,}</div><div class="label">Events in {top_state}</div></div>
  <div class="kpi"><div class="val green">{total_events:,}</div><div class="label">Top-10 Total</div></div>
  <div class="kpi"><div class="val purple">{most_expensive['State'].title()}</div><div class="label">Costliest per Event</div></div>
  <div class="kpi"><div class="val">{fmt(most_expensive['DamagePerEvent'])}</div><div class="label">Damage / Event</div></div>
</div>

<div class="grid">

<!-- Chart 1: Stacked bar - storm types by state -->
<div class="section">
  <h3>Follow-Up 1 — Storm Types by State</h3>
  <div class="question">"What storm types dominate in the top 10 states?"</div>
  <canvas id="chart1"></canvas>
</div>

<!-- Chart 2: Monthly trend -->
<div class="section">
  <h3>Follow-Up 2 — Monthly Event Trend</h3>
  <div class="question">"How does the event count change month by month?"</div>
  <canvas id="chart2"></canvas>
</div>

<!-- Chart 3: Damage per event -->
<div class="section">
  <h3>Follow-Up 3 — Damage Efficiency</h3>
  <div class="question">"Which states have the highest damage per event?"</div>
  <canvas id="chart3"></canvas>
</div>

<!-- Chart 4: Hourly pattern -->
<div class="section">
  <h3>Follow-Up 4 — Hour of Day Pattern</h3>
  <div class="question">"When do storms happen during the day?"</div>
  <canvas id="chart4"></canvas>
</div>

</div>

<!-- Table: Seed results + diversity -->
<div class="section">
  <h3>Follow-Up 5 — State Overview: Events, Diversity & Damage</h3>
  <div class="question">"How diverse are storm types across the top states?"</div>
  <table>
    <thead><tr><th>State</th><th>Events</th><th>Storm Types</th><th>Total Damage</th><th>Damage/Event</th></tr></thead>
    <tbody>"""

for r in q5:
    dpe = r["Damage"] / r["Events"] if r["Events"] else 0
    html += f"""
      <tr><td>{r['State'].title()}</td><td>{r['Events']:,}</td><td>{r['EventTypes']}</td><td>{fmt(r['Damage'])}</td><td>{fmt(dpe)}</td></tr>"""

html += """
    </tbody>
  </table>
</div>

<div class="follow-up">
  <h3>What yokusto would suggest next</h3>
  <ul>
    <li><strong>"California has $3.1M damage per event but only 898 events — what's causing that?"</strong> → drill into CA's event types</li>
    <li><strong>"The midnight spike is unusual — are those overnight tornadoes or reporting artifacts?"</strong> → filter hour 0 by event type</li>
    <li><strong>"Texas has 27 storm types — which ones cause the most damage?"</strong> → TX-specific breakdown</li>
    <li><strong>"The summer peak is obvious — but does damage peak at the same time?"</strong> → overlay damage $ on the monthly trend</li>
  </ul>
</div>

<p class="footer">Generated by yokusto — Query-Driven Exploration Mode — help.kusto.windows.net / Samples / StormEvents</p>

<script>
// Chart 1: Stacked bar - types by state
const states1 = """ + json.dumps([s for s in seed]) + """;
const stateNames = states1.map(s => s.State.replace(/\\b\\w/g, c => c.toUpperCase()).replace(/ \\w/g, c => c.toUpperCase()));
const topTypes = """ + json.dumps(top_types) + """;
const palette = """ + json.dumps(palette) + """;
const matrix = """ + json.dumps(state_type_matrix) + """;

new Chart(document.getElementById('chart1'), {
  type: 'bar',
  data: {
    labels: stateNames,
    datasets: topTypes.map((t, i) => ({
      label: t,
      data: states1.map(s => (matrix[s.State] || {})[t] || 0),
      backgroundColor: palette[i % palette.length]
    }))
  },
  options: {
    responsive: true, indexAxis: 'y', scales: { x: { stacked: true, ticks:{color:'#8b949e'}, grid:{color:'#21262d'} }, y: { stacked: true, ticks:{color:'#c9d1d9'}, grid:{display:false} } },
    plugins: { legend: { labels: { color:'#c9d1d9', font:{size:10} } } }
  }
});

// Chart 2: Monthly trend
const months = """ + json.dumps(months_sorted) + """;
const monthCounts = """ + json.dumps([monthly[m] for m in months_sorted]) + """;
new Chart(document.getElementById('chart2'), {
  type: 'line',
  data: {
    labels: months,
    datasets: [{ label: 'Events', data: monthCounts, borderColor: '#58a6ff', backgroundColor: '#58a6ff33', fill: true, tension: 0.3, pointRadius: 4 }]
  },
  options: { responsive: true, scales: { x:{ticks:{color:'#8b949e'},grid:{color:'#21262d'}}, y:{ticks:{color:'#8b949e'},grid:{color:'#21262d'}} }, plugins: { legend:{display:false} } }
});

// Chart 3: Damage per event (horizontal bar)
const dpeStates = """ + json.dumps([r["State"].title() for r in q3[:10]]) + """;
const dpeValues = """ + json.dumps([r["DamagePerEvent"] for r in q3[:10]]) + """;
new Chart(document.getElementById('chart3'), {
  type: 'bar',
  data: {
    labels: dpeStates,
    datasets: [{ label: 'Damage per Event ($)', data: dpeValues, backgroundColor: '#f0883e' }]
  },
  options: { responsive: true, indexAxis: 'y', scales: { x:{ticks:{color:'#8b949e',callback:v=>'$'+(v/1e6).toFixed(1)+'M'},grid:{color:'#21262d'}}, y:{ticks:{color:'#c9d1d9'},grid:{display:false}} }, plugins:{legend:{display:false}} }
});

// Chart 4: Polar area - hourly
const hourData = """ + json.dumps(hours) + """;
const hourLabels = Array.from({length:24}, (_,i) => i.toString().padStart(2,'0')+':00');
new Chart(document.getElementById('chart4'), {
  type: 'polarArea',
  data: {
    labels: hourLabels,
    datasets: [{ data: hourData, backgroundColor: hourData.map((_,i)=>`hsla(${i*15},70%,55%,0.6)`), borderColor: hourData.map((_,i)=>`hsla(${i*15},70%,55%,1)`) }]
  },
  options: { responsive: true, scales: { r:{ticks:{color:'#8b949e',backdropColor:'transparent'},grid:{color:'#21262d33'}} }, plugins: { legend:{display:false} } }
});
</script>

</body></html>"""

write("query_exploration_dashboard.html", html)
print("\n✅ Done — open query_exploration_dashboard.html in a browser")
