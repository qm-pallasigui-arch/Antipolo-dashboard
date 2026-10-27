"""Run the same provisional pipeline as the dashboard on an evidence JSON or workbook."""
import argparse
import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard.weekly.provisional import run_provisional
from dashboard.weekly.selection import write_json
from dashboard.weekly.transform import prepare, read_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--disease', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.source.suffix.lower() == '.json':
        payload = json.loads(args.source.read_text(encoding='utf-8-sig'))
        dataset = payload.get('dataset', payload)
    else:
        encoded = 'data:application/octet-stream;base64,' + base64.b64encode(args.source.read_bytes()).decode()
        dataset = prepare(read_source(encoded, args.source.name))
    write_json(args.output / 'input.json', {'dataset': dataset, 'source_path': str(args.source.resolve())})
    def emit(stage, message):
        print(stage + ': ' + message, flush=True)
    result = run_provisional(dataset, args.disease, args.output, emit)
    print(json.dumps({'configuration': result['configuration']['candidates'],
                      'nnar': {k: result['configuration'][k] for k in ('nnar_lags', 'hidden_nodes', 'alpha', 'seed')},
                      'validation': result['validation_metrics'], 'final_test': result['metrics'],
                      'interpretation': result['interpretation']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
