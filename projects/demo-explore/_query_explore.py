"""Gather data for query-driven exploration demo dashboards."""
from azure.identity import AzureCliCredential
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder, ClientRequestProperties
from datetime import timedelta
import json, datetime

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

print("=== Seed query: top 10 states by event count ===")
seed = q("StormEvents | summarize EventCount=count() by State | top 10 by EventCount desc")
for r in seed:
    print(f"  {r['State']:20s} Events={r['EventCount']:>6,}")

print("\n=== Q1: What storm types dominate in these top states? ===")
q1 = q("""
let topStates = StormEvents | summarize c=count() by State | top 10 by c | project State;
StormEvents
| where State in (topStates)
| summarize Events=count(), Damage=sum(DamageProperty + DamageCrops) by State, EventType
| top 50 by Events desc
""")
print(f"  {len(q1)} rows")

print("\n=== Q2: Monthly trend for top 10 states ===")
q2 = q("""
let topStates = StormEvents | summarize c=count() by State | top 10 by c | project State;
StormEvents
| where State in (topStates)
| summarize Events=count(), Damage=sum(DamageProperty + DamageCrops) by Month=startofmonth(StartTime), State
| order by Month asc, State asc
""")
print(f"  {len(q2)} rows")

print("\n=== Q3: Damage-to-event ratio by state (all states) ===")
q3 = q("""
StormEvents
| summarize Events=count(), TotalDamage=sum(DamageProperty + DamageCrops),
    Deaths=sum(DeathsDirect + DeathsIndirect) by State
| where Events >= 50
| extend DamagePerEvent = TotalDamage / Events
| top 15 by DamagePerEvent desc
""")
for r in q3:
    print(f"  {r['State']:20s} PerEvent={r['DamagePerEvent']:>12,.0f}  Events={r['Events']:>5,}")

print("\n=== Q4: Hour-of-day pattern for top 10 states ===")
q4 = q("""
let topStates = StormEvents | summarize c=count() by State | top 10 by c | project State;
StormEvents
| where State in (topStates)
| extend Hour = datetime_part("hour", StartTime)
| summarize Events=count() by Hour
| order by Hour asc
""")
for r in q4:
    print(f"  Hour {r['Hour']:>2}: {r['Events']:>5,} events")

print("\n=== Q5: Event type diversity by state ===")
q5 = q("""
StormEvents
| summarize EventTypes=dcount(EventType), Events=count(), Damage=sum(DamageProperty+DamageCrops) by State
| top 15 by Events desc
""")
for r in q5:
    print(f"  {r['State']:20s} Types={r['EventTypes']:>3}  Events={r['Events']:>6,}")

def serialize(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return str(obj)

data = {
    "seed": seed,
    "q1_type_by_state": q1,
    "q2_monthly_trend": q2,
    "q3_damage_ratio": q3,
    "q4_hourly": q4,
    "q5_diversity": q5,
}

with open("_explore_data.json", "w") as f:
    json.dump(data, f, indent=2, default=serialize)
print("\nData saved to _explore_data.json")
