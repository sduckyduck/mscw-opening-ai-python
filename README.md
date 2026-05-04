# MSCW Opening AI Python

Python-first AI training lab for MapleStory Classic World new-server opening routes.

This repository is designed to become the backend brain for your guide/simulator website. The frontend repo can display the result, but this repo handles the heavier work:

- ETL from unpacked game files / WZ-export JSON.
- Fast numerical combat and leveling simulator.
- Accuracy, AP, SP, gear, potion, death-risk, and map-efficiency modeling.
- Reinforcement learning for a single goal: **new-server opening optimal route**.
- Structured JSON guide generation for your guidebook website.

## Core idea

The AI should not optimize vague goals like "comfort" or "fun". It has one target:

> Find the best opening route under new-server / low-resource constraints.

Reward is based on:

- faster leveling;
- fewer deaths;
- lower potion cost;
- lower gear cost;
- avoiding bankruptcy;
- stable hit rate;
- valid AP/SP/equipment constraints;
- efficient map transitions.

## Project layout

```text
mscw-opening-ai-python/
  configs/
    opening_default.yaml
  data/
    raw/          # copied/exported JSON files from game data
    processed/    # normalized parquet/csv/jsonl datasets
    labels/       # hand-labeled route guides or community strategies
  outputs/
    guides/       # generated JSON/Markdown guides
    models/       # learned Q-tables / torch checkpoints
    reports/      # validation reports
  scripts/
    build_dataset.py
    train_rl.py
    generate_guide.py
    validate_guide.py
  mscw_ai/
    etl/
    sim/
    rl/
    guide/
    utils/
```

## Install

```bash
cd mscw-opening-ai-python
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -e .
```

## Copy data from your frontend repo

From your Vite repo:

```bash
# example
xcopy /E /I "D:\冒险岛\mscw-route-ai-simulator\public\data\app_metadata" "D:\冒险岛\mscw-opening-ai-python\data\raw\app_metadata"
```

Expected raw files include:

```text
data/raw/app_metadata/monsters.json
data/raw/app_metadata/maps.json
data/raw/app_metadata/items.json
data/raw/app_metadata/portals.json
```

## Run MVP pipeline

```bash
python scripts/build_dataset.py --source data/raw/app_metadata --out data/processed
python scripts/train_rl.py --config configs/opening_default.yaml
python scripts/generate_guide.py --model outputs/models/opening_q_table.json --out outputs/guides/sample_guide.json
python scripts/validate_guide.py --guide outputs/guides/sample_guide.json --data data/processed
```

## Guide JSON output

```json
{
  "job": "spearman",
  "target": "new_server_opening",
  "segments": [
    {
      "level_range": "10-15",
      "recommended_map": "Damp Forest",
      "primary_mobs": ["Slime", "Octopus"],
      "ap_distribution": "Add DEX only when hit rate falls below threshold; otherwise STR.",
      "sp_priority": ["Precise Strikes if hit rate is low", "Power Strike for kill speed"],
      "gear_policy": "Do not buy expensive gear unless it improves hit-rate or kill-time enough to offset cost.",
      "reasoning": "Stable hit rate and low potion burn make this map better than higher-level alternatives."
    }
  ]
}
```
