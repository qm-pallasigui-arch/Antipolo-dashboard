"""Corrected offline weekly selection. Requires a validated active-dataset JSON."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard.weekly.selection import select_dataset, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, help='Validated active dataset JSON, including metadata and quality')
    parser.add_argument('--output', required=True)
    parser.add_argument('--disease', choices=['Dengue', 'Leptospirosis', 'Measles'], action='append')
    parser.add_argument('--install', action='store_true', help='Install locks only after all requested searches and final tests succeed')
    args = parser.parse_args()
    dataset = json.loads(Path(args.dataset).read_text(encoding='utf-8'))
    configs = {}
    for disease in args.disease or ['Dengue', 'Leptospirosis', 'Measles']:
        c, _, _ = select_dataset(dataset, disease, Path(args.output) / disease)
        configs[disease] = c
    if args.install:
        write_json(Path(__file__).resolve().parents[1] / 'config/weekly_model_per_disease.json',
                   {'version': 'weekly-3', 'label': 'Validation-selected Hybrid SARIMA-NNAR', 'configurations': configs})


if __name__ == '__main__':
    main()
