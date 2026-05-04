from __future__ import annotations

import argparse

from mscw_ai.rl.q_learning import train_q_learning
from mscw_ai.sim.environment import OpeningEnvironment
from mscw_ai.utils.io import ensure_dir, read_yaml, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config = read_yaml(args.config)
    paths = config.get('paths', {})
    processed_dir = paths.get('processed_dir', 'data/processed')
    model_dir = ensure_dir(paths.get('model_dir', 'outputs/models'))
    env = OpeningEnvironment(processed_dir, config)
    report = train_q_learning(env, config)
    out = model_dir / 'opening_q_table.json'
    write_json(out, report)
    print(f'Saved RL report to {out}')
    print(f"Best policy: {report['best']['action']['label']}")
    print(f"Reward: {report['best']['result']['reward']}")


if __name__ == '__main__':
    main()
