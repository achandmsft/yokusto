# yokusto — Talk to Kusto Clusters in Plain English

A VS Code Copilot agent that turns natural-language questions into Kusto (Azure Data Explorer) dashboards. No KQL knowledge required.

Three modes depending on what you need:

| Mode | You have… | You get… |
|---|---|---|
| **Visualize** | A question about your data | A dashboard |
| **Explore** | An existing KQL query | Follow-up analyses + deeper insights |
| **Investigate** | A hypothesis to prove or disprove | Evidence dashboards + a verdict |

---

## Quick Start

```bash
git clone https://github.com/achandmsft/yokusto.git && cd yokusto
pip install azure-kusto-data azure-identity
az login --scope "https://kusto.kusto.windows.net/.default"
```

Open in VS Code → type `@yokusto` in Copilot Chat → go.

<details>
<summary>Dev Container / Codespaces setup</summary>

**Codespaces:** Click **Code → Codespaces → New codespace**. Wait ~2 min, then `az login --use-device-code --scope "https://kusto.kusto.windows.net/.default"`.

**Local Docker:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) + [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) → `Ctrl+Shift+P` → "Reopen in Container" → `az login`.

</details>

<details>
<summary>Prerequisites</summary>

| Requirement | Link |
|---|---|
| VS Code | [Download](https://code.visualstudio.com/) |
| GitHub Copilot | [Extension](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot) (Free, Pro, or Enterprise) |
| Python 3.10+ | [Download](https://www.python.org/downloads/) |
| Azure CLI | [Install](https://learn.microsoft.com/cli/azure/install-azure-cli) |

</details>

---

## The Three Modes

All examples below use the **free public cluster** `https://help.kusto.windows.net` — replace with your own cluster URL.

### 1. Visualize — ask a question, get a dashboard

Best for: exploring data you haven't seen before, building reports, one-off analysis.

```
@yokusto Show me storm damage by state and event type
from https://help.kusto.windows.net, database Samples, table StormEvents
```

![Storm Dashboard](projects/demo-visualize/images/storm_dashboard_preview.png)

The agent discovers schema, writes KQL, runs it, and builds a self-contained HTML dashboard — KPI cards, charts, tables. One prompt, one dashboard.

📄 [Live demo](https://achandmsft.github.io/yokusto/projects/demo-visualize/storm_dashboard.html) · [Project files](projects/demo-visualize/)

---

### 2. Explore — start from a KQL query, go deeper

Best for: Kusto users who already have a query and want to discover what else the data can tell them.

```
@yokusto Here's a query I use:
StormEvents | summarize count() by State | top 10 by count_
Analyze this and show me what else is interesting
```

![Query Exploration](projects/demo-query-driven/images/query_exploration_preview.png)

The agent runs your seed query, discovers the broader schema, and produces follow-up analyses automatically — then suggests next questions.

📄 [Live demo](https://achandmsft.github.io/yokusto/projects/demo-query-driven/query_exploration_dashboard.html) · [Project files](projects/demo-query-driven/)

---

### 3. Investigate — prove or disprove a hypothesis

Best for: validating a claim with data, building an evidence-based argument, due diligence.

```
@yokusto I think flood events cause disproportionately more damage
per event than other storm types. Prove or disprove this using
https://help.kusto.windows.net, database Samples, table StormEvents
```

![Hypothesis Summary](projects/demo-hypothesis/images/hypothesis_summary_preview.png)

The agent decomposes your claim into sub-questions, gathers evidence for and against, and delivers a verdict across multiple dashboards.

📄 [Live demo](https://achandmsft.github.io/yokusto/projects/demo-hypothesis/hypothesis_summary.html) · [Project files](projects/demo-hypothesis/)

---

## How It Works

Each session creates a self-contained project folder:

```
projects/<project-name>/
├── <topic>_dashboard.html     # Open in any browser — no server needed
├── run_<topic>.py             # Re-runnable Python script
└── <topic>.kql                # Working queries for Kusto Explorer
```

Share the HTML file via email, Teams, or SharePoint. Recipients just open it — no setup.

<details>
<summary>Behind the scenes</summary>

1. Checks Python, packages, and Azure CLI auth
2. Discovers databases, tables, and columns on your cluster
3. Writes and runs a Python script that sends KQL queries via `azure-kusto-data`
4. Generates a self-contained HTML file with Chart.js charts and formatted tables
5. Saves the dashboard, script, and `.kql` file in a project folder

</details>

---

## Team Workflow

<details>
<summary>Version control with a private GitHub repo</summary>

```bash
gh repo create my-yokusto --private --clone --template achandmsft/yokusto
cd my-yokusto
echo "projects/**/*.html" >> .gitignore   # keep dashboards local
```

Dashboard HTML files contain your actual query data. The `.gitignore` rule keeps them local while scripts and KQL files are version-controlled. Share dashboards via Teams/SharePoint instead.

**If you want public dashboards** (non-sensitive data only):

```bash
gh api repos/<you>/my-yokusto/pages -X POST -f build_type=legacy -f source.branch=main -f source.path="/"
```

> GitHub Pages on Free/Pro/Team plans are **always public**, even on private repos.

**Pull upstream updates:**

```bash
git remote add upstream https://github.com/achandmsft/yokusto.git
git remote set-url --push upstream DISABLE
git fetch upstream && git merge upstream/main
```

</details>

---

## Troubleshooting

| Problem | Fix |
|---|---|
| 403 Forbidden | Wrong tenant: `az login --tenant <TENANT_ID> --scope "https://kusto.kusto.windows.net/.default"` |
| ModuleNotFoundError | `pip install azure-kusto-data azure-identity` |
| Agent not visible | Check `.github/agents/yokusto.agent.md` exists, reload VS Code |
| Query timeout | Agent handles this automatically; try a smaller time range if it persists |

---

## Files

```
.github/agents/yokusto.agent.md    # Agent definition (the brain)
.github/prompts/yokusto.prompt.md  # Slash-command entry point
.devcontainer/devcontainer.json    # Dev Container config
projects/
├── demo-visualize/                # Mode 1 demo (safe to delete)
├── demo-query-driven/             # Mode 2 demo (safe to delete)
└── demo-hypothesis/               # Mode 3 demo (safe to delete)
```
