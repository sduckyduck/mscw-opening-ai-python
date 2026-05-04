from __future__ import annotations

import argparse
from pathlib import Path

from mscw_ai.rl.q_learning import active_actions
from mscw_ai.sim.environment_v2 import OpeningEnvironment
from mscw_ai.sim.map_rules import is_training_accessible_map
from mscw_ai.utils.io import read_yaml, write_json
from mscw_ai.versioning.rules import load_version_rules, merge_rules_into_config


def choose_action(config: dict, action_id: str):
    for action in active_actions(config):
        if action.id == action_id:
            return action
    return active_actions(config)[0]


def stats_at(env: OpeningEnvironment, action, level: int):
    stats = env._base_stats()
    for lv in range(env.start_level, level + 1):
        env._allocate_ap(stats, lv, action.dex_policy)
    return stats


def inspect_level(env: OpeningEnvironment, action, level: int, top: int):
    hard_min_hit = float(env.constraints.get('hard_min_hit_rate', 0.55))
    stats = stats_at(env, action, level)
    normal = env._eligible_spots(level, action.risk_policy)
    rows = []
    for spot in normal:
        if not is_training_accessible_map(spot, env.config):
            continue
        estimate = env._estimate_spot(level, stats, spot, action)
        rows.append({
            'map_id': spot.get('map_id'),
            'map_name': spot.get('map_name'),
            'avg_level': round(float(spot.get('avg_level', 0)), 2),
            'mobs': [m.get('name') for m in (spot.get('mobs') or [])[:3]],
            'hit_rate': estimate['hit_rate'],
            'accuracy': estimate['accuracy'],
            'hours': estimate['hours'],
            'exp_per_hour': estimate['exp_per_hour'],
            'score': round(float(estimate['score']), 2),
            'usable': estimate['hit_rate'] >= hard_min_hit,
        })
    usable = [row for row in rows if row['usable']]
    return {
        'level': level,
        'stats': stats,
        'candidate_count': len(rows),
        'usable_count': len(usable),
        'top_usable': sorted(usable, key=lambda x: x['score'], reverse=True)[:top],
        'top_all': sorted(rows, key=lambda x: x['score'], reverse=True)[:top],
    }


def load_config(config_path: str, version_path: str | None) -> dict:
    config = read_yaml(config_path)
    selected_version_path = version_path or config.get('version_rules_path')
    if selected_version_path:
        rules = load_version_rules(selected_version_path)
        config = merge_rules_into_config(config, rules)
        print(f'Using version rules: {rules.version_id} - {rules.version_name}')
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/opening_default.yaml')
    parser.add_argument('--version', default=None)
    parser.add_argument('--from-level', type=int, default=41)
    parser.add_argument('--to-level', type=int, default=50)
    parser.add_argument('--action-id', default='standard_drop_normal')
    parser.add_argument('--top', type=int, default=10)
    parser.add_argument('--out', default='outputs/reports/candidate_debug.json')
    args = parser.parse_args()

    config = load_config(args.config, args.version)
    env = OpeningEnvironment(config.get('paths', {}).get('processed_dir', 'data/processed'), config)
    action = choose_action(config, args.action_id)
    report = [inspect_level(env, action, lv, args.top) for lv in range(args.from_level, args.to_level + 1)]
    write_json(Path(args.out), report)
    print(f'Saved {args.out}')
    for item in report:
        print(f"Lv{item['level']}: candidates={item['candidate_count']} usable={item['usable_count']}")
        for row in item['top_usable'][:5]:
            print(f"  {row['map_name']} hit={row['hit_rate']} avgLv={row['avg_level']} score={row['score']}")


if __name__ == '__main__':
    main()
