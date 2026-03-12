"""Gather data for hypothesis-driven storm demo dashboards."""
from azure.identity import AzureCliCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder, ClientRequestProperties
from datetime import timedelta
import json

cred = AzureCliCredential()
kcsb = KustoConnectionStringBuilder.with_azure_token_credential("https://help.kusto.windows.net", cred)
client = KustoClient(kcsb)

def q(kql):
    props = ClientRequestProperties()
    props.set_option("servertimeout", timedelta(minutes=5))
    resp = client.execute_query("Samples", kql, props)
    t = resp.primary_results[0]
    cols = [c.column_name for c in t.columns]
    return [{cols[i]: row[i] for i in range(len(cols))} for row in t]

print("=== Q1: Damage ranking by storm type ===")
r1 = q("""
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
for r in r1:
    print(f"  {r['EventType']:25s} Dmg={r['TotalDamage']:>15,.0f}  Events={r['Events']:>6,}  Deaths={r['Deaths']}")

print("\n=== Q2: Per-event damage normalized ===")
r2 = q("""
StormEvents
| summarize Events=count(), TotalDamage=sum(DamageProperty + DamageCrops) by EventType
| where Events >= 20
| extend PerEventDamage = TotalDamage / Events
| top 10 by PerEventDamage desc
""")
for r in r2:
    print(f"  {r['EventType']:25s} PerEvent={r['PerEventDamage']:>12,.0f}  (n={r['Events']:,})")

print("\n=== Q3: Monthly trends top 4 types ===")
r3 = q("""
let topTypes = StormEvents | summarize D=sum(DamageProperty+DamageCrops) by EventType | top 4 by D | project EventType;
StormEvents
| where EventType in (topTypes)
| summarize Damage=sum(DamageProperty + DamageCrops), Events=count() by Month=startofmonth(StartTime), EventType
| order by Month asc, EventType asc
""")
print(f"  {len(r3)} rows")
for r in r3[:8]:
    print(f"  {str(r['Month'])[:7]} {r['EventType']:20s} Dmg={r['Damage']:>12,.0f}")
print("  ...")

print("\n=== Q4: Flood damage by state (top 15) ===")
r4 = q("""
StormEvents
| where EventType in ('Flood', 'Flash Flood')
| summarize FloodDamage=sum(DamageProperty + DamageCrops), Events=count(), Deaths=sum(DeathsDirect+DeathsIndirect) by State
| top 15 by FloodDamage desc
""")
for r in r4:
    print(f"  {r['State']:20s} FloodDmg={r['FloodDamage']:>12,.0f}  Events={r['Events']:>5,}")

print("\n=== Q5: Flood vs non-flood per-event ===")
r5 = q("""
StormEvents
| extend IsFlood = EventType in ('Flood', 'Flash Flood')
| summarize Events=count(), TotalDamage=sum(DamageProperty+DamageCrops), Deaths=sum(DeathsDirect+DeathsIndirect) by IsFlood
| extend PerEvent = TotalDamage / Events
""")
for r in r5:
    print(f"  IsFlood={r['IsFlood']}  PerEvent={r['PerEvent']:>10,.0f}  Total={r['TotalDamage']:>15,.0f}  Deaths={r['Deaths']}")

print("\n=== Q6: Quarterly flood damage trend ===")
r6 = q("""
StormEvents
| where EventType in ('Flood', 'Flash Flood')
| summarize Damage=sum(DamageProperty+DamageCrops), Events=count(), Deaths=sum(DeathsDirect+DeathsIndirect)
  by Quarter=startofmonth(StartTime)
| order by Quarter asc
""")
for r in r6:
    print(f"  {str(r['Quarter'])[:7]} Dmg={r['Damage']:>12,.0f}  Events={r['Events']:>4,}  Deaths={r['Deaths']}")

print("\n=== Q7: Death rate per event by type (top 10 by deaths) ===")
r7 = q("""
StormEvents
| summarize Events=count(), Deaths=sum(DeathsDirect+DeathsIndirect), Damage=sum(DamageProperty+DamageCrops) by EventType
| where Deaths > 0
| extend DeathRate = round(todouble(Deaths) / Events * 1000, 1)
| top 10 by Deaths desc
""")
for r in r7:
    print(f"  {r['EventType']:25s} Deaths={r['Deaths']:>4}  Events={r['Events']:>6,}  Rate={r['DeathRate']}/1K")

# Dump all data as JSON for dashboard generation
data = {
    "q1_damage_ranking": r1,
    "q2_per_event": r2,
    "q3_monthly_trends": r3,
    "q4_flood_by_state": r4,
    "q5_flood_vs_other": r5,
    "q6_quarterly_flood": r6,
    "q7_death_rate": r7,
}

# Convert datetimes to strings
import datetime
def serialize(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return str(obj)

with open("_hypothesis_data.json", "w") as f:
    json.dump(data, f, indent=2, default=serialize)
print("\nData saved to _hypothesis_data.json")
