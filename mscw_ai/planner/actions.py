from __future__ import annotations

from itertools import product

from mscw_ai.planner.job_profiles import get_job_profile
from mscw_ai.planner.models import ApAction


def ap_actions_for_job(job: str) -> list[ApAction]:
    profile = get_job_profile(job)
    stats = [profile.primary_stat, *profile.secondary_stats]
    stats = list(dict.fromkeys(stats))
    actions: list[ApAction] = []

    def make_action(values: dict[str, int]) -> ApAction:
        return ApAction(
            str_add=values.get('str', 0),
            dex_add=values.get('dex', 0),
            int_add=values.get('int', 0),
            luk_add=values.get('luk', 0),
        )

    if len(stats) == 1:
        return [make_action({stats[0]: 5})]

    primary = stats[0]
    secondary = stats[1]
    for secondary_points in range(0, 6):
        actions.append(make_action({primary: 5 - secondary_points, secondary: secondary_points}))

    if len(stats) >= 3:
        third = stats[2]
        for second_points, third_points in product(range(0, 4), range(0, 3)):
            primary_points = 5 - second_points - third_points
            if primary_points < 0:
                continue
            actions.append(make_action({primary: primary_points, secondary: second_points, third: third_points}))

    unique = {action.label: action for action in actions}
    return list(unique.values())


def apply_ap(stats: dict[str, float], action: ApAction) -> dict[str, float]:
    out = dict(stats)
    out['str'] = out.get('str', 0.0) + action.str_add
    out['dex'] = out.get('dex', 0.0) + action.dex_add
    out['int'] = out.get('int', 0.0) + action.int_add
    out['luk'] = out.get('luk', 0.0) + action.luk_add
    return out
