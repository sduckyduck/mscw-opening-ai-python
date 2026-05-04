from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(frozen=True)
class ApAction:
    str_add: int = 0
    dex_add: int = 0
    int_add: int = 0
    luk_add: int = 0

    @property
    def label(self) -> str:
        parts = []
        for key, value in [('STR', self.str_add), ('DEX', self.dex_add), ('INT', self.int_add), ('LUK', self.luk_add)]:
            if value:
                parts.append(f'+{value} {key}')
        return ' / '.join(parts) if parts else 'no AP'


@dataclass(frozen=True)
class SpAction:
    skill_id: str
    skill_name: str
    points: int = 1

    @property
    def label(self) -> str:
        return f'+{self.points} {self.skill_name}'


@dataclass
class BuildState:
    level: int
    job: str
    str_: float
    dex: float
    int_: float
    luk: float
    hp: float
    mp: float
    meso: float
    skills: dict[str, int] = field(default_factory=dict)
    gear: dict[str, Any] = field(default_factory=dict)
    route: list[dict[str, Any]] = field(default_factory=list)
    total_hours: float = 0.0
    total_potion_cost: float = 0.0
    expected_deaths: float = 0.0
    score: float = 0.0

    def clone(self) -> 'BuildState':
        return BuildState(
            level=self.level,
            job=self.job,
            str_=self.str_,
            dex=self.dex,
            int_=self.int_,
            luk=self.luk,
            hp=self.hp,
            mp=self.mp,
            meso=self.meso,
            skills=dict(self.skills),
            gear=dict(self.gear),
            route=list(self.route),
            total_hours=self.total_hours,
            total_potion_cost=self.total_potion_cost,
            expected_deaths=self.expected_deaths,
            score=self.score,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['str'] = data.pop('str_')
        data['int'] = data.pop('int_')
        return data
