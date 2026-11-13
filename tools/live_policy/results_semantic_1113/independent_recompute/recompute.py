"""Independent recompute of the semantic pre-registration scores (L1, L2, L3).

Written from PREREGISTRATION_SEMANTIC.md and DEVIATIONS_NOVEMBER.md items 51-52 only.
Usage: python recompute.py [--model deepseek] [--out /tmp/recompute/out_deepseek.json]
Options in OPT below change readings of points the rules leave open.
"""
import argparse, glob, itertools, json, math, os, re, sys
import numpy as np
import yaml

try:
    Loader = yaml.CSafeLoader
except AttributeError:
    Loader = yaml.SafeLoader

REPO = '/Users/sher/project/cvp/project'
SEM = f'{REPO}/tools/live_policy/semantic'
TRUTH = f'{SEM}/truth'
RUNS = '/Users/sher/cvp_live_campaign_copy/runs/live_campaign'
REPLAY = '/Users/sher/project/cvp/replay_outputs/m4'
DROPPED = []

OPT = dict(
    reach_to='square',       # 'square': distance to the cell square; 'centre': to the cell centre
    step7_from='singular',   # last word taken after the plural strip ('singular') or before ('raw')
    prior_include_unassigned=True,  # region -1 objects count in N_c
    horizontal_new=True,     # new-node distance horizontal (xy)
)
TYPES5 = ['bathroom', 'bedroom', 'kitchen', 'laundry', 'living']
CELL = 0.05
R_REACH = 0.5

# ---------------------------------------------------------------- labels
CL = json.load(open(f'{SEM}/canon_labels.json'))
STRUCT = set(CL['structure'])
TABLE = dict(CL['synonyms'])
for c in CL['classes']:
    TABLE.setdefault(c, c)
for c in CL['structure']:
    TABLE.setdefault(c, c)
DETLAB = {k.lower(): v for k, v in CL['detector_label'].items()}
NONSTRUCT_CLASSES = sorted(set(TABLE.values()) - STRUCT)


def clean(s):
    s = str(s).lower()
    s = re.sub(r'[_\-/]', ' ', s)
    s = re.sub(r'[0-9]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def singular(w):
    if w.endswith('ies'):
        return w[:-3] + 'y'
    if w.endswith('es') and re.search(r'(s|x|z|ch|sh)es$', w):
        return w[:-2]
    if w.endswith('s') and not w.endswith('ss'):
        return w[:-1]
    return w


def canon(s):
    s = clean(s)
    if s in TABLE:
        return TABLE[s]
    words = s.split(' ')
    if not words or words == ['']:
        return 'other'
    sing = ' '.join(words[:-1] + [singular(words[-1])])
    if sing in TABLE:
        return TABLE[sing]
    last = singular(words[-1]) if OPT['step7_from'] == 'singular' else words[-1]
    if last in TABLE:
        return TABLE[last]
    if OPT['step7_from'] == 'singular' and words[-1] in TABLE:
        return TABLE[words[-1]]
    return 'other'


def scored_class(c):
    return c is not None and c != 'other' and c not in STRUCT


def answers(raw):
    """Classes an annotated object answers to (5.3)."""
    out = set()
    c = canon(raw)
    if c != 'other':
        out.add(c)
    d = DETLAB.get(str(raw).lower().strip())
    if d is not None:
        c2 = canon(d)
        if c2 != 'other':
            out.add(c2)
    return out


def room_type(name):
    s = clean(name)
    if any(k in s for k in ('bath', 'toilet', 'restroom', 'washroom', 'shower')) or 'wc' in s.split(' '):
        return 'bathroom'
    if 'bed' in s:
        return 'bedroom'
    if 'kitchen' in s:
        return 'kitchen'
    if 'laundry' in s or 'utility' in s:
        return 'laundry'
    if any(k in s for k in ('living', 'lounge', 'family', 'sitting')):
        return 'living'
    if 'dining' in s:
        return 'dining'
    return None


MARKERS = {
    'bathroom': ['toilet', 'bathtub', 'bath tub', 'shower'],
    'bedroom': ['bed'],
    'kitchen': ['oven', 'stove', 'stovetop'],
    'laundry': ['washing machine', 'laundry machine', 'washer', 'dryer'],
    'living': ['couch', 'sofa'],
    'dining': ['dining table'],
}
EXCL = ['hair dryer', 'hand dryer', 'dish dryer', 'dog bed', 'cat bed', 'pet bed', 'massage bed',
        'toaster oven', 'sauna oven']


def _has_run(name_tokens, phrase):
    p = phrase.split(' ')
    n = len(p)
    return any(name_tokens[i:i + n] == p for i in range(len(name_tokens) - n + 1))


def marker_types(raw):
    toks = re.sub(r'[^a-z0-9]+', ' ', str(raw).lower()).split()
    if any(_has_run(toks, e) for e in EXCL):
        return set()
    return {t for t, ms in MARKERS.items() if any(_has_run(toks, m) for m in ms)}


# ---------------------------------------------------------------- truth
class Scene:
    def __init__(self, sc):
        z = np.load(f'{TRUTH}/{sc}_region_footprints.npz')
        self.ox, self.oy = [float(v) for v in z['origin_xy']]
        self.rids = [int(r) for r in z['region_ids']]
        self.floor = z['floor_masks']
        self.any = z['any_masks']
        self.ny, self.nx = self.any.shape[1:]
        geo = json.load(open(f'{TRUTH}/{sc}_semantic_geometry.json'))['objects']
        self.objs = []
        for o in geo.values():
            reg = o.get('region')
            has_geo = o.get('world_min') is not None and o.get('world_max') is not None and (o.get('n_tri') or 0) > 0
            cen = None
            if has_geo:
                cen = ((o['world_min'][0] + o['world_max'][0]) / 2, (o['world_min'][1] + o['world_max'][1]) / 2)
            ans = answers(o['name'])
            self.objs.append(dict(id=o['id'], name=o['name'], region=reg, cen=cen, ans=ans,
                                  ref=(has_geo and reg is not None and reg in self.rids and any(scored_class(c) for c in ans)),
                                  mtypes=marker_types(o['name'])))
        self.rtypes = {r: set() for r in self.rids}
        for o in self.objs:
            if o['region'] in self.rtypes:
                self.rtypes[o['region']] |= o['mtypes']
        self.has_floor = {r: bool(self.floor[i].any()) for i, r in enumerate(self.rids)}
        self.ref_by_region = {r: [o for o in self.objs if o['ref'] and o['region'] == r] for r in self.rids}
        self.classes_in = {r: set(c for o in self.ref_by_region[r] for c in o['ans'] if scored_class(c)) for r in self.rids}
        # reach cache
        self._reach = {}

    def cell(self, x, y):
        return int(math.floor((x - self.ox) / CELL)), int(math.floor((y - self.oy) / CELL))

    def inside(self, p, mask_kind='any'):
        ix, iy = self.cell(*p)
        if not (0 <= ix < self.nx and 0 <= iy < self.ny):
            return set()
        m = self.any if mask_kind == 'any' else self.floor
        return {r for i, r in enumerate(self.rids) if m[i, iy, ix]}

    def in_floor(self, p):
        ix, iy = self.cell(*p)
        if not (0 <= ix < self.nx and 0 <= iy < self.ny):
            return set()
        out = set()
        for i, r in enumerate(self.rids):
            m = self.floor if self.has_floor[r] else self.any
            if m[i, iy, ix]:
                out.add(r)
        return out

    def reaches(self, p):
        key = (round(p[0], 6), round(p[1], 6))
        if key in self._reach:
            return self._reach[key]
        x, y = p
        k = int(R_REACH / CELL) + 2
        cx, cy = self.cell(x, y)
        ix0, ix1 = max(cx - k, 0), min(cx + k + 1, self.nx)
        iy0, iy1 = max(cy - k, 0), min(cy + k + 1, self.ny)
        out = set()
        if ix0 < ix1 and iy0 < iy1:
            ixs = np.arange(ix0, ix1)
            iys = np.arange(iy0, iy1)
            if OPT['reach_to'] == 'square':
                lx = self.ox + ixs * CELL
                ly = self.oy + iys * CELL
                dx = np.maximum(np.maximum(lx - x, x - (lx + CELL)), 0)
                dy = np.maximum(np.maximum(ly - y, y - (ly + CELL)), 0)
            else:
                dx = np.abs(self.ox + (ixs + 0.5) * CELL - x)
                dy = np.abs(self.oy + (iys + 0.5) * CELL - y)
            D = np.sqrt(dy[:, None] ** 2 + dx[None, :] ** 2) <= R_REACH + 1e-12
            sub = self.any[:, iy0:iy1, ix0:ix1]
            for i, r in enumerate(self.rids):
                if (sub[i] & D).any():
                    out.add(r)
        self._reach[key] = out
        return out


SCENES = {}


def scene(sc):
    if sc not in SCENES:
        SCENES[sc] = Scene(sc)
    return SCENES[sc]


# ---------------------------------------------------------------- graphs
def pos(n):
    p = n.get('position')
    if isinstance(p, str):
        p = json.loads(p)
    return (float(p[0]), float(p[1]))


def load_graph(path):
    if isinstance(path, dict):
        g = path
    else:
        with open(path) as f:
            g = yaml.load(f, Loader=Loader)
    objs, rooms = [], []
    for n in g.get('nodes') or []:
        t = n.get('node_type')
        if t == 'object':
            objs.append(dict(name=str(n.get('name')), p=pos(n)))
        elif t == 'room':
            rooms.append(dict(name=str(n.get('name')), p=pos(n)))
    return objs, rooms


def d2(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ---------------------------------------------------------------- frame
def read_frame():
    rows = []
    rnd = 0
    for line in open(f'{SEM}/sample_frame.txt'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            m = re.match(r'#\s*Round\s+(\d+)', line)
            if m:
                rnd = int(m.group(1))
            continue
        rid, rd, st = line.split()
        m = re.match(r'(e1|e2|fa1)_(\d{5})_s(\d+)_', rid)
        scn, seed = m.group(2), int(m.group(3))
        arm = 'filter_only' if 'filter_only' in rd else 'official'
        rows.append(dict(row_id=rid, run=os.path.basename(rd), stage=int(st), scene=scn, seed=seed,
                         arm=arm, cluster=f'{scn}_s{seed}_{arm}', round=rnd))
    return rows


def member_paths(row, model):
    sd = f"{RUNS}/{row['run']}/stages/{row['stage']}"
    if model.startswith('claude-'):
        out = {}
        for m in range(4):
            md = f"{REPLAY}/{model}/effort_medium/{row['row_id']}/member_{m}"
            pj, pg = f'{md}/parse.json', f'{md}/parsed_graph.yaml'
            ok = os.path.exists(pj) and json.load(open(pj)).get('ok') is True and os.path.exists(pg)
            if ok:
                out[m] = pg
            else:
                DROPPED.append((row['row_id'], m))
        return out
    if model != 'deepseek':
        raise NotImplementedError(model)
    if row['arm'] == 'filter_only':
        atts = glob.glob(f'{sd}/live_policy_raw/attempt_*')
        hi = max(atts, key=lambda a: int(a.rsplit('_', 1)[1]))
        base = hi
    else:
        base = sd
    out = {}
    for m in range(4):
        p = f'{base}/habitat_scene_graph_new_graph_{m}.yaml'
        if os.path.exists(p):
            out[m] = p
    return out


# ---------------------------------------------------------------- row state (5.4, 5.5)
def row_state(row):
    S = scene(row['scene'])
    sd = f"{RUNS}/{row['run']}/stages"
    obs_objs, obs_rooms = load_graph(f"{sd}/{row['stage']}/habitat_scene_graph_original_graph0.yaml")
    for o in obs_objs:
        o['c'] = canon(o['name'])
    for r in obs_rooms:
        r['t'] = room_type(r['name'])
    pts = []
    for k in range(1, row['stage'] + 1):
        ep = f'{sd}/{k}/executed_path.json'
        if os.path.exists(ep):
            pts += [(float(p[0]), float(p[1])) for p in json.load(open(ep))['world_frame_path']]
        else:
            print('WARN no executed_path', ep, file=sys.stderr)

    def mapped(o):
        if o['cen'] is None:
            return False
        good = {c for c in o['ans'] if c not in STRUCT}
        if not good:
            return False
        return any(n['c'] in good and d2(n['p'], o['cen']) <= R_REACH for n in obs_objs)

    for o in S.objs:
        o['_mapped'] = mapped(o)
    seen, partly, unobs = set(), set(), set()
    path_regions = set()
    for p in pts:
        path_regions |= S.in_floor(p)
    room_in = [S.inside(r['p']) for r in obs_rooms]
    room_reach = [S.reaches(r['p']) for r in obs_rooms]
    for R in S.rids:
        nm = sum(1 for o in S.ref_by_region[R] if o['_mapped'])
        if R in path_regions or any(R in ri for ri in room_in) or nm >= 2:
            seen.add(R)
        elif nm >= 1 or any(R in rr for rr in room_reach):
            partly.add(R)
        else:
            unobs.add(R)
    unseen = partly | unobs
    open_types = set()
    for T in TYPES5 + ['dining']:
        for R in unseen:
            if T not in S.rtypes[R]:
                continue
            markers = [o for o in S.objs if o['region'] == R and T in o['mtypes']]
            if any(o['_mapped'] for o in markers):
                continue
            closed = False
            for r, ri, rr in zip(obs_rooms, room_in, room_reach):
                if r['t'] != T:
                    continue
                if R in ri:
                    closed = True
                    break
                if R in rr and not any((R2 != R and T in S.rtypes[R2]) for R2 in ri):
                    closed = True
                    break
            if not closed:
                open_types.add(T)
                break
    open_classes = set()
    for R in unseen:
        for o in S.ref_by_region[R]:
            if not o['_mapped']:
                open_classes |= {c for c in o['ans'] if scored_class(c)}
    return dict(S=S, obs_objs=obs_objs, obs_rooms=obs_rooms, seen=seen, partly=partly, unobs=unobs,
                open_types=open_types, open_classes=open_classes)


# ---------------------------------------------------------------- members (7, 8)
def member_claims(st, path):
    objs, rooms = load_graph(path)
    oo, orr = st['obs_objs'], st['obs_rooms']
    new_o = [o for o in objs if all(d2(o['p'], q['p']) > R_REACH for q in oo)]
    new_r = [r for r in rooms if all(d2(r['p'], q['p']) > R_REACH for q in orr)]
    for o in new_o:
        o['c'] = canon(o['name'])
    for r in new_r:
        r['t'] = room_type(r['name'])
    l1 = sorted({r['t'] for r in new_r if r['t'] in TYPES5})
    l2 = sorted({o['c'] for o in new_o if scored_class(o['c'])})
    items = [('room', r['t'], r['p']) for r in new_r if r['t'] in TYPES5] + \
            [('obj', o['c'], o['p']) for o in new_o if scored_class(o['c'])]
    return dict(n_new_o=len(new_o), n_new_r=len(new_r), l1=l1, l2=l2, items=items,
                n_dining_dropped=sum(1 for r in new_r if r['t'] == 'dining'))


def item_hit(S, kind, lab, R):
    if kind == 'room':
        return lab in S.rtypes[R]
    return lab in S.classes_in[R]


def l3_hits(st, items, sigma=None):
    S = st['S']
    h = 0
    for kind, lab, p in items:
        regs = S.reaches(p) & st['unobs']
        if sigma is not None:
            ok = any(item_hit(S, kind, lab, sigma[R]) for R in regs)
        else:
            ok = any(item_hit(S, kind, lab, R) for R in regs)
        h += ok
    return h


# ---------------------------------------------------------------- prior B3
def build_prior():
    s = json.load(open(f'{TRUTH}/hm3d_semantic_summary.json'))
    houses = {}
    for h in s['houses']:
        if h['number'] in ('00853', '00871'):
            continue
        houses.setdefault(h['number'], h)
    NT, NC = [], []
    for h in houses.values():
        nt = {T: 0 for T in TYPES5}
        nc = {}
        for rid, cats in h['regions'].items():
            if int(rid) >= 0:
                types = set()
                for name in cats:
                    types |= marker_types(name)
                for T in types:
                    if T in nt:
                        nt[T] += 1
            if int(rid) < 0 and not OPT['prior_include_unassigned']:
                continue
            for name, cnt in cats.items():
                for c in answers(name):
                    if scored_class(c):
                        nc[c] = nc.get(c, 0) + cnt
        NT.append(nt)
        NC.append(nc)
    held_T = {T: sum(1 for nt in NT if nt[T] > 0) for T in TYPES5}
    held_C = {}
    for nc in NC:
        for c, v in nc.items():
            if v > 0:
                held_C[c] = held_C.get(c, 0) + 1
    return dict(n=len(houses), NT=NT, NC=NC, held_T=held_T, held_C=held_C)


def prior_rank(P, st):
    mT = {T: int(any(r['t'] == T for r in st['obs_rooms'])) for T in TYPES5}
    nC = {}
    for o in st['obs_objs']:
        nC[o['c']] = nC.get(o['c'], 0) + 1

    def share(vals, m):
        den = sum(1 for v in vals if v >= m)
        return 0.0 if den == 0 else sum(1 for v in vals if v > m) / den
    sT = {T: share([nt[T] for nt in P['NT']], mT[T]) for T in TYPES5}
    sC = {c: share([nc.get(c, 0) for nc in P['NC']], nC.get(c, 0)) for c in NONSTRUCT_CLASSES}
    rT = sorted(TYPES5, key=lambda T: (-sT[T], -P['held_T'][T], T))
    rC = sorted(NONSTRUCT_CLASSES, key=lambda c: (-sC[c], -P['held_C'].get(c, 0), c))
    return rT, rC, sT, sC


# ---------------------------------------------------------------- stats
def signflip_p(d):
    d = np.asarray(d, float)
    n = len(d)
    obs = d.mean()
    S = np.array(list(itertools.product([1, -1], repeat=n)))
    m = (S * d).mean(1)
    return float(np.mean(m >= obs - 1e-12))


def signflip_ci(d, alpha=0.05):
    d = np.asarray(d, float)
    n = len(d)
    S = np.array(list(itertools.product([1, -1], repeat=n)))
    cands = set()
    for s in S:
        for sel in (s == -1, s == 1):
            if sel.any():
                cands.add(round(float(d[sel].mean()), 12))
    cands = sorted(cands)

    def p2(delta):
        e = d - delta
        t = abs(e.mean())
        return float(np.mean(np.abs((S * e).mean(1)) >= t - 1e-12))
    acc = [c for c in cands if p2(c) > alpha]
    return [min(acc), max(acc)] if acc else None


def mean_or_none(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


# ---------------------------------------------------------------- main
def derangement(n, rng):
    while True:
        p = rng.permutation(n)
        if not np.any(p == np.arange(n)):
            return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='deepseek')
    ap.add_argument('--out', default=None)
    ap.add_argument('--nd', type=int, default=200)
    ap.add_argument('--nb5', type=int, default=1000)
    ap.add_argument('--seed', type=int, default=20261113)
    ap.add_argument('--no-b1', action='store_true')
    ap.add_argument('--opt', action='append', default=[], help='key=value to override OPT')
    a = ap.parse_args()
    for kv in a.opt:
        k, v = kv.split('=')
        OPT[k] = {'True': True, 'False': False}.get(v, v)
    rng = np.random.default_rng(a.seed)
    global LP, CALIB
    if not a.no_b1:
        import importlib.util
        spec = importlib.util.spec_from_file_location('lp_placebo', f'{REPO}/tools/live_policy/live_policy.py')
        LP = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(LP)
        CALIB = LP.load_calibration()
    P = build_prior()
    rows = read_frame()
    out_rows = []
    for row in rows:
        st = row_state(row)
        rT, rC, sT, sC = prior_rank(P, st)
        mem = {}
        for m, path in member_paths(row, a.model).items():
            mc = member_claims(st, path)
            k1, k2 = len(mc['l1']), len(mc['l2'])
            l1h = sum(1 for T in mc['l1'] if T in st['open_types'])
            l2h = sum(1 for c in mc['l2'] if c in st['open_classes'])
            items = mc['items']
            l3h = l3_hits(st, items)
            b3_l1 = rT[:k1]
            b3_l2 = rC[:k2]
            b3h1 = sum(1 for T in b3_l1 if T in st['open_types'])
            b3h2 = sum(1 for c in b3_l2 if c in st['open_classes'])
            # B3L
            B3Lv = None
            if items:
                rep = {}
                for kind, rank in (('room', rT), ('obj', rC)):
                    cnt = {}
                    for it in items:
                        if it[0] == kind:
                            cnt[it[1]] = cnt.get(it[1], 0) + 1
                    order = sorted(cnt, key=lambda x: (-cnt[x], x))
                    for i, lab in enumerate(order):
                        rep[(kind, lab)] = rank[i]
                B3Lv = l3_hits(st, [(k, rep[(k, l)], pp) for k, l, pp in items]) / len(items)
            # D
            U = sorted(st['unobs'])
            Dv = None
            if items and len(U) >= 2:
                vals = []
                for _ in range(a.nd):
                    p = derangement(len(U), rng)
                    sigma = {U[i]: U[p[i]] for i in range(len(U))}
                    vals.append(l3_hits(st, items, sigma) / len(items))
                Dv = float(np.mean(vals))
            # B5
            B5v = None
            if items:
                vals = []
                rooms_i = [i for i, it in enumerate(items) if it[0] == 'room']
                objs_i = [i for i, it in enumerate(items) if it[0] == 'obj']
                for _ in range(a.nb5):
                    new = list(items)
                    for idx in (rooms_i, objs_i):
                        if len(idx) > 1:
                            labs = [items[i][1] for i in idx]
                            perm = rng.permutation(len(idx))
                            for j, i in enumerate(idx):
                                new[i] = (items[i][0], labs[perm[j]], items[i][2])
                    vals.append(l3_hits(st, new) / len(items))
                B5v = float(np.mean(vals))
            mem[m] = dict(n_new_o=mc['n_new_o'], n_new_r=mc['n_new_r'], l1=mc['l1'], l2=mc['l2'],
                          n_items=len(items), n_item_rooms=sum(1 for i in items if i[0] == 'room'),
                          l1_hits=l1h, l2_hits=l2h, l3_hits=l3h,
                          L1=l1h / k1 if k1 else None, L2=l2h / k2 if k2 else None,
                          L3=l3h / len(items) if items else None,
                          B3_L1=b3h1 / k1 if k1 else None, B3_L2=b3h2 / k2 if k2 else None,
                          B3_l1_claims=b3_l1, B3L=B3Lv, D=Dv, B5=B5v, dining_dropped=mc['n_dining_dropped'])
        b1 = {}
        if not a.no_b1:
            with open(f"{RUNS}/{row['run']}/stages/{row['stage']}/habitat_scene_graph_original_graph0.yaml") as f:
                obs_raw = yaml.safe_load(f)
            for m in range(4):
                g = LP.placebo_graph(obs_raw, np.random.default_rng([row['seed'], row['stage'], m]), CALIB)
                mc = member_claims(st, g)
                k1, k2 = len(mc['l1']), len(mc['l2'])
                b1[m] = dict(L1=(sum(T in st['open_types'] for T in mc['l1']) / k1) if k1 else None,
                             L2=(sum(c in st['open_classes'] for c in mc['l2']) / k2) if k2 else None)
        out_rows.append(dict(row, b1=b1, seen=sorted(st['seen']), partly=sorted(st['partly']), unobs=sorted(st['unobs']),
                             open_types=sorted(st['open_types']), open_classes=sorted(st['open_classes']),
                             possible=dict(L1=bool(st['open_types'] & set(TYPES5)), L2=bool(st['open_classes']),
                                           L3=bool(st['unobs'])),
                             members=mem))
        print(row['row_id'], 'seen', len(st['seen']), 'partly', len(st['partly']), 'unobs', len(st['unobs']),
              'open', sorted(st['open_types']), len(st['open_classes']), file=sys.stderr)
    res = analyse(out_rows)
    res['dropped'] = DROPPED
    json.dump(dict(opt=OPT, prior_n=P['n'], rows=out_rows, analysis=res), open(a.out or f'/tmp/recompute/out_{a.model}.json', 'w'), indent=1, default=list)
    print(json.dumps(res, indent=1))


def analyse(rows):
    res = {}
    clusters = sorted({r['cluster'] for r in rows})

    def row_mean(r, key):
        return mean_or_none([m[key] for m in r['members'].values()])

    for L, comps in (('L1', ['B3', 'B1']), ('L2', ['B3', 'B1']), ('L3', ['D', 'B5', 'B3L'])):
        live = [r for r in rows if r['possible'][L]]
        mcs = {}
        for c in clusters:
            v = mean_or_none([row_mean(r, L) for r in live if r['cluster'] == c])
            if v is not None:
                mcs[c] = v
        out = dict(n_rows_impossible=len(rows) - len(live), model_cluster_scores=mcs,
                   mean=float(np.mean(list(mcs.values()))))
        for comp in comps:
            key = f'B3_{L}' if comp == 'B3' else comp
            diffs = {}
            nrow = 0
            for c in clusters:
                pairs = []
                for r in live:
                    if r['cluster'] != c:
                        continue
                    if comp == 'B1':
                        x, y = row_mean(r, L), mean_or_none([v[L] for v in r.get('b1', {}).values()])
                        if x is not None and y is not None:
                            pairs.append((x, y))
                        continue
                    mm = [(m[L], m[key]) for m in r['members'].values() if m[L] is not None and m[key] is not None]
                    if mm:
                        pairs.append((np.mean([x for x, _ in mm]), np.mean([y for _, y in mm])))
                if pairs:
                    nrow += len(pairs)
                    diffs[c] = float(np.mean([x for x, _ in pairs]) - np.mean([y for _, y in pairs]))
            d = list(diffs.values())
            if not d:
                continue
            out[comp] = dict(clusters=diffs, n_rows=nrow, n_clusters=len(d), mean_diff=float(np.mean(d)),
                             p=signflip_p(d), ci=signflip_ci(d))
        res[L] = out
    return res


if __name__ == '__main__':
    main()


def family(results, alpha=0.05):
    """results: {model: analysis}. Holm over the six hypotheses, verdicts, thesis (10)."""
    named = {'L1': ('B3', 0.05), 'L2': ('B3', 0.05), 'L3': ('D', 0.03)}
    comps = {'L1': ['B3', 'B1'], 'L2': ['B3', 'B1'], 'L3': ['B5', 'D', 'B3L']}
    H = {}
    for m, A in results.items():
        for L in ('L1', 'L2', 'L3'):
            have = [c for c in comps[L] if c in A[L]]
            H[f'{m}|{L}'] = dict(p=max(A[L][c]['p'] for c in have), missing=[c for c in comps[L] if c not in have],
                                 ci_upper_named=A[L][named[L][0]]['ci'][1], delta=named[L][1])
    keys = sorted(H, key=lambda k: H[k]['p'])
    run = 0.0
    for i, k in enumerate(keys):
        run = max(run, min(1.0, (len(keys) - i) * H[k]['p']))
        H[k]['p_holm'] = run
    for k, h in H.items():
        h['verdict'] = 'Supported' if h['p_holm'] < alpha else ('Rejected' if h['ci_upper_named'] < h['delta'] else 'Inconclusive')
    models = list(results)
    v = lambda m, L: H[f'{m}|{L}']['verdict']
    if any(v(m, 'L3') == 'Supported' for m in models):
        thesis = 'The claim holds'
    elif any(v(m, L) == 'Supported' for m in models for L in ('L1', 'L2')):
        thesis = 'Mixed? (needs the wrong-house gate, not computed here)'
    elif all(v(m, 'L2') == 'Rejected' and v(m, 'L3') == 'Rejected' for m in models):
        thesis = 'The claim fails'
    else:
        thesis = 'Inconclusive'
    return H, thesis
