from __future__ import annotations

import math
import random
from dataclasses import asdict
from typing import Any

from mscw_ai.sim.environment import OpeningEnvironment, POLICY_ACTIONS

DISABLED_POLICY_IDS = {'highacc_shop_greedy'}


def active_actions() -> list:
    return [action for action in POLICY_ACTIONS if action.id not in DISABLED_POLICY_IDS]


def train_q_learning(env: OpeningEnvironment, config: dict[str, Any]) -> dict[str, Any]:
    training = config.get('training', {})
    episodes = int(training.get('episodes', 500))
    alpha = float(training.get('alpha', 0.22))
    gamma = float(training.get('gamma', 0.9))
    eps_start = float(training.get('epsilon_start', 0.9))
    eps_end = float(training.get('epsilon_end', 0.05))
    seed = int(config.get('seed', 42))
    rng = random.Random(seed)
    actions = active_actions()

    q_values = {action.id: 0.0 for action in actions}
    history = []
    best = None

    for episode in range(1, episodes + 1):
        frac = episode / max(1, episodes)
        epsilon = eps_end + (eps_start - eps_end) * math.exp(-4.5 * frac)
        if rng.random() < epsilon:
            action = rng.choice(actions)
        else:
            action = max(actions, key=lambda a: q_values[a.id])

        result = env.run_policy(action)
        old_q = q_values[action.id]
        next_q = max(q_values.values())
        new_q = old_q + alpha * (result.reward + gamma * next_q - old_q)
        q_values[action.id] = new_q

        row = {
            'episode': episode,
            'epsilon': round(epsilon, 4),
            'action_id': action.id,
            'action_label': action.label,
            'reward': result.reward,
            'q_value': round(new_q, 4),
            'total_hours': result.total_hours,
            'ending_meso': result.ending_meso,
            'potion_cost': result.potion_cost,
            'expected_ko': result.expected_ko,
            'comfort': result.comfort,
        }
        history.append(row)
        if best is None or result.reward > best['result']['reward']:
            best = {'action': asdict(action), 'result': asdict(result)}

    learned_action = max(actions, key=lambda a: q_values[a.id])
    learned_result = env.run_policy(learned_action)
    if best is None or learned_result.reward >= best['result']['reward']:
        best = {'action': asdict(learned_action), 'result': asdict(learned_result)}

    return {
        'algorithm': 'q_learning',
        'episodes': episodes,
        'disabled_policy_ids': sorted(DISABLED_POLICY_IDS),
        'q_values': {a.label: round(q_values[a.id], 4) for a in actions},
        'best': best,
        'history': history,
    }
