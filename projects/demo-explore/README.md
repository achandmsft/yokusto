# Demo: Explore Mode

Start from an existing KQL query and let yokusto explore outward — discovering patterns, suggesting follow-ups, and building a rich dashboard automatically.

## Seed Query

```kql
StormEvents | summarize count() by State | top 10 by count_
```

## What the agent produced

| Dashboard | Description |
|---|---|
| [query_exploration_dashboard.html](query_exploration_dashboard.html) | 5 follow-up analyses from the seed query |

## Key Findings

- **Texas** leads with 4,701 events across 27 storm types — the most diverse state.
- **California** has only 898 events but $3.1M damage per event — 25× the average.
- Storms peak at **5–6 PM** local time; a midnight spike (hour 0) may be a reporting artifact.
- **Summer months** (Jun–Aug) see 3–4× more events than winter.

## Re-run

```bash
cd projects/demo-explore
pip install azure-kusto-data azure-identity
az login
python run_query_exploration.py
```

## Data Source

- **Cluster:** `https://help.kusto.windows.net`
- **Database:** Samples
- **Table:** StormEvents (59K events, 2007)
