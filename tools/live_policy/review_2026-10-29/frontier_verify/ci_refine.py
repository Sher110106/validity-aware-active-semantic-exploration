import importlib.util, sys
spec = importlib.util.spec_from_file_location("pt", "/tmp/cvp_verify_step7/permtest_lib.py")
pt = importlib.util.module_from_spec(spec); spec.loader.exec_module(pt)
import numpy as np
def p_at(arm, metric, d): return pt.test(pt.groups(arm, metric, shift=d))[1]
for arm in ("official", "placebo"):
    for metric in ("auc60", "auc50"):
        obs = pt.stat_of(pt.groups(arm, metric))
        grid = np.linspace(obs - 0.12, obs + 0.12, 24001)
        ps = np.array([p_at(arm, metric, d) for d in grid])
        for thr, lab in ((lambda p: p > 0.05, "p>0.05"), (lambda p: p >= 0.05, "p>=0.05")):
            keep = grid[thr(ps)]
            print(arm, metric, lab, "CI ~ [%.5f, %.5f]" % (keep.min(), keep.max()), "min p on grid", ps.min())
        # achievable p values
        print("  distinct p near edges:", sorted(set(np.round(ps,4)))[:6])
