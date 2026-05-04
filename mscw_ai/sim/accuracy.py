from __future__ import annotations

import math


def stat_derived_accuracy(dex: float, luk: float) -> int:
    return math.floor(max(0, dex) / 3) + math.floor(max(0, luk) / 6) + 5


def physical_hit_rate(player_level: int, monster_level: float, accuracy: float, monster_avoid: float) -> float:
    if monster_avoid <= 0:
        return 1.0
    if accuracy <= 0:
        return 0.0
    level_gap = max(0.0, monster_level - player_level)
    a = accuracy * 100.0 / ((level_gap + 51.0) * 5.0)
    if a <= 0:
        return 0.0
    f = 0.3 / (1.0 + math.exp((a - monster_avoid) / 12.0))
    roll_min = 0.95 - f
    roll_max = 1.05 + f
    needed = monster_avoid / a
    return max(0.0, min(1.0, (roll_max - needed) / (roll_max - roll_min)))
