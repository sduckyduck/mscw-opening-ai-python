from __future__ import annotations

from dataclasses import dataclass

from mscw_ai.planner.models import SpAction


@dataclass(frozen=True)
class SkillRule:
    skill_id: str
    name: str
    max_level: int
    stage: int
    prereq_skill_id: str | None = None
    prereq_level: int = 0
    effect_type: str = 'damage'


WARRIOR_SKILLS = [
    SkillRule('warrior_hp_recovery', 'Improved HP Recovery', 15, 1, effect_type='hp_recovery'),
    SkillRule('warrior_max_hp', 'Max HP Increase', 15, 1, 'warrior_hp_recovery', 3, 'max_hp'),
    SkillRule('warrior_precise_strikes', 'Precise Strikes', 15, 1, effect_type='accuracy'),
    SkillRule('warrior_power_strike', 'Power Strike', 20, 1, effect_type='single_damage'),
    SkillRule('warrior_slash_blast', 'Slash Blast', 20, 1, 'warrior_power_strike', 1, 'mob_damage'),
]

SPEARMAN_SECOND_JOB_SKILLS = [
    SkillRule('spearman_spear_mastery', 'Spear Mastery', 20, 2, effect_type='mastery_accuracy'),
    SkillRule('spearman_polearm_mastery', 'Polearm Mastery', 20, 2, effect_type='mastery_accuracy'),
    SkillRule('spearman_spear_booster', 'Spear Booster', 20, 2, 'spearman_spear_mastery', 5, 'speed'),
    SkillRule('spearman_polearm_booster', 'Polearm Booster', 20, 2, 'spearman_polearm_mastery', 5, 'speed'),
    SkillRule('spearman_iron_will', 'Iron Will', 20, 2, effect_type='defense'),
    SkillRule('spearman_hyper_body', 'Hyper Body', 30, 2, 'spearman_iron_will', 3, 'hp_mp'),
]

BASIC_SKILLS_BY_JOB = {
    'fighter': WARRIOR_SKILLS,
    'page': WARRIOR_SKILLS,
    'spearman': WARRIOR_SKILLS + SPEARMAN_SECOND_JOB_SKILLS,
}


def sp_for_level(level: int) -> int:
    if level < 10:
        return 0
    return 1 if level == 10 else 3


def stage_for_level(level: int) -> int:
    return 1 if level < 30 else 2


def available_sp_actions(job: str, level: int, skills: dict[str, int]) -> list[SpAction]:
    points = sp_for_level(level)
    if points <= 0:
        return []
    rules = BASIC_SKILLS_BY_JOB.get(job, [])
    actions: list[SpAction] = []
    stage = stage_for_level(level)
    for rule in rules:
        if rule.stage > stage:
            continue
        current = skills.get(rule.skill_id, 0)
        if current >= rule.max_level:
            continue
        if rule.prereq_skill_id and skills.get(rule.prereq_skill_id, 0) < rule.prereq_level:
            continue
        actions.append(SpAction(rule.skill_id, rule.name, min(points, rule.max_level - current)))
    return actions or [SpAction('hold_sp', 'Hold SP', 0)]


def apply_sp(skills: dict[str, int], action: SpAction) -> dict[str, int]:
    out = dict(skills)
    if action.points > 0:
        out[action.skill_id] = out.get(action.skill_id, 0) + action.points
    return out


def skill_accuracy(skills: dict[str, int]) -> int:
    first_job_acc = int(skills.get('warrior_precise_strikes', 0) * 1.3)
    spear_mastery_acc = int(skills.get('spearman_spear_mastery', 0) * 0.8)
    polearm_mastery_acc = int(skills.get('spearman_polearm_mastery', 0) * 0.8)
    return first_job_acc + max(spear_mastery_acc, polearm_mastery_acc)


def passive_damage_multiplier(skills: dict[str, int]) -> float:
    mastery = max(skills.get('spearman_spear_mastery', 0), skills.get('spearman_polearm_mastery', 0))
    return 1.0 + mastery * 0.012


def attack_skill_modes(skills: dict[str, int], mob_density: float = 1.0) -> list[dict[str, float | str]]:
    modes: list[dict[str, float | str]] = [{'name': 'basic_attack', 'damage_mult': 1.0, 'mp_cost': 0.0, 'mob_factor': 1.0}]
    power = skills.get('warrior_power_strike', 0)
    slash = skills.get('warrior_slash_blast', 0)
    if power > 0:
        modes.append({
            'name': 'power_strike',
            'damage_mult': 1.0 + power / 20.0 * 1.6,
            'mp_cost': 5.0 + power * 0.35,
            'mob_factor': 1.0,
        })
    if slash > 0:
        modes.append({
            'name': 'slash_blast',
            'damage_mult': 0.9 + slash / 20.0 * 0.8,
            'mp_cost': 7.0 + slash * 0.45,
            'mob_factor': min(3.0, max(1.0, mob_density)),
        })
    return modes


def skill_damage_multiplier(skills: dict[str, int]) -> float:
    power = skills.get('warrior_power_strike', 0)
    slash = skills.get('warrior_slash_blast', 0)
    return passive_damage_multiplier(skills) + power * 0.0 + slash * 0.0


def skill_speed_multiplier(skills: dict[str, int]) -> float:
    booster = max(skills.get('spearman_spear_booster', 0), skills.get('spearman_polearm_booster', 0))
    return 1.0 + min(0.18, booster * 0.012)


def hp_mp_survival_multiplier(skills: dict[str, int]) -> float:
    hyper_body = skills.get('spearman_hyper_body', 0)
    max_hp = skills.get('warrior_max_hp', 0)
    return 1.0 + hyper_body * 0.012 + max_hp * 0.006


def damage_reduction_from_skills(skills: dict[str, int]) -> float:
    iron_will = skills.get('spearman_iron_will', 0)
    return min(0.18, iron_will * 0.006)


def buff_mp_cost_per_hour(skills: dict[str, int]) -> float:
    booster = max(skills.get('spearman_spear_booster', 0), skills.get('spearman_polearm_booster', 0))
    hyper_body = skills.get('spearman_hyper_body', 0)
    iron_will = skills.get('spearman_iron_will', 0)
    return booster * 18.0 + hyper_body * 16.0 + iron_will * 8.0


def mp_cost_per_attack(skills: dict[str, int]) -> float:
    # Deprecated compatibility helper. Active attack costs are now emitted by attack_skill_modes().
    return 0.0
