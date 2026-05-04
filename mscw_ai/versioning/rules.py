from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mscw_ai.utils.io import read_yaml


@dataclass(frozen=True)
class VersionRules:
    version_id: str
    version_name: str
    formulas: dict[str, Any]
    progression: dict[str, Any]
    economy: dict[str, Any]
    drops: dict[str, Any]
    routing: dict[str, Any]


def load_version_rules(path: str | Path) -> VersionRules:
    data = read_yaml(path)
    return VersionRules(
        version_id=str(data.get('version_id', 'unknown')),
        version_name=str(data.get('version_name', data.get('version_id', 'unknown'))),
        formulas=dict(data.get('formulas', {})),
        progression=dict(data.get('progression', {})),
        economy=dict(data.get('economy', {})),
        drops=dict(data.get('drops', {})),
        routing=dict(data.get('routing', {})),
    )


def merge_rules_into_config(config: dict[str, Any], rules: VersionRules) -> dict[str, Any]:
    out = dict(config)
    out['version_id'] = rules.version_id
    out['version_name'] = rules.version_name
    out['version_rules'] = {
        'formulas': rules.formulas,
        'progression': rules.progression,
        'economy': rules.economy,
        'drops': rules.drops,
        'routing': rules.routing,
    }

    constraints = dict(out.get('constraints', {}))
    routing = rules.routing
    if 'excluded_training_map_ids' in routing:
        constraints['excluded_training_map_ids'] = routing['excluded_training_map_ids']
    if 'max_same_map_streak' in routing:
        constraints['max_same_map_streak'] = routing['max_same_map_streak']
    if 'max_over_level_gap' in routing:
        constraints['max_over_level_gap'] = routing['max_over_level_gap']
    formulas = rules.formulas
    accuracy = formulas.get('accuracy', {}) if isinstance(formulas.get('accuracy'), dict) else {}
    if 'hard_min_hit_rate' in accuracy:
        constraints['hard_min_hit_rate'] = accuracy['hard_min_hit_rate']
    if 'preferred_hit_rate' in accuracy:
        constraints['preferred_hit_rate'] = accuracy['preferred_hit_rate']
    out['constraints'] = constraints
    return out
