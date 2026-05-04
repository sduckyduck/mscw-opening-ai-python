from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobProfile:
    job: str
    family: str
    primary_stat: str
    secondary_stats: tuple[str, ...]
    accuracy_stats: tuple[str, ...]
    weapon_types: tuple[str, ...]
    notes: str = ''


JOB_PROFILES: dict[str, JobProfile] = {
    'fighter': JobProfile('fighter', 'warrior', 'str', ('dex',), ('dex', 'luk'), ('1H Sword', '2H Sword', '1H Axe', '2H Axe', '1H Blunt Weapon', '2H Blunt Weapon')),
    'page': JobProfile('page', 'warrior', 'str', ('dex',), ('dex', 'luk'), ('1H Sword', '2H Sword', '1H Blunt Weapon', '2H Blunt Weapon')),
    'spearman': JobProfile('spearman', 'warrior', 'str', ('dex',), ('dex', 'luk'), ('Spear', 'Polearm')),
    'hunter': JobProfile('hunter', 'bowman', 'dex', ('str',), ('dex', 'luk'), ('Bow',)),
    'crossbowman': JobProfile('crossbowman', 'bowman', 'dex', ('str',), ('dex', 'luk'), ('Crossbow',)),
    'fire_poison': JobProfile('fire_poison', 'mage', 'int', ('luk',), ('int', 'luk'), ('Wand', 'Staff')),
    'ice_lightning': JobProfile('ice_lightning', 'mage', 'int', ('luk',), ('int', 'luk'), ('Wand', 'Staff')),
    'cleric': JobProfile('cleric', 'mage', 'int', ('luk',), ('int', 'luk'), ('Wand', 'Staff')),
    'assassin': JobProfile('assassin', 'thief', 'luk', ('dex',), ('dex', 'luk'), ('Claw',)),
    'bandit': JobProfile('bandit', 'thief', 'luk', ('dex', 'str'), ('dex', 'luk'), ('Dagger',)),
    'brawler': JobProfile('brawler', 'pirate', 'str', ('dex',), ('dex', 'luk'), ('Knuckle',)),
    'gunslinger': JobProfile('gunslinger', 'pirate', 'dex', ('str',), ('dex', 'luk'), ('Gun',)),
}


def get_job_profile(job: str) -> JobProfile:
    if job not in JOB_PROFILES:
        raise KeyError(f'Unknown job profile: {job}')
    return JOB_PROFILES[job]


def job_family(job: str) -> str:
    return get_job_profile(job).family


def primary_stat(job: str) -> str:
    return get_job_profile(job).primary_stat


def secondary_stats(job: str) -> tuple[str, ...]:
    return get_job_profile(job).secondary_stats
