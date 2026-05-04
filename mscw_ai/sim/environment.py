from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from mscw_ai.sim.accuracy import physical_hit_rate, stat_derived_accuracy
from mscw_ai.sim.exp_table import exp_to_next
from mscw_ai.utils.io import read_json


@dataclass(frozen=True)
class PolicyAction:
    id: str
    label: str
    dex_policy: str
    gear_policy: str
    risk_policy: str
    skill_policy: str


POLICY_ACTIONS = [
    PolicyAction('lowdex_no_buy_safe', '低DEX不买装备保守刷', 'low', 'none', 'conservative', 'mp'),
    PolicyAction('standard_drop_normal', '标准DEX靠掉落普通刷', 'standard', 'drop', 'normal', 'balanced'),
    PolicyAction('standard_shop_normal', '标准DEX商店普通刷', 'standard', 'shop', 'normal', 'balanced'),
    PolicyAction('highacc_shop_greedy', '高命中商店越级刷', 'high', 'shop', 'greedy', 'accuracy'),
    PolicyAction('weaponreq_hybrid_fast', '装备需求混合快刷', 'weapon_req', 'hybrid', 'greedy', 'damage'),
    PolicyAction('standard_craft_stable', '标准DEX锻造稳定刷', 'standard', 'craft', 'normal', 'balanced'),
]


@dataclass
class EpisodeResult:
    action: dict[str, Any]
    total_hours: float
    ending_meso: float
    potion_cost: float
    gear_cost: float
    expected_ko: float
    comfort: float
    reward: float
    decisions: list[dict[str, Any]]


class OpeningEnvironment:
    def __init__(self, processed_dir: str | Path, config: dict[str, Any]):
        self.processed_dir = Path(processed_dir)
        self.config = config
        self.spots = read_json(self.processed_dir / 'training_spots.json')
        self.job = config.get('job', 'spearman')
        self.start_level = int(config.get('start_level', 10))
        self.target_level = int(config.get('target_level', 50))
        self.weights = config.get('reward_weights', {})
        self.constraints = config.get('constraints', {})

    def run_policy(self, action: PolicyAction) -> EpisodeResult:
        stats = self._base_stats()
        decisions: list[dict[str, Any]] = []
        total_hours = 0.0
        total_potion = 0.0
        total_gear = 0.0
        total_ko = 0.0
        comfort_values: list[float] = []

        for level in range(self.start_level, self.target_level):
            self._allocate_ap(stats, level, action.dex_policy)
            candidates = self._eligible_spots(level, action.risk_policy)
            if not candidates:
                continue
            best = max((self._estimate_spot(level, stats, spot, action) for spot in candidates), key=lambda x: x['score'])
            stats['meso'] += best['meso_earned'] - best['potion_cost']
            total_hours += best['hours']
            total_potion += best['potion_cost']
            total_ko += best['expected_ko']
            comfort_values.append(best['comfort'])
            decisions.append(best)

        comfort = sum(comfort_values) / len(comfort_values) if comfort_values else 0.0
        reward = self._reward(total_hours, stats['meso'], total_potion, total_gear, total_ko, comfort, decisions)
        return EpisodeResult(
            action=asdict(action),
            total_hours=round(total_hours, 3),
            ending_meso=round(stats['meso'], 1),
            potion_cost=round(total_potion, 1),
            gear_cost=round(total_gear, 1),
            expected_ko=round(total_ko, 3),
            comfort=round(comfort, 2),
            reward=round(reward, 3),
            decisions=decisions,
        )

    def _base_stats(self) -> dict[str, float]:
        if self.job in {'fighter', 'page', 'spearman'}:
            return {'str': 45.0, 'dex': 25.0, 'int': 4.0, 'luk': 4.0, 'watk': 17.0, 'meso': 0.0}
        if self.job in {'hunter', 'crossbowman'}:
            return {'str': 20.0, 'dex': 46.0, 'int': 4.0, 'luk': 4.0, 'watk': 20.0, 'meso': 0.0}
        if self.job in {'fire_poison', 'ice_lightning', 'cleric'}:
            return {'str': 4.0, 'dex': 4.0, 'int': 52.0, 'luk': 13.0, 'watk': 0.0, 'meso': 0.0}
        return {'str': 4.0, 'dex': 30.0, 'int': 4.0, 'luk': 40.0, 'watk': 20.0, 'meso': 0.0}

    def _allocate_ap(self, stats: dict[str, float], level: int, dex_policy: str) -> None:
        if level <= 10:
            return
        target_dex = level + 5
        if dex_policy == 'low':
            target_dex -= 8
        elif dex_policy == 'high':
            target_dex += 12
        elif dex_policy == 'weapon_req':
            target_dex += 4
        remaining = 5
        need_dex = max(0, target_dex - stats['dex'])
        add_dex = min(remaining, need_dex)
        stats['dex'] += add_dex
        remaining -= add_dex
        stats['str'] += remaining

    def _eligible_spots(self, level: int, risk_policy: str) -> list[dict[str, Any]]:
        if risk_policy == 'conservative':
            hi = level + 3
        elif risk_policy == 'greedy':
            hi = level + int(self.constraints.get('max_map_level_gap', 8))
        else:
            hi = level + 6
        lo = level - 9
        return [s for s in self.spots if lo <= float(s.get('avg_level', 1)) <= hi]

    def _estimate_spot(self, level: int, stats: dict[str, float], spot: dict[str, Any], action: PolicyAction) -> dict[str, Any]:
        acc = stat_derived_accuracy(stats['dex'], stats['luk'])
        hit = physical_hit_rate(level, float(spot['avg_level']), acc, float(spot.get('avg_avoid', 0)))
        level_penalty = 1.0 / (1.0 + max(0.0, float(spot['avg_level']) - level) * 0.08)
        skill_mult = 1.0
        if action.skill_policy == 'damage':
            skill_mult = 1.25
        elif action.skill_policy == 'accuracy':
            acc += 12
            hit = physical_hit_rate(level, float(spot['avg_level']), acc, float(spot.get('avg_avoid', 0)))
        elif action.skill_policy == 'mp':
            skill_mult = 1.08

        damage = (stats['watk'] * 2.6 + stats['str'] * 1.35 + stats['dex'] * 0.35) * hit * level_penalty * skill_mult
        kill_seconds = max(0.65, min(18.0, float(spot['avg_hp']) / max(1.0, damage) + 0.75))
        kills_per_hour = min((3600.0 / kill_seconds), float(spot['total_mob_count']) * 900.0)
        exp_per_hour = kills_per_hour * float(spot['avg_exp'])
        hours = exp_to_next(level) / max(1.0, exp_per_hour)
        death_rate = max(0.0, min(0.35, (float(spot['avg_level']) - level + 5) / 18.0 - acc / 900.0))
        expected_ko = death_rate * hours
        potion_cost = kills_per_hour * hours * death_rate * (1.8 + level * 0.15)
        meso_earned = kills_per_hour * hours * (float(spot['avg_level']) * 2.2 + float(spot['avg_exp']) * 0.45)
        comfort = max(0.0, min(100.0, 100.0 - death_rate * 140.0 - max(0.0, 0.9 - hit) * 60.0 - kill_seconds * 2.0))
        return {
            'level': level,
            'map_id': spot['map_id'],
            'map_name': spot['map_name'],
            'primary_mobs': [m['name'] for m in spot['mobs'][:3]],
            'hit_rate': round(hit, 4),
            'accuracy': acc,
            'hours': round(hours, 4),
            'exp_per_hour': round(exp_per_hour, 1),
            'kills_per_hour': round(kills_per_hour, 1),
            'meso_earned': round(meso_earned, 1),
            'potion_cost': round(potion_cost, 1),
            'expected_ko': round(expected_ko, 4),
            'comfort': round(comfort, 2),
            'score': exp_per_hour - potion_cost * 0.8 - expected_ko * 8000 + comfort * 40,
        }

    def _reward(self, hours: float, meso: float, potion: float, gear: float, ko: float, comfort: float, decisions: list[dict[str, Any]]) -> float:
        w = self.weights
        reward = len(decisions) * float(w.get('completion_per_level', 55.0))
        reward -= hours * float(w.get('time_penalty_per_hour', 18.0))
        reward -= ko * float(w.get('penalty_per_ko', 180.0))
        reward -= potion * float(w.get('potion_cost_weight', 0.00118))
        reward -= gear * float(w.get('gear_cost_weight', 0.00083))
        reward += max(0.0, meso) * 0.00055
        reward += comfort * float(w.get('comfort_bonus', 5.0))
        reward -= sum(1 for d in decisions if d['hit_rate'] < 0.75) * float(w.get('low_hit_penalty', 140.0))
        return reward
