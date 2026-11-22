import sys, json, warnings
import numpy as np, pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings('ignore')

D = sys.argv[1] if len(sys.argv) > 1 else '.'
e = pd.read_csv(f'{D}/edstays.csv', parse_dates=['intime', 'outtime'])
t = pd.read_csv(f'{D}/triage.csv')
d = e.merge(t, on=['subject_id', 'stay_id'], how='left')
d['los'] = (d.outtime - d.intime).dt.total_seconds() / 60
d = d[(d.los > 0) & (d.los < 48 * 60)].sort_values(['subject_id', 'intime']).reset_index(drop=True)
d['hour'] = d.intime.dt.hour
d['dow'] = d.intime.dt.dayofweek
d['amb'] = d.arrival_transport.isin(['AMBULANCE', 'HELICOPTER']).astype(int)
d['walk'] = (d.arrival_transport == 'WALK IN').astype(int)
d['male'] = (d.gender == 'M').astype(int)
VIT = ['temperature', 'heartrate', 'resprate', 'o2sat', 'sbp', 'dbp', 'pain', 'acuity']
for c in VIT: d[c] = pd.to_numeric(d[c], errors='coerce')
g = d.groupby('subject_id')
d['prior_n'] = g.cumcount()
d['prior_med'] = g.los.transform(lambda s: s.shift().expanding().median())
d['prior_last'] = g.los.shift()
d['gap_days'] = g.intime.diff().dt.total_seconds() / 86400
d['cc'] = d.chiefcomplaint.fillna('').str.upper()

BASIC = ['hour', 'dow', 'acuity', 'amb']
NUM = BASIC + ['walk', 'male'] + VIT[:-1]
HIST = ['prior_n', 'prior_med', 'prior_last', 'gap_days']

def pre(cols, text):
    tr = [('n', make_pipeline(SimpleImputer(strategy='median', add_indicator=True), StandardScaler()), cols)]
    if text: tr.append(('t', CountVectorizer(min_df=4, binary=True, lowercase=False, token_pattern=r'[A-Z/]{2,}'), 'cc'))
    return ColumnTransformer(tr, sparse_threshold=0)

def logt(m): return TransformedTargetRegressor(m, func=np.log, inverse_func=np.exp)

CANDS = {
    'gbr_basic': make_pipeline(pre(BASIC, False), GradientBoostingRegressor(loss='absolute_error', n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=0)),
    'gbr_triage': make_pipeline(pre(NUM, True), GradientBoostingRegressor(loss='absolute_error', n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=0)),
    'gbr_triage_hist': make_pipeline(pre(NUM + HIST, True), GradientBoostingRegressor(loss='absolute_error', n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=0)),
    'rf_log_triage_hist': logt(make_pipeline(pre(NUM + HIST, True), RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=0))),
    'ridge_log_triage_hist': logt(make_pipeline(pre(NUM + HIST, True), Ridge(alpha=30))),
    'ridge_log_triage': logt(make_pipeline(pre(NUM, True), Ridge(alpha=30))),
}

X, y, grp = d, d.los.values, d.subject_id.values
mae = lambda a, b: float(np.mean(np.abs(a - b)))

def folds(groups, k, seed):
    u = np.unique(groups); rng = np.random.RandomState(seed); rng.shuffle(u)
    m = {s: i % k for i, s in enumerate(u)}; f = np.array([m[s] for s in groups])
    return [(np.where(f != i)[0], np.where(f == i)[0]) for i in range(k)]

rows, picks = [], {}
for rep in range(5):
    for tr, te in folds(grp, 5, rep):
        inner = {}
        for name, m in CANDS.items():
            s = []
            for a, b in folds(grp[tr], 3, 100 + rep):
                s.append(mae(clone(m).fit(X.iloc[tr[a]], y[tr[a]]).predict(X.iloc[tr[b]]), y[tr[b]]))
            inner[name] = np.mean(s)
        best = min(inner, key=inner.get); picks[best] = picks.get(best, 0) + 1
        p = clone(CANDS[best]).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
        old = clone(CANDS['gbr_basic']).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
        rows.append((mae(np.median(y[tr]), y[te]), mae(p, y[te]), mae(old, y[te]), len(tr), len(te)))
r = np.array(rows)
out = dict(n=int(len(d)), patients=int(d.subject_id.nunique()), base_mae=round(r[:, 0].mean()), model_mae=round(r[:, 1].mean()),
           old_mae=round(r[:, 2].mean()), improve=round((1 - r[:, 1].mean() / r[:, 0].mean()) * 100),
           wins=int((r[:, 1] < r[:, 0]).sum()), folds=len(r), ntr=int(r[:, 3].mean()), nte=int(r[:, 4].mean()),
           median_los=round(float(np.median(y))), hourly=np.bincount(d.hour, minlength=24).tolist(), picks=picks)
print(json.dumps(out)); json.dump(out, open('result.json', 'w'))
