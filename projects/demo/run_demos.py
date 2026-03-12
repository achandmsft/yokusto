"""yokusto: Generate 3 showcase dashboards from help.kusto.windows.net."""
from azure.identity import AzureCliCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder, ClientRequestProperties
from datetime import timedelta
from collections import defaultdict
import json, html as html_mod

cred = AzureCliCredential()
kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
    "https://help.kusto.windows.net", cred)
client = KustoClient(kcsb)

def query(db, kql, timeout_min=10):
    props = ClientRequestProperties()
    props.set_option("servertimeout", timedelta(minutes=timeout_min))
    resp = client.execute_query(db, kql, props)
    table = resp.primary_results[0]
    cols = [c.column_name for c in table.columns]
    return [{cols[i]: row[i] for i in range(len(cols))} for row in table]

def fmt(n):
    if n >= 1_000_000_000: return f"${n/1_000_000_000:,.1f}B"
    if n >= 1_000_000: return f"${n/1_000_000:,.1f}M"
    if n >= 1_000: return f"${n/1_000:,.0f}K"
    return f"${n:,.0f}"

def fmtN(n):
    if n >= 1_000_000: return f"{n/1_000_000:,.1f}M"
    if n >= 1_000: return f"{n/1_000:,.1f}K"
    return f"{n:,}"

# ═══════════════════════════════════════════════════════════════
# DASHBOARD 1: Storm Events — Damage & Destruction
# ═══════════════════════════════════════════════════════════════
print("━" * 60)
print("DASHBOARD 1: Storm Damage & Destruction")
print("━" * 60)

print("  Querying overview...")
overview = query("Samples", """
StormEvents
| summarize Events=count(),
    PropertyDamage=sum(DamageProperty),
    CropDamage=sum(DamageCrops),
    Deaths=sum(DeathsDirect + DeathsIndirect),
    Injuries=sum(InjuriesDirect + InjuriesIndirect),
    States=dcount(State)
""")[0]
print(f"  {overview['Events']:,} events, {fmt(overview['PropertyDamage'])} property, {fmt(overview['CropDamage'])} crop, {overview['Deaths']} deaths")

print("  Querying top event types by damage...")
by_type = query("Samples", """
StormEvents
| summarize Events=count(),
    TotalDamage=sum(DamageProperty + DamageCrops),
    Deaths=sum(DeathsDirect + DeathsIndirect),
    Injuries=sum(InjuriesDirect + InjuriesIndirect)
  by EventType
| top 12 by TotalDamage desc
""")

print("  Querying monthly trend...")
by_month = query("Samples", """
StormEvents
| summarize Events=count(),
    Damage=sum(DamageProperty + DamageCrops),
    Deaths=sum(DeathsDirect + DeathsIndirect)
  by Month=startofmonth(StartTime)
| order by Month asc
""")

print("  Querying top 15 states by damage...")
by_state = query("Samples", """
StormEvents
| summarize Events=count(),
    PropertyDamage=sum(DamageProperty),
    CropDamage=sum(DamageCrops),
    Deaths=sum(DeathsDirect + DeathsIndirect)
  by State
| top 15 by PropertyDamage + CropDamage desc
""")

print("  Querying deadliest events...")
deadliest = query("Samples", """
StormEvents
| summarize Deaths=sum(DeathsDirect + DeathsIndirect),
    Events=count(),
    Damage=sum(DamageProperty + DamageCrops)
  by EventType
| where Deaths > 0
| top 10 by Deaths desc
""")

total_damage = overview['PropertyDamage'] + overview['CropDamage']

# Build Dashboard 1 HTML
month_labels = [str(r['Month'])[:7] for r in by_month]
month_events = [r['Events'] for r in by_month]
month_damage = [r['Damage'] for r in by_month]
month_deaths = [r['Deaths'] for r in by_month]

type_labels = [r['EventType'] for r in by_type]
type_damage = [r['TotalDamage'] for r in by_type]
type_deaths = [r['Deaths'] for r in by_type]
type_events = [r['Events'] for r in by_type]

state_labels = [r['State'] for r in by_state]
state_prop = [r['PropertyDamage'] for r in by_state]
state_crop = [r['CropDamage'] for r in by_state]

dead_labels = [r['EventType'] for r in deadliest]
dead_deaths = [r['Deaths'] for r in deadliest]
dead_injuries_placeholder = [r['Events'] for r in deadliest]

storm_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>yokusto — US Storm Damage & Destruction (2007)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0f0f23; color: #e0e0e0; padding: 24px; }}
  h1 {{ text-align: center; font-size: 28px; margin-bottom: 6px; background: linear-gradient(135deg, #ff6b6b, #ffa726); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .subtitle {{ text-align: center; color: #888; font-size: 14px; margin-bottom: 24px; }}
  .kpi-row {{ display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin-bottom: 28px; }}
  .kpi {{ background: linear-gradient(135deg, #1a1a3e, #2a2a5e); border-radius: 12px; padding: 20px 28px; min-width: 160px; text-align: center; border: 1px solid #333366; }}
  .kpi .value {{ font-size: 32px; font-weight: 800; }}
  .kpi .label {{ font-size: 12px; color: #aaa; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }}
  .kpi.red .value {{ color: #ff6b6b; }}
  .kpi.orange .value {{ color: #ffa726; }}
  .kpi.blue .value {{ color: #42a5f5; }}
  .kpi.green .value {{ color: #66bb6a; }}
  .kpi.purple .value {{ color: #ab47bc; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
  .card {{ background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4e; }}
  .card h3 {{ font-size: 15px; color: #ccc; margin-bottom: 12px; }}
  .full {{ grid-column: 1 / -1; }}
  canvas {{ max-height: 320px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 10px; border-bottom: 2px solid #333; color: #aaa; font-weight: 600; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #222; }}
  tr:hover {{ background: #1e1e3e; }}
  .right {{ text-align: right; }}
  .red {{ color: #ff6b6b; }}
  .footer {{ text-align: center; color: #555; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>
<h1>US Storm Damage & Destruction</h1>
<p class="subtitle">59,066 storm events across 67 states &amp; territories &mdash; Full Year 2007</p>

<div class="kpi-row">
  <div class="kpi orange"><div class="value">{fmt(total_damage)}</div><div class="label">Total Damage</div></div>
  <div class="kpi red"><div class="value">{overview['Deaths']:,}</div><div class="label">Deaths</div></div>
  <div class="kpi purple"><div class="value">{overview['Injuries']:,}</div><div class="label">Injuries</div></div>
  <div class="kpi blue"><div class="value">{overview['Events']:,}</div><div class="label">Storm Events</div></div>
  <div class="kpi green"><div class="value">{overview['States']}</div><div class="label">States</div></div>
</div>

<div class="grid">
  <div class="card full">
    <h3>Monthly Storm Activity &amp; Damage Trend</h3>
    <canvas id="monthlyChart"></canvas>
  </div>
  <div class="card">
    <h3>Top 12 Storm Types by Total Damage ($)</h3>
    <canvas id="typeChart"></canvas>
  </div>
  <div class="card">
    <h3>Top 15 States &mdash; Property vs Crop Damage</h3>
    <canvas id="stateChart"></canvas>
  </div>
  <div class="card">
    <h3>Deadliest Storm Types</h3>
    <canvas id="deadChart"></canvas>
  </div>
  <div class="card">
    <h3>Damage Breakdown by Event Type</h3>
    <table>
      <tr><th>Event Type</th><th class="right">Events</th><th class="right">Damage ($)</th><th class="right">Deaths</th></tr>
      {"".join(f'<tr><td>{r["EventType"]}</td><td class="right">{r["Events"]:,}</td><td class="right">{fmt(r["TotalDamage"])}</td><td class="right{" red" if r["Deaths"]>0 else ""}">{r["Deaths"]}</td></tr>' for r in by_type)}
    </table>
  </div>
</div>

<p class="footer">Generated by yokusto &mdash; help.kusto.windows.net / Samples / StormEvents</p>

<script>
const dOpts = {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#ccc' }} }} }}, scales: {{ x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#222' }} }}, y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#222' }} }} }} }};

// Monthly dual-axis
new Chart(document.getElementById('monthlyChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(month_labels)},
    datasets: [
      {{ label: 'Events', data: {json.dumps(month_events)}, backgroundColor: 'rgba(66,165,245,0.7)', yAxisID: 'y', order: 2 }},
      {{ label: 'Damage ($M)', data: {json.dumps([round(d/1e6,1) for d in month_damage])}, type: 'line', borderColor: '#ffa726', backgroundColor: 'rgba(255,167,38,0.1)', yAxisID: 'y1', tension: 0.3, order: 1 }},
      {{ label: 'Deaths', data: {json.dumps(month_deaths)}, type: 'line', borderColor: '#ff6b6b', backgroundColor: 'transparent', yAxisID: 'y1', tension: 0.3, borderDash: [5,3], order: 0 }}
    ]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#ccc' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#222' }} }},
      y: {{ position: 'left', ticks: {{ color: '#42a5f5' }}, grid: {{ color: '#222' }}, title: {{ display: true, text: 'Events', color: '#42a5f5' }} }},
      y1: {{ position: 'right', ticks: {{ color: '#ffa726' }}, grid: {{ drawOnChartArea: false }}, title: {{ display: true, text: 'Damage ($M) / Deaths', color: '#ffa726' }} }}
    }}
  }}
}});

// Event types by damage
new Chart(document.getElementById('typeChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(type_labels)},
    datasets: [{{ label: 'Total Damage ($M)', data: {json.dumps([round(d/1e6,1) for d in type_damage])}, backgroundColor: {json.dumps(['rgba(255,107,107,0.8)' if d>0 else 'rgba(255,167,38,0.8)' for d in type_deaths])} }}]
  }},
  options: {{ indexAxis: 'y', responsive: true, plugins: {{ legend: {{ display: false }} }},
    scales: {{ x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#222' }} }}, y: {{ ticks: {{ color: '#ccc', font: {{ size: 11 }} }}, grid: {{ color: '#222' }} }} }}
  }}
}});

// States stacked
new Chart(document.getElementById('stateChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(state_labels)},
    datasets: [
      {{ label: 'Property Damage ($M)', data: {json.dumps([round(d/1e6,1) for d in state_prop])}, backgroundColor: 'rgba(66,165,245,0.8)' }},
      {{ label: 'Crop Damage ($M)', data: {json.dumps([round(d/1e6,1) for d in state_crop])}, backgroundColor: 'rgba(102,187,106,0.8)' }}
    ]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#ccc' }} }} }},
    scales: {{ x: {{ stacked: true, ticks: {{ color: '#888', maxRotation: 45 }}, grid: {{ color: '#222' }} }}, y: {{ stacked: true, ticks: {{ color: '#888' }}, grid: {{ color: '#222' }} }} }}
  }}
}});

// Deadliest types
new Chart(document.getElementById('deadChart'), {{
  type: 'doughnut',
  data: {{
    labels: {json.dumps(dead_labels)},
    datasets: [{{ data: {json.dumps(dead_deaths)}, backgroundColor: ['#ff6b6b','#ff8a80','#ffa726','#ffcc80','#ab47bc','#ce93d8','#42a5f5','#90caf9','#66bb6a','#a5d6a7'] }}]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ position: 'right', labels: {{ color: '#ccc', font: {{ size: 11 }} }} }} }} }}
}});
</script>
</body></html>"""

with open("storm_dashboard.html", "w", encoding="utf-8") as f:
    f.write(storm_html)
print("  ✓ storm_dashboard.html")

# ═══════════════════════════════════════════════════════════════
# DASHBOARD 2: Contoso Sales — Revenue Analytics
# ═══════════════════════════════════════════════════════════════
print()
print("━" * 60)
print("DASHBOARD 2: Contoso Sales Revenue Analytics")
print("━" * 60)

print("  Querying overview...")
sales_ov = query("ContosoSales", """
SalesTable
| summarize Revenue=sum(SalesAmount), Cost=sum(TotalCost), Txns=count(), Customers=dcount(CustomerKey)
""")[0]
margin = (sales_ov['Revenue'] - sales_ov['Cost']) / sales_ov['Revenue'] * 100
print(f"  Revenue: {fmt(sales_ov['Revenue'])}, Cost: {fmt(sales_ov['Cost'])}, Margin: {margin:.1f}%, Txns: {fmtN(sales_ov['Txns'])}")

print("  Querying monthly trend...")
sales_monthly = query("ContosoSales", """
SalesTable
| summarize Revenue=sum(SalesAmount), Cost=sum(TotalCost), Txns=count()
  by Month=startofmonth(DateKey)
| order by Month asc
""")

print("  Querying top 10 countries...")
sales_country = query("ContosoSales", """
SalesTable
| summarize Revenue=sum(SalesAmount), Cost=sum(TotalCost), Txns=count()
  by Country
| top 10 by Revenue desc
""")

print("  Querying product categories...")
sales_cat = query("ContosoSales", """
SalesTable
| lookup (Products | project ProductKey, ProductCategoryName) on ProductKey
| summarize Revenue=sum(SalesAmount), Cost=sum(TotalCost), Txns=count()
  by ProductCategoryName
| order by Revenue desc
""")

print("  Querying top 15 cities...")
sales_city = query("ContosoSales", """
SalesTable
| summarize Revenue=sum(SalesAmount), Txns=count()
  by City, Country
| top 15 by Revenue desc
""")

print("  Querying gender/education breakdown...")
sales_demo = query("ContosoSales", """
SalesTable
| summarize Revenue=sum(SalesAmount) by Gender
""")

sales_edu = query("ContosoSales", """
SalesTable
| summarize Revenue=sum(SalesAmount) by Education
| order by Revenue desc
""")

# Build Dashboard 2 HTML
sm_labels = [str(r['Month'])[:7] for r in sales_monthly]
sm_rev = [round(r['Revenue']/1e6, 2) for r in sales_monthly]
sm_cost = [round(r['Cost']/1e6, 2) for r in sales_monthly]
sm_margin = [round((r['Revenue']-r['Cost'])/r['Revenue']*100, 1) if r['Revenue'] else 0 for r in sales_monthly]

sc_labels = [r['Country'] for r in sales_country]
sc_rev = [round(r['Revenue']/1e6, 2) for r in sales_country]

scat_labels = [r['ProductCategoryName'] or 'Unknown' for r in sales_cat]
scat_rev = [round(r['Revenue']/1e6, 2) for r in sales_cat]
scat_cost = [round(r['Cost']/1e6, 2) for r in sales_cat]

sdemo_labels = [r['Gender'] for r in sales_demo]
sdemo_rev = [round(r['Revenue']/1e6, 2) for r in sales_demo]

sedu_labels = [r['Education'] for r in sales_edu]
sedu_rev = [round(r['Revenue']/1e6, 2) for r in sales_edu]

sales_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>yokusto — Contoso Sales Revenue Analytics</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0a1628; color: #e0e0e0; padding: 24px; }}
  h1 {{ text-align: center; font-size: 28px; margin-bottom: 6px; background: linear-gradient(135deg, #42a5f5, #66bb6a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .subtitle {{ text-align: center; color: #888; font-size: 14px; margin-bottom: 24px; }}
  .kpi-row {{ display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin-bottom: 28px; }}
  .kpi {{ background: linear-gradient(135deg, #0d2137, #132d4f); border-radius: 12px; padding: 20px 28px; min-width: 170px; text-align: center; border: 1px solid #1e3a5f; }}
  .kpi .value {{ font-size: 32px; font-weight: 800; }}
  .kpi .label {{ font-size: 12px; color: #aaa; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }}
  .kpi.blue .value {{ color: #42a5f5; }}
  .kpi.green .value {{ color: #66bb6a; }}
  .kpi.orange .value {{ color: #ffa726; }}
  .kpi.purple .value {{ color: #ab47bc; }}
  .kpi.cyan .value {{ color: #26c6da; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
  .card {{ background: #0f1d30; border-radius: 12px; padding: 20px; border: 1px solid #1e3a5f; }}
  .card h3 {{ font-size: 15px; color: #ccc; margin-bottom: 12px; }}
  .full {{ grid-column: 1 / -1; }}
  canvas {{ max-height: 320px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 10px; border-bottom: 2px solid #1e3a5f; color: #aaa; font-weight: 600; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #162a42; }}
  tr:hover {{ background: #132d4f; }}
  .right {{ text-align: right; }}
  .green {{ color: #66bb6a; }}
  .footer {{ text-align: center; color: #555; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>
<h1>Contoso Global Sales Analytics</h1>
<p class="subtitle">3.8M transactions across {len(sc_labels)} countries &mdash; Full product catalog</p>

<div class="kpi-row">
  <div class="kpi blue"><div class="value">{fmt(sales_ov['Revenue'])}</div><div class="label">Total Revenue</div></div>
  <div class="kpi orange"><div class="value">{fmt(sales_ov['Cost'])}</div><div class="label">Total Cost</div></div>
  <div class="kpi green"><div class="value">{margin:.1f}%</div><div class="label">Gross Margin</div></div>
  <div class="kpi purple"><div class="value">{fmtN(sales_ov['Txns'])}</div><div class="label">Transactions</div></div>
  <div class="kpi cyan"><div class="value">{fmtN(sales_ov['Customers'])}</div><div class="label">Customers</div></div>
</div>

<div class="grid">
  <div class="card full">
    <h3>Monthly Revenue &amp; Cost Trend</h3>
    <canvas id="monthlyChart"></canvas>
  </div>
  <div class="card">
    <h3>Revenue by Country (Top 10)</h3>
    <canvas id="countryChart"></canvas>
  </div>
  <div class="card">
    <h3>Revenue vs Cost by Product Category</h3>
    <canvas id="catChart"></canvas>
  </div>
  <div class="card">
    <h3>Revenue by Gender</h3>
    <canvas id="genderChart"></canvas>
  </div>
  <div class="card">
    <h3>Revenue by Education Level</h3>
    <canvas id="eduChart"></canvas>
  </div>
  <div class="card full">
    <h3>Top 15 Cities by Revenue</h3>
    <table>
      <tr><th>City</th><th>Country</th><th class="right">Revenue</th><th class="right">Transactions</th></tr>
      {"".join(f'<tr><td>{r["City"]}</td><td>{r["Country"]}</td><td class="right">{fmt(r["Revenue"])}</td><td class="right">{r["Txns"]:,}</td></tr>' for r in sales_city)}
    </table>
  </div>
</div>

<p class="footer">Generated by yokusto &mdash; help.kusto.windows.net / ContosoSales / SalesTable</p>

<script>
// Monthly trend with margin line
new Chart(document.getElementById('monthlyChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(sm_labels)},
    datasets: [
      {{ label: 'Revenue ($M)', data: {json.dumps(sm_rev)}, backgroundColor: 'rgba(66,165,245,0.7)', yAxisID: 'y' }},
      {{ label: 'Cost ($M)', data: {json.dumps(sm_cost)}, backgroundColor: 'rgba(255,167,38,0.5)', yAxisID: 'y' }},
      {{ label: 'Margin %', data: {json.dumps(sm_margin)}, type: 'line', borderColor: '#66bb6a', backgroundColor: 'transparent', yAxisID: 'y1', tension: 0.3 }}
    ]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#ccc' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#162a42' }} }},
      y: {{ position: 'left', ticks: {{ color: '#42a5f5' }}, grid: {{ color: '#162a42' }}, title: {{ display: true, text: '$ Millions', color: '#42a5f5' }} }},
      y1: {{ position: 'right', ticks: {{ color: '#66bb6a' }}, grid: {{ drawOnChartArea: false }}, title: {{ display: true, text: 'Margin %', color: '#66bb6a' }}, min: 0, max: 100 }}
    }}
  }}
}});

// Country bar
new Chart(document.getElementById('countryChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(sc_labels)},
    datasets: [{{ label: 'Revenue ($M)', data: {json.dumps(sc_rev)}, backgroundColor: ['#42a5f5','#66bb6a','#ffa726','#ab47bc','#26c6da','#ef5350','#78909c','#ffca28','#8d6e63','#ec407a'] }}]
  }},
  options: {{ indexAxis: 'y', responsive: true, plugins: {{ legend: {{ display: false }} }},
    scales: {{ x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#162a42' }} }}, y: {{ ticks: {{ color: '#ccc', font: {{ size: 11 }} }}, grid: {{ color: '#162a42' }} }} }}
  }}
}});

// Category grouped bar
new Chart(document.getElementById('catChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(scat_labels)},
    datasets: [
      {{ label: 'Revenue ($M)', data: {json.dumps(scat_rev)}, backgroundColor: 'rgba(66,165,245,0.8)' }},
      {{ label: 'Cost ($M)', data: {json.dumps(scat_cost)}, backgroundColor: 'rgba(255,167,38,0.6)' }}
    ]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#ccc' }} }} }},
    scales: {{ x: {{ ticks: {{ color: '#888', maxRotation: 45 }}, grid: {{ color: '#162a42' }} }}, y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#162a42' }} }} }}
  }}
}});

// Gender doughnut
new Chart(document.getElementById('genderChart'), {{
  type: 'doughnut',
  data: {{
    labels: {json.dumps(sdemo_labels)},
    datasets: [{{ data: {json.dumps(sdemo_rev)}, backgroundColor: ['#42a5f5','#ec407a','#78909c'] }}]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#ccc' }} }} }} }}
}});

// Education bar
new Chart(document.getElementById('eduChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(sedu_labels)},
    datasets: [{{ label: 'Revenue ($M)', data: {json.dumps(sedu_rev)}, backgroundColor: ['#ab47bc','#7e57c2','#5c6bc0','#42a5f5','#26c6da'] }}]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }},
    scales: {{ x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#162a42' }} }}, y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#162a42' }} }} }}
  }}
}});
</script>
</body></html>"""

with open("sales_dashboard.html", "w", encoding="utf-8") as f:
    f.write(sales_html)
print("  ✓ sales_dashboard.html")

# ═══════════════════════════════════════════════════════════════
# DASHBOARD 3: Storm Seasons — When & Where Storms Strike
# ═══════════════════════════════════════════════════════════════
print()
print("━" * 60)
print("DASHBOARD 3: Storm Seasons — When & Where Storms Strike")
print("━" * 60)

print("  Querying monthly × event type heatmap data...")
heat = query("Samples", """
StormEvents
| summarize Events=count() by MonthNum=monthofyear(StartTime), EventType
| join kind=inner (
    StormEvents | summarize TotalEvents=count() by EventType | top 10 by TotalEvents desc
  ) on EventType
| project MonthNum, EventType, Events
| order by EventType asc, MonthNum asc
""")

print("  Querying hourly distribution...")
hourly = query("Samples", """
StormEvents
| summarize Events=count() by Hour=hourofday(StartTime)
| order by Hour asc
""")

print("  Querying storm duration stats...")
duration = query("Samples", """
StormEvents
| extend DurationHrs = datetime_diff('hour', EndTime, StartTime)
| where DurationHrs >= 0 and DurationHrs <= 720
| summarize AvgDurationHrs=round(avg(DurationHrs),1), MaxDurationHrs=max(DurationHrs), Events=count()
  by EventType
| top 12 by AvgDurationHrs desc
""")

print("  Querying seasonal summary...")
seasonal = query("Samples", """
StormEvents
| extend Season=case(
    monthofyear(StartTime) in (3,4,5), "Spring",
    monthofyear(StartTime) in (6,7,8), "Summer",
    monthofyear(StartTime) in (9,10,11), "Fall",
    "Winter")
| summarize Events=count(), Damage=sum(DamageProperty+DamageCrops), Deaths=sum(DeathsDirect+DeathsIndirect) by Season
| order by Events desc
""")

print("  Querying top 10 state×month combinations...")
state_month = query("Samples", """
StormEvents
| summarize Events=count(), Damage=sum(DamageProperty+DamageCrops)
  by State, MonthName=format_datetime(StartTime, "MMM")
| top 20 by Events desc
""")

# Build heatmap-like data: pivot EventType × Month
heat_types = sorted(set(r['EventType'] for r in heat))
heat_data = {}
for r in heat:
    heat_data[(r['EventType'], r['MonthNum'])] = r['Events']

month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

# For heatmap simulation, use grouped bar per month for top types
heat_datasets = []
colors = ['#ff6b6b','#ffa726','#ffee58','#66bb6a','#42a5f5','#ab47bc','#26c6da','#ec407a','#78909c','#8d6e63']
for i, et in enumerate(heat_types):
    heat_datasets.append({
        'label': et,
        'data': [heat_data.get((et, m+1), 0) for m in range(12)],
        'backgroundColor': colors[i % len(colors)]
    })

hourly_labels = [f"{h:02d}:00" for h in range(24)]
hourly_events = [0]*24
for r in hourly:
    hourly_events[r['Hour']] = r['Events']

dur_labels = [r['EventType'] for r in duration]
dur_avg = [r['AvgDurationHrs'] for r in duration]
dur_events = [r['Events'] for r in duration]

# Seasonal doughnut
season_order = ['Spring','Summer','Fall','Winter']
season_map = {r['Season']: r for r in seasonal}
season_events = [season_map.get(s, {}).get('Events', 0) for s in season_order]
season_damage = [season_map.get(s, {}).get('Damage', 0) for s in season_order]
season_deaths = [season_map.get(s, {}).get('Deaths', 0) for s in season_order]

season3_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>yokusto — Storm Seasons: When &amp; Where Storms Strike</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #e0e0e0; padding: 24px; }}
  h1 {{ text-align: center; font-size: 28px; margin-bottom: 6px; background: linear-gradient(135deg, #26c6da, #ab47bc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .subtitle {{ text-align: center; color: #888; font-size: 14px; margin-bottom: 24px; }}
  .kpi-row {{ display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin-bottom: 28px; }}
  .kpi {{ background: linear-gradient(135deg, #161b22, #1c2333); border-radius: 12px; padding: 18px 24px; min-width: 140px; text-align: center; border: 1px solid #30363d; }}
  .kpi .value {{ font-size: 28px; font-weight: 800; }}
  .kpi .label {{ font-size: 11px; color: #aaa; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }}
  .kpi .sub {{ font-size: 11px; color: #666; }}
  .spring .value {{ color: #66bb6a; }}
  .summer .value {{ color: #ffa726; }}
  .fall .value {{ color: #ef5350; }}
  .winter .value {{ color: #42a5f5; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
  .card {{ background: #161b22; border-radius: 12px; padding: 20px; border: 1px solid #30363d; }}
  .card h3 {{ font-size: 15px; color: #ccc; margin-bottom: 12px; }}
  .full {{ grid-column: 1 / -1; }}
  canvas {{ max-height: 340px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 10px; border-bottom: 2px solid #30363d; color: #aaa; font-weight: 600; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #21262d; }}
  tr:hover {{ background: #1c2333; }}
  .right {{ text-align: right; }}
  .footer {{ text-align: center; color: #555; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>
<h1>Storm Seasons: When &amp; Where Storms Strike</h1>
<p class="subtitle">Temporal patterns of 59,066 storm events &mdash; Full Year 2007</p>

<div class="kpi-row">
  <div class="kpi spring"><div class="value">{season_events[0]:,}</div><div class="label">Spring</div><div class="sub">{fmt(season_damage[0])} damage</div></div>
  <div class="kpi summer"><div class="value">{season_events[1]:,}</div><div class="label">Summer</div><div class="sub">{fmt(season_damage[1])} damage</div></div>
  <div class="kpi fall"><div class="value">{season_events[2]:,}</div><div class="label">Fall</div><div class="sub">{fmt(season_damage[2])} damage</div></div>
  <div class="kpi winter"><div class="value">{season_events[3]:,}</div><div class="label">Winter</div><div class="sub">{fmt(season_damage[3])} damage</div></div>
</div>

<div class="grid">
  <div class="card full">
    <h3>Top 10 Storm Types by Month (Stacked)</h3>
    <canvas id="heatChart"></canvas>
  </div>
  <div class="card">
    <h3>Storm Activity by Hour of Day</h3>
    <canvas id="hourlyChart"></canvas>
  </div>
  <div class="card">
    <h3>Seasonal Split &mdash; Events vs Damage</h3>
    <canvas id="seasonChart"></canvas>
  </div>
  <div class="card full">
    <h3>Average Storm Duration by Type (hours)</h3>
    <canvas id="durChart"></canvas>
  </div>
  <div class="card full">
    <h3>Busiest State &times; Month Combinations</h3>
    <table>
      <tr><th>State</th><th>Month</th><th class="right">Events</th><th class="right">Damage ($)</th></tr>
      {"".join(f'<tr><td>{r["State"]}</td><td>{r["MonthName"]}</td><td class="right">{r["Events"]:,}</td><td class="right">{fmt(r["Damage"])}</td></tr>' for r in state_month)}
    </table>
  </div>
</div>

<p class="footer">Generated by yokusto &mdash; help.kusto.windows.net / Samples / StormEvents</p>

<script>
// Stacked bar: storm types by month
new Chart(document.getElementById('heatChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(month_names)},
    datasets: {json.dumps(heat_datasets)}
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#ccc', font: {{ size: 10 }} }} }} }},
    scales: {{
      x: {{ stacked: true, ticks: {{ color: '#888' }}, grid: {{ color: '#21262d' }} }},
      y: {{ stacked: true, ticks: {{ color: '#888' }}, grid: {{ color: '#21262d' }}, title: {{ display: true, text: 'Events', color: '#888' }} }}
    }}
  }}
}});

// Hourly polar area
new Chart(document.getElementById('hourlyChart'), {{
  type: 'polarArea',
  data: {{
    labels: {json.dumps(hourly_labels)},
    datasets: [{{ data: {json.dumps(hourly_events)}, backgroundColor: {json.dumps([f"hsla({int(h/24*360)}, 70%, 55%, 0.7)" for h in range(24)])} }}]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }},
    scales: {{ r: {{ ticks: {{ color: '#888', backdropColor: 'transparent' }}, grid: {{ color: '#21262d' }} }} }}
  }}
}});

// Seasonal doughnut x2
new Chart(document.getElementById('seasonChart'), {{
  type: 'doughnut',
  data: {{
    labels: {json.dumps(season_order)},
    datasets: [
      {{ label: 'Events', data: {json.dumps(season_events)}, backgroundColor: ['#66bb6a','#ffa726','#ef5350','#42a5f5'] }},
    ]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#ccc' }} }} }} }}
}});

// Duration horizontal bar
new Chart(document.getElementById('durChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(dur_labels)},
    datasets: [{{ label: 'Avg Duration (hrs)', data: {json.dumps(dur_avg)}, backgroundColor: 'rgba(38,198,218,0.7)' }}]
  }},
  options: {{ indexAxis: 'y', responsive: true, plugins: {{ legend: {{ display: false }} }},
    scales: {{ x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#21262d' }}, title: {{ display: true, text: 'Hours', color: '#888' }} }}, y: {{ ticks: {{ color: '#ccc', font: {{ size: 11 }} }}, grid: {{ color: '#21262d' }} }} }}
  }}
}});
</script>
</body></html>"""

with open("seasons_dashboard.html", "w", encoding="utf-8") as f:
    f.write(season3_html)
print("  ✓ seasons_dashboard.html")

print()
print("━" * 60)
print("All 3 dashboards generated!")
print("  1. storm_dashboard.html    — Damage & Destruction")
print("  2. sales_dashboard.html    — Contoso Revenue Analytics")
print("  3. seasons_dashboard.html  — When & Where Storms Strike")
print("━" * 60)
