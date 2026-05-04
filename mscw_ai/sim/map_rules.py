from __future__ import annotations

from typing import Any

# Maps that should not be considered normal training maps.
# 80001100 = Magician's Tree Dungeon. It is tied to mage/job-advancement access.
# 800xxxxx maps in this dataset are mostly instanced PQ / job / event maps, not ordinary grinding maps.
DEFAULT_EXCLUDED_TRAINING_MAP_IDS = {
    80001100,
}

DEFAULT_EXCLUDED_NAME_KEYWORDS = (
    'job advancement',
    'training camp',
    'tutorial',
    'accompaniment',
    '<1st stage>',
    '<last stage>',
)


def excluded_training_map_ids(config: dict[str, Any] | None = None) -> set[int]:
    ids = set(DEFAULT_EXCLUDED_TRAINING_MAP_IDS)
    if config:
        for value in config.get('excluded_training_map_ids', []) or []:
            try:
                ids.add(int(value))
            except (TypeError, ValueError):
                continue
        for value in config.get('constraints', {}).get('excluded_training_map_ids', []) or []:
            try:
                ids.add(int(value))
            except (TypeError, ValueError):
                continue
    return ids


def exclude_instanced_maps(config: dict[str, Any] | None = None) -> bool:
    if not config:
        return True
    routing = config.get('version_rules', {}).get('routing', {})
    return bool(routing.get('exclude_instanced_map_ids', True))


def is_training_accessible_map(spot: dict[str, Any], config: dict[str, Any] | None = None) -> bool:
    try:
        map_id = int(spot.get('map_id'))
    except (TypeError, ValueError):
        return False

    if map_id in excluded_training_map_ids(config):
        return False

    if exclude_instanced_maps(config) and map_id >= 80000000:
        return False

    name = str(spot.get('map_name', '')).lower()
    if any(keyword in name for keyword in DEFAULT_EXCLUDED_NAME_KEYWORDS):
        return False

    return True
