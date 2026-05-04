from __future__ import annotations

from dataclasses import asdict
from typing import Any

from mscw_ai.planner.actions import ap_actions_for_job, apply_ap
from mscw_ai.planner.equipment_requirements import future_equipment_pressure
from mscw_ai.planner.job_profiles import get_job_profile
from mscw_ai.planner.models import BuildState
from mscw_ai.planner.skills import available_sp_actions, apply_sp, mp_cost_per_attack, skill_accuracy, skill_damage_multiplier
from mscw_ai.sim.accuracy import physical_hit_rate, stat_derived_accuracy
from mscw_ai.sim.exp_table import exp_to_next
from mscw_ai.sim.map_rules import is_training_accessible_map


def initial_state(job: str, start_level: int) -> BuildState:
    if job in {'fighter', 'page', 'spearman'}:
        return BuildState(start_level, job, 45, 25, 4, 4, 450, 100, 0)
    if job in {'hunter', 'crossbowman'}:
        return BuildState(start_level, job, 20, 46, 4, 4, 380, 120, 0)
    if job in {'fire_poison', 'ice_lightning', 'cleric'}:
        return BuildState(start_level, job, 4, 4, 52, 13, 260, 260, 0)
    if job in {'assassin', 'bandit'}:
        return BuildState(start_level, job, 4, 30, 4, 40, 360, 130, 0)
    return BuildState(start_level, job, 35, 25, 4, 4, 400, 100, 0)


def state_stats(state: BuildState) -> dict[str, float]:
    return {'str': state.str_, 'dex': state.dex, 'int': state.int_, 'luk': state.luk}


def estimate_map(state: BuildState, spot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    profile = get_job_profile(state.job)
    stats = state_stats(state)
    base_acc = stat_derived_accuracy(stats['dex'], stats['luk'])
    acc = base_acc + skill_accuracy(state.skills)
    hit = physical_hit_rate(state.level, float(spot.get('avg_level', 1)), acc, float(spot.get('avg_avoid', 0)))

    primary = stats.get(profile.primary_stat, 0.0)
    secondary = sum(stats.get(stat, 0.0) for stat in profile.secondary_stats)
    watk = 17.0 + float(state.gear.get('weapon_attack', 0.0))
    level_penalty = 1.0 / (1.0 + max(0.0, float(spot.get('avg_level', 1)) - state.level) * 0.08)
    damage = (watk * 2.6 + primary * 1.35 + secondary * 0.35) * hit * level_penalty * skill_damage_multiplier(state.skills)
    kill_seconds = max(0.75, min(22.0, float(spot.get('avg_hp', 1)) / max(1.0, damage) + 0.8))
    kills_per_hour = min(3600.0 / kill_seconds, float(spot.get('total_mob_count', 1)) * 850.0)
    exp_per_hour = kills_per_hour * float(spot.get('avg_exp', 0))
    hours = exp_to_next(state.level) / max(1.0, exp_per_hour)

    mp_cost = mp_cost_per_attack(state.skills) * kills_per_hour * hours
    death_risk = max(0.0, min(0.45, (float(spot.get('avg_level', 1)) - state.level + 5) / 18.0 - acc / 900.0))
    expected_deaths = death_risk * hours
    potion_cost = mp_cost * 2.0 + expected_deaths * (250 + state.level * 20)
    economy = config.get('version_rules', {}).get('economy', {})
    meso_mult = float(economy.get('meso_income_multiplier', 0.25))
    meso_earned = kills_per_hour * hours * (float(spot.get('avg_level', 1)) * 2.0 + float(spot.get('avg_exp', 0)) * 0.35) * meso_mult

    return {
        'map_id': spot.get('map_id'),
        'map_name': spot.get('map_name'),
        'mobs': [m.get('name') for m in (spot.get('mobs') or [])[:3]],
        'avg_level': round(float(spot.get('avg_level', 0)), 2),
        'accuracy': acc,
        'hit_rate': round(hit, 4),
        'hours': round(hours, 4),
        'exp_per_hour': round(exp_per_hour, 1),
        'kills_per_hour': round(kills_per_hour, 1),
        'potion_cost': round(potion_cost, 1),
        'meso_earned': round(meso_earned, 1),
        'expected_deaths': round(expected_deaths, 4),
    }


def candidate_maps(state: BuildState, spots: list[dict[str, Any]], config: dict[str, Any], top_maps: int) -> list[dict[str, Any]]:
    hard_min_hit = float(config.get('constraints', {}).get('hard_min_hit_rate', 0.55))
    lo = state.level - 10
    hi = state.level + int(config.get('constraints', {}).get('max_map_level_gap', 8))
    rows = []
    for spot in spots:
        if not is_training_accessible_map(spot, config):
            continue
        avg_level = float(spot.get('avg_level', 1))
        if not (lo <= avg_level <= hi):
            continue
        est = estimate_map(state, spot, config)
        if est['hit_rate'] < hard_min_hit:
            continue
        score = est['exp_per_hour'] - est['potion_cost'] * 4.0 - est['expected_deaths'] * 5000.0
        rows.append((score, est))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [row[1] for row in rows[:top_maps]]


def route_score(candidate: BuildState, pressure_bonus: float = 0.0) -> float:
    bankruptcy_penalty = abs(min(0.0, candidate.meso)) * 0.25
    return (
        candidate.total_hours * 100.0
        + candidate.total_potion_cost * 0.02
        + candidate.expected_deaths * 1000.0
        + bankruptcy_penalty
        - max(0.0, candidate.meso) * 0.0003
        - pressure_bonus
    )


def expand_state(state: BuildState, spots: list[dict[str, Any]], items: list[dict[str, Any]], config: dict[str, Any], top_maps: int) -> list[BuildState]:
    next_states: list[BuildState] = []
    ap_actions = ap_actions_for_job(state.job)
    for ap in ap_actions:
        stats_after_ap = apply_ap(state_stats(state), ap)
        pressure = future_equipment_pressure(items, state.job, state.level, stats_after_ap, lookahead=5)
        pressure_bonus = sum(pressure.values()) * 0.002
        for sp in available_sp_actions(state.job, state.level, state.skills):
            new_state = state.clone()
            new_state.str_ = stats_after_ap['str']
            new_state.dex = stats_after_ap['dex']
            new_state.int_ = stats_after_ap['int']
            new_state.luk = stats_after_ap['luk']
            new_state.skills = apply_sp(new_state.skills, sp)
            maps = candidate_maps(new_state, spots, config, top_maps)
            for chosen_map in maps:
                candidate = new_state.clone()
                candidate.level += 1
                candidate.total_hours += chosen_map['hours']
                candidate.total_potion_cost += chosen_map['potion_cost']
                candidate.expected_deaths += chosen_map['expected_deaths']
                candidate.meso += chosen_map['meso_earned'] - chosen_map['potion_cost']
                candidate.score = route_score(candidate, pressure_bonus)
                candidate.route.append({
                    'level': state.level,
                    'ap': ap.label,
                    'sp': sp.label,
                    'map': chosen_map['map_name'],
                    'map_id': chosen_map['map_id'],
                    'mobs': chosen_map['mobs'],
                    'hit_rate': chosen_map['hit_rate'],
                    'accuracy': chosen_map['accuracy'],
                    'hours': chosen_map['hours'],
                    'potion_cost': chosen_map['potion_cost'],
                    'meso_earned': chosen_map['meso_earned'],
                    'meso_after': round(candidate.meso, 1),
                    'expected_deaths': chosen_map['expected_deaths'],
                    'reason': build_reason(ap.label, sp.label, chosen_map),
                })
                next_states.append(candidate)
    return next_states


def build_reason(ap: str, sp: str, chosen_map: dict[str, Any]) -> str:
    mobs = ', '.join(chosen_map.get('mobs', [])) or 'unknown mobs'
    return f"AP {ap}; SP {sp}; fight {mobs}. Hit rate {chosen_map['hit_rate']:.2f}; EXP/hour {chosen_map['exp_per_hour']:.0f}; potion cost {chosen_map['potion_cost']:.0f}."


def select_beam(expanded: list[BuildState], beam_width: int, config: dict[str, Any]) -> list[BuildState]:
    economy = config.get('version_rules', {}).get('economy', {})
    allow_bankruptcy = bool(economy.get('bankruptcy_allowed', False))
    pool = expanded
    if not allow_bankruptcy:
        non_bankrupt = [state for state in expanded if state.meso >= 0]
        if non_bankrupt:
            pool = non_bankrupt
    pool.sort(key=lambda state: state.score)
    return pool[:beam_width]


def plan_route(spots: list[dict[str, Any]], items: list[dict[str, Any]], config: dict[str, Any], job: str, start_level: int, target_level: int, beam_width: int = 40, top_maps: int = 8) -> dict[str, Any]:
    beam = [initial_state(job, start_level)]
    for _level in range(start_level, target_level):
        expanded: list[BuildState] = []
        for state in beam:
            expanded.extend(expand_state(state, spots, items, config, top_maps))
        if not expanded:
            break
        beam = select_beam(expanded, beam_width, config)
    best = min(beam, key=lambda state: state.score)
    return {
        'job': job,
        'start_level': start_level,
        'target_level': target_level,
        'reached_level': best.level,
        'score': round(best.score, 3),
        'total_hours': round(best.total_hours, 3),
        'total_potion_cost': round(best.total_potion_cost, 1),
        'ending_meso': round(best.meso, 1),
        'bankrupt': best.meso < 0,
        'expected_deaths': round(best.expected_deaths, 3),
        'final_stats': best.to_dict(),
        'route': best.route,
    }
