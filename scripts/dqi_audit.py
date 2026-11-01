"""DQI audit: recompute DQI at lock using the PRODUCTION utils.dqi.calculate_dqi on each lock snapshot,
join to actual runs (dataset_teams.csv), test each status vs the rest. ASCII only.
Writes reports/season_2026_dqi_audit.md"""
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from utils.dqi import calculate_dqi  # noqa: E402
from build_season_dataset import load_lock  # noqa: E402
from season_signal_audit import clus_diff, md_table  # noqa: E402

D = os.path.join(ROOT, "data", "season_2026")


def main():
    T = pd.read_csv(os.path.join(D, "dataset_teams.csv"))
    rows = []
    for ds in sorted(T.date.unique()):
        lock, slot = load_lock(ds)
        if not lock:
            continue
        for t in lock["teams"]:
            sc, st, pos, warn = calculate_dqi(t, lock["pitchers"])
            rows.append({"date": ds, "team": t["team"], "dqi": sc, "dqi_status": st or "GATED_OUT",
                         "stored_trust": t.get("stack_trust_score"), "div": t.get("divergence")})
    Q = pd.DataFrame(rows)
    M = T.merge(Q, on=["date", "team"], how="inner")
    M = M[(M.game_type == "R") & (M.dh == 0)].copy()
    M["resid_itt"] = M.actual_runs - M.implied_total
    M["hit_itt"] = (M.actual_runs >= M.implied_total).astype(float) * 100
    M["p5"] = (M.actual_runs >= 5).astype(float) * 100
    M["p7"] = (M.actual_runs >= 7).astype(float) * 100

    L = ["# OMEGA 2026 DQI Audit (recomputed at lock with production `calculate_dqi`)\n"]
    L.append("Teams: %d team-games on %d regular-season dates. Mean runs %.2f, mean ITT %.2f, hit-ITT baseline %.1f%%.\n" %
             (len(M), M.date.nunique(), M.actual_runs.mean(), M.implied_total.mean(), M.hit_itt.mean()))
    g = M.dqi.notna()
    corr = M.loc[g, ["dqi", "stored_trust"]].dropna()
    exact = (corr.dqi == corr.stored_trust.round()).mean() if len(corr) else float("nan")
    L.append("Recompute vs stored `stack_trust_score` (gated rows, n=%d): Pearson %.3f, exact-int match %.1f%%. "
             "(Statuses below use CURRENT scoring code applied to the lock-time inputs; the live status shown on the day may "
             "differ if the code changed.)\n" % (len(corr), corr.dqi.corr(corr.stored_trust), 100 * exact))

    L.append("\n## Status vs the rest of the league\n")
    L.append("Each row = flagged teams minus all other team-games (incl. gated-out). Positive runs-ITT means beat Vegas. "
             "95% date-clustered bootstrap CIs.\n")
    out = []
    for st in ["OVERPRICED", "CAUTION", "LEVERAGE", "GATED_OUT"]:
        m = (M.dqi_status == st).values
        r = {"status": st, "n": int(m.sum()), "days": M.loc[m, "date"].nunique(),
             "hit_ITT%": "%.1f" % M.loc[m, "hit_itt"].mean() if m.any() else "n/a",
             "mean_runs": "%.2f" % M.loc[m, "actual_runs"].mean() if m.any() else "n/a"}
        for name, col in (("runs_ITT", "resid_itt"), ("hit_ITT_diff", "hit_itt"), ("p5_diff", "p5"), ("p7_diff", "p7")):
            pt, lo, hi, n = clus_diff(M[col].values, m, M.date.values)
            r[name] = "%+.2f [%+.2f, %+.2f]" % (pt, lo, hi) if n >= 5 else "n/a"
        out.append(r)
    L.append(md_table(out, ["status", "n", "days", "mean_runs", "hit_ITT%", "runs_ITT", "hit_ITT_diff", "p5_diff", "p7_diff"]) + "\n")

    L.append("\n## Continuous DQI score (gated teams only)\n")
    G = M[g].copy()
    G["bucket"] = pd.cut(G.dqi, [-1, 30, 49, 64, 81, 101], labels=["0-30", "31-49", "50-64", "65-81", "82+"])
    t = G.groupby("bucket", observed=True).agg(n=("dqi", "size"), mean_itt=("implied_total", "mean"),
                                               mean_runs=("actual_runs", "mean"), runs_itt=("resid_itt", "mean"),
                                               hit_itt=("hit_itt", "mean"), p7=("p7", "mean"))
    L.append(md_table([{"dqi_score": i, "n": r.n, "mean_ITT": "%.2f" % r.mean_itt, "mean_runs": "%.2f" % r.mean_runs,
                        "runs_minus_ITT": "%+.2f" % r.runs_itt, "hit_ITT%": "%.1f" % r.hit_itt, "p7%": "%.1f" % r.p7}
                       for i, r in t.iterrows()],
                      ["dqi_score", "n", "mean_ITT", "mean_runs", "runs_minus_ITT", "hit_ITT%", "p7%"]) + "\n")
    sp = G[["dqi", "resid_itt"]].corr(method="spearman").iloc[0, 1]
    sp2 = G[["dqi", "actual_runs"]].corr(method="spearman").iloc[0, 1]
    L.append("\nPooled Spearman (gated teams, n=%d): DQI vs runs-ITT %+.3f; DQI vs actual runs %+.3f. "
             "Note DQI includes implied total as an input, so its relation to raw runs is partly Vegas.\n" % (len(G), sp, sp2))

    L.append("\n## Does DQI add anything on top of implied total? (gated teams, OLS: runs ~ ITT + DQI)\n")
    X = np.column_stack([np.ones(len(G)), G.implied_total.values, G.dqi.values])
    y = G.actual_runs.values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    s2 = res @ res / (len(y) - 3)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    L.append("runs = %.2f + %.3f*ITT + %.4f*DQI  (SE ITT %.3f, SE DQI %.4f; t(DQI)=%.2f). Naive SEs, rows within a day are correlated, so treat as indicative.\n" %
             (beta[0], beta[1], beta[2], se[1], se[2], beta[2] / se[2]))

    path = os.path.join(ROOT, "reports", "season_2026_dqi_audit.md")
    open(path, "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
