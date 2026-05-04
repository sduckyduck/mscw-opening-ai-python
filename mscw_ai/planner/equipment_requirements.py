from __future__ import annotations

from typing import Any

from mscw_ai.planner.job_profiles import get_job_profile

STAT_KEYS = ('str', 'dex', 'int', 'luk')
REQ_KEYS = {
    'str': ('reqSTR', 'req_str'),
    'dex': ('reqDEX', 'req_dex'),
    'int': ('reqINT', 'req_int'),
    'luk': ('reqLUK', 'req_luk'),
}
INC_KEYS = {
    'str': ('incSTR', 'str'),
    'dex': ('incDEX', 'dex'),
    'int': ('incINT', 'int'),
    'luk': ('incLUK', 'luk'),
}


def _num(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _stats(item: dict[str, Any]) -> dict[str, Any]:
    raw = item.get('stats')
    return raw if isinstance(raw, dict) else item


def item_req_level(item: dict[str, Any]) -> int:
    s = _stats(item)
    return int(_num(s.get('reqLevel') or s.get('req_level')))


def item_requirements(item: dict[str, Any]) -> dict[str, float]:
    s = _stats(item)
    out: dict[str, float] = {}
    for stat, keys in REQ_KEYS.items():
        out[stat] = max(_num(s.get(key)) for key in keys)
    return out


def item_stat_gains(item: dict[str, Any]) -> dict[str, float]:
    s = _stats(item)
    out: dict[str, float] = {}
    for stat, keys in INC_KEYS.items():
        out[stat] = max(_num(s.get(key)) for key in keys)
    out['accuracy'] = max(_num(s.get('incACC')), _num(s.get('accuracy')))
    out['weapon_attack'] = max(_num(s.get('incPAD')), _num(s.get('weaponAttack')))
    out['magic_attack'] = max(_num(s.get('incMAD')), _num(s.get('magicAttack')))
    return out


def can_equip(item: dict[str, Any], job: str, level: int, stats: dict[str, float]) -> bool:
    if item_req_level(item) > level:
        return False
    reqs = item_requirements(item)
    for stat in STAT_KEYS:
        if stats.get(stat, 0.0) < reqs.get(stat, 0.0):
            return False
    return is_job_compatible(item, job)


def is_job_compatible(item: dict[str, Any], job: str) -> bool:
    profile = get_job_profile(job)
    label = str(item.get('req_job_label') or item.get('job') or 'All')
    if label == 'All' or label == '0':
        return True
    return profile.family.lower() in label.lower()


def future_equipment_pressure(items: list[dict[str, Any]], job: str, level: int, stats: dict[str, float], lookahead: int = 5) -> dict[str, float]:
    pressure = {stat: 0.0 for stat in STAT_KEYS}
    for item in items:
        req_level = item_req_level(item)
        if req_level < level or req_level > level + lookahead:
            continue
        if not is_job_compatible(item, job):
            continue
        reqs = item_requirements(item)
        gains = item_stat_gains(item)
        value = gains.get('accuracy', 0.0) * 3.0 + gains.get('weapon_attack', 0.0) * 8.0 + gains.get('magic_attack', 0.0) * 7.0
        value += sum(max(0.0, gains.get(stat, 0.0)) * 3.0 for stat in STAT_KEYS)
        if value <= 0:
            continue
        for stat in STAT_KEYS:
            gap = max(0.0, reqs.get(stat, 0.0) - stats.get(stat, 0.0))
            if gap > 0:
                pressure[stat] += value / (gap + 1.0)
    return pressure
