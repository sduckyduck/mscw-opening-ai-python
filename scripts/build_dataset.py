from __future__ import annotations

import argparse

from mscw_ai.etl.dataset_builder import build_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, help='Raw app_metadata directory')
    parser.add_argument('--out', required=True, help='Processed output directory')
    args = parser.parse_args()
    counts = build_dataset(args.source, args.out)
    print('Dataset built:')
    for key, value in counts.items():
        print(f'  {key}: {value}')


if __name__ == '__main__':
    main()
