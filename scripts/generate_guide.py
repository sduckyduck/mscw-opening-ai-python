from __future__ import annotations

import argparse

from mscw_ai.guide.generator import build_guide
from mscw_ai.utils.io import read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True, help='Path to opening_q_table.json')
    parser.add_argument('--out', required=True, help='Output guide JSON path')
    args = parser.parse_args()
    report = read_json(args.model)
    guide = build_guide(report)
    write_json(args.out, guide)
    print(f'Saved guide to {args.out}')


if __name__ == '__main__':
    main()
