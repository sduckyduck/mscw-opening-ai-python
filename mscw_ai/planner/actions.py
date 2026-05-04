from __future__ import annotations

from mscw_ai.planner.models import ApAction


def ap_actions_for_job(job: str) -> list[ApAction]:
    if job in {'fighter', 'page', 'spearman'}:
        return [
            ApAction(str_add=5),
            ApAction(str_add=4, dex_add=1),
            ApAction(str_add=3, dex_add=2),
            ApAction(str_add=2, dex_add=3),
            ApAction(str_add=1, dex_add=4),
            ApAction(dex_add=5),
        ]
    if job in {'hunter', 'crossbowman'}:
        return [
            ApAction(dex_add=5),
            ApAction(dex_add=4, str_add=1),
            ApAction(dex_add=3, str_add=2),
        ]
    if job in {'fire_poison', 'ice_lightning', 'cleric'}:
        return [
            ApAction(int_add=5),
            ApAction(int_add=4, luk_add=1),
            ApAction(int_add=3, luk_add=2),
        ]
    if job in {'assassin', 'bandit'}:
        return [
            ApAction(luk_add=5),
            ApAction(luk_add=4, dex_add=1),
            ApAction(luk_add=3, dex_add=2),
        ]
    return [ApAction(str_add=5)]


def apply_ap(stats: dict[str, float], action: ApAction) -> dict[str, float]:
    out = dict(stats)
    out['str'] = out.get('str', 0.0) + action.str_add
    out['dex'] = out.get('dex', 0.0) + action.dex_add
    out['int'] = out.get('int', 0.0) + action.int_add
    out['luk'] = out.get('luk', 0.0) + action.luk_add
    return out
