import heapq, json, random, sys
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupShuffleSplit

REAL_HOURLY = [2,3,3,2,4,5,5,2,5,7,6,15,14,10,15,13,17,14,20,14,15,15,8,6]
MEAN = {'reg': 3.2, 'doc': 10.5, 'pha': 4.8}
STAGES = ['reg', 'doc', 'pha']
OPEN, CLOSE = 450, 1020

def shape(t):
    h = int(t // 60) % 24
    return REAL_HOURLY[h] / max(REAL_HOURLY[7:17])

def sim_day(rng, day):
    base = rng.uniform(0.15, 0.55)
    k = {'reg': rng.randint(1, 4), 'doc': rng.randint(2, 6), 'pha': rng.randint(1, 3)}
    ev, seq, t = [], 0, OPEN
    while True:
        t += rng.expovariate(base)
        if t > CLOSE: break
        if rng.random() < shape(t) / 1.0:
            u = 0 if rng.random() < 0.05 else (1 if rng.random() < 0.16 else 2)
            heapq.heappush(ev, (t, seq, 'arr', {'u': u, 't0': t, 'w': 0.0})); seq += 1
    q = {s: [] for s in STAGES}; busy = {s: 0 for s in STAGES}
    rows, recent = [], []
    def start(s, now):
        nonlocal seq
        while busy[s] < k[s] and q[s]:
            _, _, enq, p = heapq.heappop(q[s])
            p['w'] += now - enq; busy[s] += 1
            heapq.heappush(ev, (now + rng.lognormvariate(np.log(MEAN[s]) - 0.18, 0.6), seq, 'fin', (s, p))); seq += 1
    def enqueue(s, p, now):
        nonlocal seq
        heapq.heappush(q[s], (p['u'], now, now, p)); seq += 1
        start(s, now)
    while ev:
        now, _, kind, d = heapq.heappop(ev)
        if kind == 'arr':
            recent = [x for x in recent if x > now - 30] + [now]
            d['feat'] = [now / 60, d['u'], len(q['reg']), len(q['doc']), len(q['pha']), busy['reg'], busy['doc'], busy['pha'], k['reg'], k['doc'], k['pha'], len(recent)]
            d['formula'] = sum((len(q[s]) + max(0, busy[s] - k[s] + 1)) / k[s] * MEAN[s] for s in STAGES)
            enqueue('reg', d, now)
        else:
            s, p = d; busy[s] -= 1
            nxt = STAGES.index(s) + 1
            if nxt < 3: enqueue(STAGES[nxt], p, now)
            else: rows.append((p['feat'], p['formula'], p['w'], day))
            start(s, now)
    return rows

def main(days):
    rng = random.Random(7); rows = []
    for d in range(days): rows += sim_day(rng, d)
    X = np.array([r[0] for r in rows]); F = np.array([r[1] for r in rows]); y = np.array([r[2] for r in rows]); g = np.array([r[3] for r in rows])
    tr, te = next(GroupShuffleSplit(1, test_size=0.2, random_state=0).split(X, y, g))
    m = HistGradientBoostingRegressor(loss='absolute_error', max_iter=300, learning_rate=0.08, max_leaf_nodes=31, random_state=0).fit(X[tr], y[tr])
    p = m.predict(X[te])
    mae_m = float(np.mean(np.abs(p - y[te]))); mae_f = float(np.mean(np.abs(F[te] - y[te]))); mae_0 = float(np.mean(np.abs(np.median(y[tr]) - y[te])))
    within = float(np.mean(np.abs(p - y[te]) <= 10)) * 100; within_f = float(np.mean(np.abs(F[te] - y[te]) <= 10)) * 100
    ss = float(np.sum((y[te] - y[te].mean()) ** 2)); r2 = 1 - float(np.sum((y[te] - p) ** 2)) / ss; r2f = 1 - float(np.sum((y[te] - F[te]) ** 2)) / ss
    out = dict(visits=len(rows), days=days, train=int(len(tr)), test=int(len(te)), test_days=int(len(set(g[te]))),
               mae_model=round(mae_m, 1), mae_formula=round(mae_f, 1), mae_median=round(mae_0, 1),
               within10_model=round(within), within10_formula=round(within_f), r2_model=round(r2, 2), r2_formula=round(r2f, 2),
               improve=round((1 - mae_m / mae_f) * 100), mean_wait=round(float(y.mean()), 1))
    print(json.dumps(out)); json.dump(out, open('result_eta.json', 'w'))

if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2000)
