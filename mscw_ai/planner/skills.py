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

BASIC_SKILLS_BY_JOB = {
    'fighter': WARRIOR_SKILLS,
    'page': WARRIOR_SKILLS,
    'spearman': WARRIOR_SKILLS,
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
    return int(skills.get('warrior_precise_strikes', 0) * 1.3)


def skill_damage_multiplier(skills: dict[str, int]) -> float:
    power = skills.get('warrior_power_strike', 0)
    slash = skills.get('warrior_slash_blast', 0)
    return 1.0 + power * 0.035 + slash * 0.025


def mp_cost_per_attack(skills: dict[str, int]) -> float:
    power = skills.get('warrior_power_strike', 0)
    slash = skills.get('warrior_slash_blast', 0)
    return max(0.0, power * 0.35 + slash * 0.55)
