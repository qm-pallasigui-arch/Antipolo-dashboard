"""Real-library verification in an isolated database; never alters the active app database."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--canonical', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='antipolo-prototype-verification-') as directory:
        os.environ['MPLCONFIGDIR'] = str(Path(directory) / 'matplotlib')
        for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'STAN_NUM_THREADS'):
            os.environ[key] = '1'
        from dashboard.monthly.store import Store
        from dashboard.monthly.security import create_user
        from dashboard.monthly.forecast import ForecastService
        from dashboard.monthly.reports import build_report, export_html
        if args.canonical:
            raw, filename = args.canonical.read_bytes(), args.canonical.name
        else:
            from tests.test_monthly_system import frame
            raw, filename = frame().to_csv(index=False).encode(), 'synthetic-verification.csv'
        store = Store(Path(directory) / 'state.sqlite3', is_prototype=True)
        user_id = create_user(store, 'prototype-verifier', 'isolated-verification-password', bootstrap=True)
        user = dict(id=user_id, username='prototype-verifier', role='admin', active=1)
        candidate = store.stage(user, raw, filename)
        dataset = store.activate(user, candidate['candidate_id'])
        ranking = ForecastService(store).run_all(user)
        from dashboard.monthly.repositories.forecast_repository import ForecastRepository
        forecasts = ForecastRepository(store).completed(dataset['dataset_signature'])
        with store.connect() as db:
            statuses = dict(db.execute('SELECT status,count(*) FROM forecasts GROUP BY status'))
            value_count = db.execute('SELECT count(*) FROM forecast_values').fetchone()[0]
        summary = dict(is_prototype=True, methodology_status='provisional', input_file=filename,
            dataset_signature=dataset['dataset_signature'], configuration=store.model_config.snapshot(),
            readiness=dataset['blocks'], statuses=statuses, stored_monthly_values=value_count,
            ranking=ranking, evaluations={r['icd10_block']: r['evaluation'] for r in forecasts})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2, allow_nan=False), encoding='utf-8')
        if forecasts:
            args.output.with_suffix('.html').write_text(export_html(build_report(store, user, forecasts[0]['icd10_block'])), encoding='utf-8')
        print(json.dumps({'statuses': statuses, 'stored_monthly_values': value_count,
                          'ranked_blocks': len(ranking['rankings']), 'top_five_status': ranking['top_five_status']}))
        if ranking['failed_blocks'] or not forecasts:
            raise SystemExit('Prototype verification failed; inspect persisted statuses in the evidence file.')


if __name__ == '__main__':
    main()
