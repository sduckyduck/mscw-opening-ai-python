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
