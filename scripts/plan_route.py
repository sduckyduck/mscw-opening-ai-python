from __future__ import annotations

import argparse
from pathlib import Path

from mscw_ai.planner.beam_search import plan_route
from mscw_ai.utils.io import read_json, read_yaml, write_json
from mscw_ai.versioning.rules import load_version_rules, merge_rules_into_config


def load_config(config_path: str, version_path: str | None) -> dict:
    config = read_yaml(config_path)
    selected_version_path = version_path or config.get('version_rules_path')
    if selected_version_path:
        rules = load_version_rules(selected_version_path)
        config = merge_rules_into_config(config, rules)
        print(f'Using version rules: {rules.version_id} - {rules.version_name}')
    return config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/opening_default.yaml')
    parser.add_argument('--version', default=None)
    parser.add_argument('--job', default=None)
    parser.add_argument('--start-level', type=int, default=None)
    parser.add_argument('--target-level', type=int, default=None)
    parser.add_argument('--beam-width', type=int, default=40)
    parser.add_argument('--top-maps', type=int, default=8)
    parser.add_argument('--out', default='outputs/guides/planned_route.json')
    args = parser.parse_args()

    config = load_config(args.config, args.version)
    paths = config.get('paths', {})
    processed_dir = Path(paths.get('processed_dir', 'data/processed'))
    spots = read_json(processed_dir / 'training_spots.json')
    items = read_json(processed_dir / 'items.json')

    job = args.job or config.get('job', 'spearman')
    start_level = args.start_level or int(config.get('start_level', 10))
    target_level = args.target_level or int(config.get('target_level', 50))

    result = plan_route(
        spots=spots,
        items=items,
        config=config,
        job=job,
        start_level=start_level,
        target_level=target_level,
        beam_width=args.beam_width,
        top_maps=args.top_maps,
    )
    result['version_id'] = config.get('version_id')
    result['version_name'] = config.get('version_name')
    write_json(args.out, result)
    print(f"Saved planned route to {args.out}")
    print(f"Job: {result['job']}")
    print(f"Reached level: {result['reached_level']} / {result['target_level']}")
    print(f"Total hours: {result['total_hours']}")
    print(f"Potion cost: {result['total_potion_cost']}")
    print(f"Ending meso: {result['ending_meso']}")
    print(f"Expected deaths: {result['expected_deaths']}")
    for step in result['route'][:8]:
        print(f"Lv{step['level']}: {step['ap']} | {step['sp']} | {step['map']} | hit {step['hit_rate']}")
    if len(result['route']) > 8:
        print('...')


if __name__ == '__main__':
    main()
