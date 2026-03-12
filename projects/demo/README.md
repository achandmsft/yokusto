# Demo Project — yokusto Showcase Dashboards

These 3 dashboards were generated entirely by yokusto from a single natural-language prompt each, using the **free public demo cluster** `https://help.kusto.windows.net`. No KQL written by hand.

| Dashboard | Live Preview | Prompt |
|---|---|---|
| US Storm Damage | [storm_dashboard.html](https://achandmsft.github.io/yokusto/projects/demo/storm_dashboard.html) | `@yokusto Show me storm damage by state, event type, and month…` |
| Contoso Sales | [sales_dashboard.html](https://achandmsft.github.io/yokusto/projects/demo/sales_dashboard.html) | `@yokusto Build a sales dashboard from ContosoSales…` |
| Storm Seasons | [seasons_dashboard.html](https://achandmsft.github.io/yokusto/projects/demo/seasons_dashboard.html) | `@yokusto Analyze temporal storm patterns…` |

## Re-generate

```bash
python run_demos.py
```

This runs against `https://help.kusto.windows.net` and recreates all 3 dashboards. Requires `az login` and `pip install azure-kusto-data azure-identity`.

## Delete when ready

This folder exists as a reference. When you're ready to use yokusto for your own data, feel free to delete it:

```bash
rm -rf projects/demo
```

The yokusto agent and all setup files live outside this folder and are unaffected.
