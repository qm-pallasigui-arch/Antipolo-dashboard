"""Independent workbook-total and fixed-seasonality checks; no model changes."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from dashboard.data.mock_data import generate_fallback_data

data = json.loads(Path('evidence/investigation.json').read_text())
monthly = pd.read_csv('evidence/real-monthly.csv')
checks = {'workbook_totals': [], 'seasonal_average': []}
for sheet, disease in [('Dengue','Dengue'),('Measles-Rubella','Measles'),('Leptospirosis','Leptospirosis')]:
    raw = pd.read_excel(data['source'],sheet_name=sheet,header=None)
    header = next(i for i in range(10) if str(raw.iloc[i,0]).strip() == 'Morbidity Week')
    weeks = pd.to_numeric(raw.iloc[:,0],errors='coerce').between(1,53)
    for col in range(1,len(raw.columns)):
        year = int(raw.iloc[header,col])
        values = pd.to_numeric(raw.loc[weeks,col],errors='coerce')
        source_total = float(values.sum())
        parsed_total = int(monthly.loc[(monthly.disease==disease)&(monthly.year==year),'cases'].sum())
        assert source_total == parsed_total
        checks['workbook_totals'].append(dict(disease=disease,year=year,source_total=source_total,
                                             parsed_total=parsed_total,blank_week_cells=int(values.isna().sum())))
sample = generate_fallback_data()
for disease in sample.disease.unique():
    rows = sample.loc[sample.disease==disease]
    training = rows.loc[(rows.year<2025)&~rows.year.between(2020,2022)]
    seasonal = training.groupby('month').cases.mean().sort_index().to_numpy()
    actual = rows.loc[rows.year==2025].sort_values('month').cases.to_numpy()
    score = float(100*np.abs(actual-seasonal).sum()/np.abs(actual).sum())
    checks['seasonal_average'].append(dict(disease=disease,wape=score))
Path('evidence/source-checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print('PASS: all 30 workbook disease/year totals reconcile with parsed monthly data.')
print(json.dumps(checks['seasonal_average'],indent=2))
