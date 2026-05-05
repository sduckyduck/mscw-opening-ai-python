from __future__ import annotations

from typing import Any

from mscw_ai.planner.actions import ap_actions_for_job, apply_ap
from mscw_ai.planner.equipment_requirements import future_equipment_pressure
from mscw_ai.planner.job_profiles import get_job_profile
from mscw_ai.planner.models import BuildState
from mscw_ai.planner.skills import (
    attack_skill_modes,
    available_sp_actions,
    apply_sp,
    buff_mp_cost_per_hour,
    damage_reduction_from_skills,
    hp_mp_survival_multiplier,
    passive_damage_multiplier,
    skill_accuracy,
    skill_speed_multiplier,
)
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


def combat_modes(state: BuildState, spot: dict[str, Any]) -> list[dict[str, float | str]]:
    mob_density = min(3.0, max(1.0, float(spot.get('total_mob_count', 1)) / 12.0))
    return attack_skill_modes(state.skills, mob_density=mob_density)


def estimate_map_with_mode(state: BuildState, spot: dict[str, Any], config: dict[str, Any], mode: dict[str, float | str]) -> dict[str, Any]:
    profile = get_job_profile(state.job)
    stats = state_stats(state)
    base_acc = stat_derived_accuracy(stats['dex'], stats['luk'])
    acc = base_acc + skill_accuracy(state.skills)
    hit = physical_hit_rate(state.level, float(spot.get('avg_level', 1)), acc, float(spot.get('avg_avoid', 0)))
    primary = stats.get(profile.primary_stat, 0.0)
    secondary = sum(stats.get(stat, 0.0) for stat in profile.secondary_stats)
    watk = 17.0 + float(state.gear.get('weapon_attack', 0.0))
    level_penalty = 1.0 / (1.0 + max(0.0, float(spot.get('avg_level', 1)) - state.level) * 0.08)
    speed_mult = skill_speed_multiplier(state.skills)
    mob_factor = float(mode.get('mob_factor', 1.0))
    damage = (watk * 2.6 + primary * 1.35 + secondary * 0.35) * hit * level_penalty * passive_damage_multiplier(state.skills) * float(mode['damage_mult'])
    kill_seconds = max(0.65, min(22.0, (float(spot.get('avg_hp', 1)) / max(1.0, damage) + 0.8) / speed_mult))
    kills_per_hour = min((3600.0 / kill_seconds) * mob_factor, float(spot.get('total_mob_count', 1)) * 850.0)
    exp_per_hour = kills_per_hour * float(spot.get('avg_exp', 0))
    hours = exp_to_next(state.level) / max(1.0, exp_per_hour)
    attacks_needed = kills_per_hour * hours / max(1.0, mob_factor)
    active_mp_cost = float(mode['mp_cost']) * attacks_needed
    buff_mp_cost = buff_mp_cost_per_hour(state.skills) * hours

    survival_mult = hp_mp_survival_multiplier(state.skills)
    damage_reduction = damage_reduction_from_skills(state.skills)
    contact_pressure = max(0.0, float(spot.get('avg_level', 1)) - state.level + 6.0)
    contact_events = kills_per_hour * hours * min(0.18, 0.035 + contact_pressure * 0.008)
    hp_potion_cost = contact_events * (state.level * 1.1 + float(spot.get('avg_level', 1)) * 0.9) * (1.0 - damage_reduction) / survival_mult

    death_risk = max(0.0, min(0.45, (float(spot.get('avg_level', 1)) - state.level + 5) / 18.0 - acc / 900.0)) / survival_mult
    expected_deaths = death_risk * hours
    mp_potion_cost = (active_mp_cost + buff_mp_cost) * 2.0
    potion_cost = mp_potion_cost + hp_potion_cost + expected_deaths * (250 + state.level * 20)
    economy = config.get('version_rules', {}).get('economy', {})
    meso_mult = float(economy.get('meso_income_multiplier', 0.25))
    meso_earned = kills_per_hour * hours * (float(spot.get('avg_level', 1)) * 2.0 + float(spot.get('avg_exp', 0)) * 0.35) * meso_mult
    net_value = exp_per_hour - potion_cost * 4.0 - expected_deaths * 5000.0
    return {
        'map_id': spot.get('map_id'),
        'map_name': spot.get('map_name'),
        'mobs': [m.get('name') for m in (spot.get('mobs') or [])[:3]],
        'avg_level': round(float(spot.get('avg_level', 0)), 2),
        'combat_mode': str(mode['name']),
        'accuracy': acc,
        'hit_rate': round(hit, 4),
        'hours': round(hours, 4),
        'exp_per_hour': round(exp_per_hour, 1),
        'kills_per_hour': round(kills_per_hour, 1),
        'potion_cost': round(potion_cost, 1),
        'hp_potion_cost': round(hp_potion_cost, 1),
        'mp_potion_cost': round(mp_potion_cost, 1),
        'active_mp_cost': round(active_mp_cost * 2.0, 1),
        'buff_mp_cost': round(buff_mp_cost * 2.0, 1),
        'meso_earned': round(meso_earned, 1),
        'expected_deaths': round(expected_deaths, 4),
        'net_value': round(net_value, 2),
    }


def estimate_map(state: BuildState, spot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    estimates = [estimate_map_with_mode(state, spot, config, mode) for mode in combat_modes(state, spot)]
    return max(estimates, key=lambda item: item['net_value'])


def _candidate_maps_for_band(state: BuildState, spots: list[dict[str, Any]], config: dict[str, Any], top_maps: int, lo: float, hi: float, fallback: bool) -> list[dict[str, Any]]:
    hard_min_hit = float(config.get('constraints', {}).get('hard_min_hit_rate', 0.55))
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
        if fallback:
            level_gap = max(0.0, state.level - avg_level - 10.0)
            est['net_value'] = round(float(est['net_value']) - level_gap * 2500.0, 2)
            est['fallback_lower_level'] = True
        rows.append((est['net_value'], est))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [row[1] for row in rows[:top_maps]]


def candidate_maps(state: BuildState, spots: list[dict[str, Any]], config: dict[str, Any], top_maps: int) -> list[dict[str, Any]]:
    max_gap = int(config.get('constraints', {}).get('max_map_level_gap', 8))
    normal = _candidate_maps_for_band(state, spots, config, top_maps, state.level - 10, state.level + max_gap, False)
    if normal:
        return normal
    return _candidate_maps_for_band(state, spots, config, top_maps, max(1, state.level - 25), state.level + max_gap, True)


def route_score(candidate: BuildState, pressure_bonus: float = 0.0) -> float:
    bankruptcy_penalty = abs(min(0.0, candidate.meso)) * 0.25
    return candidate.total_hours * 100.0 + candidate.total_potion_cost * 0.02 + candidate.expected_deaths * 1000.0 + bankruptcy_penalty - max(0.0, candidate.meso) * 0.0003 - pressure_bonus


def expand_state(state: BuildState, spots: list[dict[str, Any]], items: list[dict[str, Any]], config: dict[str, Any], top_maps: int) -> list[BuildState]:
    next_states: list[BuildState] = []
    for ap in ap_actions_for_job(state.job):
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
            for chosen_map in candidate_maps(new_state, spots, config, top_maps):
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
                    'combat_mode': chosen_map['combat_mode'],
                    'map': chosen_map['map_name'],
                    'map_id': chosen_map['map_id'],
                    'mobs': chosen_map['mobs'],
                    'fallback_lower_level': bool(chosen_map.get('fallback_lower_level', False)),
                    'hit_rate': chosen_map['hit_rate'],
                    'accuracy': chosen_map['accuracy'],
                    'hours': chosen_map['hours'],
                    'potion_cost': chosen_map['potion_cost'],
                    'hp_potion_cost': chosen_map.get('hp_potion_cost', 0.0),
                    'mp_potion_cost': chosen_map.get('mp_potion_cost', 0.0),
                    'active_mp_cost': chosen_map.get('active_mp_cost', 0.0),
                    'buff_mp_cost': chosen_map.get('buff_mp_cost', 0.0),
                    'meso_earned': chosen_map['meso_earned'],
                    'meso_after': round(candidate.meso, 1),
                    'expected_deaths': chosen_map['expected_deaths'],
                    'reason': build_reason(ap.label, sp.label, chosen_map),
                })
                next_states.append(candidate)
    return next_states


def build_reason(ap: str, sp: str, chosen_map: dict[str, Any]) -> str:
    mobs = ', '.join(chosen_map.get('mobs', [])) or 'unknown mobs'
    fallback = ' fallback lower-level route;' if chosen_map.get('fallback_lower_level') else ''
    return f"AP {ap}; SP {sp};{fallback} use {chosen_map.get('combat_mode')}; fight {mobs}. Hit rate {chosen_map['hit_rate']:.2f}; EXP/hour {chosen_map['exp_per_hour']:.0f}; HP pot {chosen_map.get('hp_potion_cost', 0):.0f}; MP pot {chosen_map.get('mp_potion_cost', 0):.0f}."


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
