# Demo: Investigate Mode

This project demonstrates **yokusto's Investigate mode** — autonomous, evidence-based data exploration that tests a hypothesis with multiple dashboards.

## Hypothesis

> **"Flood events cause disproportionately more property damage per event than any other storm type, and this pattern is driven by geographic hotspots."**

## Verdict: PARTIALLY SUPPORTED

Floods are **2.2× more damaging per event** than the average storm ($406K vs $183K) — but they are **not the most destructive per event** (wildfires are 28× higher). The damage is **highly concentrated**: 53% of flood losses originate from just 3 states.

## Dashboards

| # | Dashboard | Sub-question | Verdict |
|---|-----------|-------------|---------|
| 1 | [hypothesis_01_ranking.html](hypothesis_01_ranking.html) | Where do floods rank by total damage? | PARTIALLY SUPPORTED |
| 2 | [hypothesis_02_per_event.html](hypothesis_02_per_event.html) | Is per-event flood damage disproportionate? | SUPPORTED |
| 3 | [hypothesis_03_geographic.html](hypothesis_03_geographic.html) | Are there geographic hotspots? | SUPPORTED |
| **Σ** | [**hypothesis_summary.html**](hypothesis_summary.html) | **Executive summary + overall verdict** | **PARTIALLY SUPPORTED** |

## Key Findings

- **Ranking**: Floods rank 6th–7th by total damage individually, but combined (Flood + Flash Flood = $2.2B) they rival #1
- **Per-event**: $406K/event for floods vs. $183K average (2.2×) — though wildfires hit $5.2M/event
- **Hotspots**: Missouri ($532M), Texas ($336M), Kansas ($268M) = 53% of all flood damage
- **Seasonality**: Jul–Aug accounts for $1.46B (66%) of annual flood damage

## Run It Yourself

```bash
# Prerequisites
pip install azure-kusto-data azure-identity
az login

# Generate dashboards from live data
python run_hypothesis_demo.py
```

This queries the public `help.kusto.windows.net` / `Samples` / `StormEvents` dataset — no Azure subscription required.

## Suggested Follow-up Hypotheses

1. "Summer flooding is driven by Midwest states — coastal states have a different seasonal profile"
2. "Missouri's outsized 2007 flood damage was caused by 1–2 catastrophic events, not a high baseline"

## Data Source

- **Cluster**: `help.kusto.windows.net`
- **Database**: `Samples`
- **Table**: `StormEvents`
- **Period**: 2007 (59,066 events)
