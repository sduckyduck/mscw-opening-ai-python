from __future__ import annotations

from typing import Any


def build_guide(training_report: dict[str, Any]) -> dict[str, Any]:
    best = training_report['best']
    action = best['action']
    result = best['result']
    segments = []
    for decision in result.get('decisions', []):
        segments.append(
            {
                'level_range': f"{decision['level']}-{decision['level'] + 1}",
                'recommended_map': decision['map_name'],
                'primary_mobs': decision.get('primary_mobs', []),
                'ap_distribution': ap_text(action),
                'sp_priority': sp_text(action),
                'gear_policy': gear_text(action),
                'metrics': {
                    'hit_rate': decision.get('hit_rate'),
                    'exp_per_hour': decision.get('exp_per_hour'),
                    'hours': decision.get('hours'),
                    'potion_cost': decision.get('potion_cost'),
                    'expected_ko': decision.get('expected_ko'),
                },
                'reasoning': reasoning_text(decision),
            }
        )
    return {
        'target': 'new_server_opening',
        'learned_policy': action,
        'summary': {
            'total_hours': result.get('total_hours'),
            'ending_meso': result.get('ending_meso'),
            'potion_cost': result.get('potion_cost'),
            'expected_ko': result.get('expected_ko'),
            'comfort': result.get('comfort'),
            'reward': result.get('reward'),
        },
        'segments': segments,
    }


def ap_text(action: dict[str, Any]) -> str:
    policy = action.get('dex_policy')
    if policy == 'low':
        return 'Keep DEX low; add DEX only when hit rate falls below the threshold, otherwise add primary stat.'
    if policy == 'high':
        return 'Prioritize enough DEX for higher-level mobs, then add primary stat.'
    if policy == 'weapon_req':
        return 'Maintain secondary stat for weapon requirements, then add primary stat.'
    return 'Maintain standard secondary stat for accuracy and equipment requirements; put the rest into primary stat.'


def sp_text(action: dict[str, Any]) -> list[str]:
    policy = action.get('skill_policy')
    if policy == 'accuracy':
        return ['Accuracy skill when hit rate is unstable', 'Main attack skill after hit rate is stable']
    if policy == 'damage':
        return ['Main attack skill first', 'Accuracy or survival skill when simulation flags a bottleneck']
    if policy == 'mp':
        return ['Low-MP or recovery skill first', 'Attack skill when potion pressure is acceptable']
    return ['Balance hit rate, kill speed, and potion cost based on simulation feedback']


def gear_text(action: dict[str, Any]) -> str:
    policy = action.get('gear_policy')
    if policy == 'none':
        return 'Do not buy gear early; save mesos for potions unless the simulation flags a hard bottleneck.'
    if policy == 'drop':
        return 'Prefer dropped gear; switch when it improves hit rate or kill speed enough.'
    if policy == 'craft':
        return 'Use crafted gear when material cost is lower than shop upgrade cost.'
    if policy == 'shop':
        return 'Buy shop gear only when the time saved offsets the meso cost.'
    return 'Use a hybrid of shop, drop, and craft upgrades when the simulation shows positive value.'


def reasoning_text(decision: dict[str, Any]) -> str:
    hit = float(decision.get('hit_rate', 0) or 0)
    ko = float(decision.get('expected_ko', 0) or 0)
    if hit < 0.75:
        return 'Hit rate is below the preferred threshold, so the next step should add accuracy or choose a lower-level map.'
    if ko > 0.15:
        return 'This map is efficient but risky, so compare safer policy variants before recommending it.'
    return 'This segment balances EXP per hour, potion cost, and hit-rate stability better than nearby alternatives.'
