from __future__ import annotations

from dataclasses import asdict
from typing import Any

from mscw_ai.sim.environment import EpisodeResult, OpeningEnvironment as BaseOpeningEnvironment, PolicyAction


class OpeningEnvironment(BaseOpeningEnvironment):
    """Safer opening-route environment.

    V2 keeps the original MVP environment but adds hard opening-route constraints:
    - avoid selecting normal routes with extremely low hit rate;
    - fall back to lower-level maps when the current level band is not hittable;
    - make meso estimates conservative until real drop tables are connected.
    """

    def run_policy(self, action: PolicyAction) -> EpisodeResult:
        stats = self._base_stats()
        decisions: list[dict[str, Any]] = []
        total_hours = 0.0
        total_potion = 0.0
        total_gear = 0.0
        total_ko = 0.0
        comfort_values: list[float] = []
        hard_min_hit = float(self.constraints.get('hard_min_hit_rate', 0.55))

        for level in range(self.start_level, self.target_level):
            self._allocate_ap(stats, level, action.dex_policy)
            candidates = self._eligible_spots(level, action.risk_policy)
            estimates = [self._estimate_spot(level, stats, spot, action) for spot in candidates]
            viable = [estimate for estimate in estimates if estimate['hit_rate'] >= hard_min_hit]

            if not viable:
                fallback_spots = [
                    spot for spot in self.spots
                    if max(1, level - 25) <= float(spot.get('avg_level', 1)) <= level
                ]
                fallback_estimates = [self._estimate_spot(level, stats, spot, action) for spot in fallback_spots]
                viable = [estimate for estimate in fallback_estimates if estimate['hit_rate'] >= hard_min_hit]

            if not viable:
                break

            best = max(viable, key=lambda x: x['score'])
            stats['meso'] += best['meso_earned'] - best['potion_cost']
            total_hours += best['hours']
            total_potion += best['potion_cost']
            total_ko += best['expected_ko']
            comfort_values.append(best['comfort'])
            decisions.append(best)

        comfort = sum(comfort_values) / len(comfort_values) if comfort_values else 0.0
        reward = self._reward(total_hours, stats['meso'], total_potion, total_gear, total_ko, comfort, decisions)
        if len(decisions) < max(0, self.target_level - self.start_level):
            missing_levels = max(0, self.target_level - self.start_level - len(decisions))
            reward -= missing_levels * 500.0

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

    def _estimate_spot(self, level: int, stats: dict[str, float], spot: dict[str, Any], action: PolicyAction) -> dict[str, Any]:
        estimate = super()._estimate_spot(level, stats, spot, action)
        estimate['meso_earned'] = round(float(estimate.get('meso_earned', 0.0)) * 0.25, 1)
        hit = float(estimate.get('hit_rate', 0.0))
        if hit < 0.55:
            estimate['score'] = float(estimate.get('score', 0.0)) - 1_000_000.0
        elif hit < 0.75:
            estimate['score'] = float(estimate.get('score', 0.0)) - 120_000.0
        return estimate

    def _reward(self, hours: float, meso: float, potion: float, gear: float, ko: float, comfort: float, decisions: list[dict[str, Any]]) -> float:
        reward = super()._reward(hours, meso, potion, gear, ko, comfort, decisions)
        reward -= sum(1 for decision in decisions if decision['hit_rate'] < 0.75) * 180.0
        reward -= sum(1 for decision in decisions if decision['hit_rate'] < 0.55) * 800.0
        if meso < 0:
            reward -= abs(meso) * 0.004
        return reward
