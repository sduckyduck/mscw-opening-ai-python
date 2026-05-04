from __future__ import annotations

from pathlib import Path
from typing import Any

from mscw_ai.utils.io import read_json, write_json


def _as_list(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return payload[key]
    if isinstance(payload, list):
        return payload
    return []


def build_dataset(source_dir: str | Path, out_dir: str | Path) -> dict[str, int]:
    source = Path(source_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    monsters_payload = read_json(source / 'monsters.json')
    maps_payload = read_json(source / 'maps.json')
    items_payload = read_json(source / 'items.json') if (source / 'items.json').exists() else {'items': []}

    monsters = _as_list(monsters_payload, 'monsters')
    items = _as_list(items_payload, 'items')

    maps: list[dict[str, Any]] = []
    if isinstance(maps_payload, dict):
        for region in maps_payload.get('regions', []):
            for m in region.get('maps', []):
                m = dict(m)
                m.setdefault('region', region.get('region'))
                maps.append(m)

    training_spots: dict[int, dict[str, Any]] = {}
    map_by_id = {int(m.get('id')): m for m in maps if str(m.get('id', '')).isdigit()}
    for mob in monsters:
        if mob.get('is_boss'):
            continue
        for ref in mob.get('maps') or []:
            try:
                map_id = int(ref.get('id'))
            except Exception:
                continue
            m = map_by_id.get(map_id)
            if not m or m.get('is_town'):
                continue
            spot = training_spots.setdefault(
                map_id,
                {
                    'map_id': map_id,
                    'map_name': m.get('name') or ref.get('name') or f'Map {map_id}',
                    'region': m.get('region'),
                    'mobs': [],
                },
            )
            spot['mobs'].append(
                {
                    'id': mob.get('id'),
                    'name': mob.get('name'),
                    'level': mob.get('level', 1),
                    'hp': mob.get('hp', 1),
                    'exp': mob.get('exp', 0),
                    'avoid': mob.get('eva', 0),
                    'pa_damage': mob.get('PADamage', 0),
                    'ma_damage': mob.get('MADamage', 0),
                    'count': max(1, int(ref.get('count') or 1)),
                }
            )

    spot_rows = []
    for spot in training_spots.values():
        total_count = sum(m['count'] for m in spot['mobs']) or 1
        spot_rows.append(
            {
                **spot,
                'total_mob_count': total_count,
                'avg_level': sum(m['level'] * m['count'] for m in spot['mobs']) / total_count,
                'avg_hp': sum(m['hp'] * m['count'] for m in spot['mobs']) / total_count,
                'avg_exp': sum(m['exp'] * m['count'] for m in spot['mobs']) / total_count,
                'avg_avoid': sum((m.get('avoid') or 0) * m['count'] for m in spot['mobs']) / total_count,
            }
        )

    write_json(out / 'monsters.json', monsters)
    write_json(out / 'maps.json', maps)
    write_json(out / 'items.json', items)
    write_json(out / 'training_spots.json', spot_rows)
    return {'monsters': len(monsters), 'maps': len(maps), 'items': len(items), 'training_spots': len(spot_rows)}
