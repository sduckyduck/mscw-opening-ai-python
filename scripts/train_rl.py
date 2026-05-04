from __future__ import annotations

import argparse

from mscw_ai.rl.q_learning import train_q_learning
from mscw_ai.sim.environment_v2 import OpeningEnvironment
from mscw_ai.utils.io import ensure_dir, read_yaml, write_json
from mscw_ai.versioning.rules import load_version_rules, merge_rules_into_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--version', default=None, help='Optional version rules yaml path')
    args = parser.parse_args()
    config = read_yaml(args.config)
    version_path = args.version or config.get('version_rules_path')
    if version_path:
        rules = load_version_rules(version_path)
        config = merge_rules_into_config(config, rules)
        print(f'Using version rules: {rules.version_id} - {rules.version_name}')
    paths = config.get('paths', {})
    processed_dir = paths.get('processed_dir', 'data/processed')
    model_dir = ensure_dir(paths.get('model_dir', 'outputs/models'))
    env = OpeningEnvironment(processed_dir, config)
    report = train_q_learning(env, config)
    report['version_id'] = config.get('version_id')
    report['version_name'] = config.get('version_name')
    out = model_dir / 'opening_q_table.json'
    write_json(out, report)
    print(f'Saved RL report to {out}')
    print(f"Best policy: {report['best']['action']['label']}")
    print(f"Reward: {report['best']['result']['reward']}")


if __name__ == '__main__':
    main()
