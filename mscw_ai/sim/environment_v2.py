from __future__ import annotations

from dataclasses import asdict
from typing import Any

from mscw_ai.sim.environment import EpisodeResult, OpeningEnvironment as BaseOpeningEnvironment, PolicyAction
from mscw_ai.sim.map_rules import is_training_accessible_map


class OpeningEnvironment(BaseOpeningEnvironment):
    """Safer opening-route environment with hard route replacement filters."""

    def run_policy(self, action: PolicyAction) -> EpisodeResult:
        stats = self._base_stats()
        decisions: list[dict[str, Any]] = []
        total_hours = 0.0
        total_potion = 0.0
        total_gear = 0.0
        total_ko = 0.0
        comfort_values: list[float] = []
        hard_min_hit = float(self.constraints.get('hard_min_hit_rate', 0.55))
        max_same_map_streak = int(self.constraints.get('max_same_map_streak', 8))
        max_over_level = float(self.constraints.get('max_over_level_gap', 12))
        same_map_streak: dict[int, int] = {}

        for level in range(self.start_level, self.target_level):
            self._allocate_ap(stats, level, action.dex_policy)
            candidates = [spot for spot in self._eligible_spots(level, action.risk_policy) if is_training_accessible_map(spot, self.config)]
            estimates = [self._estimate_spot(level, stats, spot, action) for spot in candidates]
            estimates = [self._apply_route_context(e, level, same_map_streak) for e in estimates]
            viable = [estimate for estimate in estimates if estimate['hit_rate'] >= hard_min_hit]
            viable = self._prefer_replacement_routes(viable, level, same_map_streak, max_same_map_streak, max_over_level)

            if not viable:
                fallback_spots = [
                    spot for spot in self.spots
                    if is_training_accessible_map(spot, self.config)
                    and max(1, level - 25) <= float(spot.get('avg_level', 1)) <= level
                ]
                fallback_estimates = [self._estimate_spot(level, stats, spot, action) for spot in fallback_spots]
                fallback_estimates = [self._apply_route_context(e, level, same_map_streak) for e in fallback_estimates]
                viable = [estimate for estimate in fallback_estimates if estimate['hit_rate'] >= hard_min_hit]
                viable = self._prefer_replacement_routes(viable, level, same_map_streak, max_same_map_streak, max_over_level)

            if not viable:
                break

            best = max(viable, key=lambda x: x['score'])
            same_map_streak[int(best['map_id'])] = same_map_streak.get(int(best['map_id']), 0) + 1
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

    def _prefer_replacement_routes(
        self,
        viable: list[dict[str, Any]],
        level: int,
        same_map_streak: dict[int, int],
        max_same_map_streak: int,
        max_over_level: float,
    ) -> list[dict[str, Any]]:
        if not viable:
            return viable
        preferred = []
        for estimate in viable:
            map_id = int(estimate['map_id'])
            avg_mob_level = self._avg_level_for_map(map_id)
            too_tired = same_map_streak.get(map_id, 0) >= max_same_map_streak
            too_low = level - avg_mob_level > max_over_level
            if not too_tired and not too_low:
                preferred.append(estimate)
        return preferred or viable

    def _apply_route_context(self, estimate: dict[str, Any], level: int, same_map_streak: dict[int, int]) -> dict[str, Any]:
        out = dict(estimate)
        map_id = int(out['map_id'])
        streak = same_map_streak.get(map_id, 0)
        avg_mob_level = self._avg_level_for_map(map_id)
        over_level = max(0.0, level - avg_mob_level)

        if streak >= 8:
            out['score'] = float(out['score']) - (streak - 7) * 30_000.0
            out['route_context_note'] = 'same_map_fatigue'

        if over_level >= 10:
            penalty = (over_level - 9.0) * 18_000.0
            out['score'] = float(out['score']) - penalty
            out['low_level_mob_penalty'] = round(penalty, 1)

        return out

    def _avg_level_for_map(self, map_id: int) -> float:
        for spot in self.spots:
            if int(spot.get('map_id', -1)) == map_id:
                return float(spot.get('avg_level', 1))
        return 1.0

    def _reward(self, hours: float, meso: float, potion: float, gear: float, ko: float, comfort: float, decisions: list[dict[str, Any]]) -> float:
        reward = super()._reward(hours, meso, potion, gear, ko, comfort, decisions)
        reward -= sum(1 for decision in decisions if decision['hit_rate'] < 0.75) * 180.0
        reward -= sum(1 for decision in decisions if decision['hit_rate'] < 0.55) * 800.0
        reward -= self._same_map_penalty(decisions)
        if meso < 0:
            reward -= abs(meso) * 0.004
        return reward

    def _same_map_penalty(self, decisions: list[dict[str, Any]]) -> float:
        penalty = 0.0
        current_map = None
        streak = 0
        for decision in decisions:
            map_id = decision.get('map_id')
            if map_id == current_map:
                streak += 1
            else:
                current_map = map_id
                streak = 1
            if streak > 8:
                penalty += (streak - 8) * 120.0
        return penalty
