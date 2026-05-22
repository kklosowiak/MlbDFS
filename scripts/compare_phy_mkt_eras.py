"""Side-by-side PHY/MKT display eras for teams + hitters."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.sharps_weighting import SharpsWeighting

# User screenshot slate (approx inputs from live board)
TEAM_SLATE = [
    ("Arizona Diamondbacks", 0.405, 0.410, 6.01, 18.6, 78, 15.5),
    ("New York Yankees", 0.385, 0.395, 4.69, 33.1, 72, 16.0),
    ("Los Angeles Angels", 0.378, 0.388, 4.72, 25.5, 70, 14.0),
    ("Athletics", 0.365, 0.375, 4.15, 34.1, 55, 8.0),
    ("Toronto Blue Jays", 0.340, 0.350, 3.12, 25.6, 45, 5.0),
    ("Colorado Rockies", 0.355, 0.365, 3.88, 27.4, 50, 0.0),
]

# Typical hitter spread on a slate (xwOBA from OPS heuristic often 0.33–0.45)
HITTER_SAMPLES = [
    ("Elite cap", 0.450, 320, 1.15),
    ("Strong", 0.400, 450, 1.08),
    ("Average", 0.350, 550, 1.00),
    ("Weak", 0.300, 650, 0.95),
    ("Platoon boost elite", 0.420, 300, 1.25),
]


def team_eras(sw, name, xw, conc, itt, opp_phys, pen, outs):
    r = sw.calculate_stack_score(
        name,
        ml_move=0,
        tt_move=0,
        curr_itt=itt,
        implied_total=itt,
        team_xwoba=xw,
        power_concentration=conc,
        park_factor=1.0,
        bullpen_fatigue=pen,
        opp_pitcher_physics=opp_phys,
        pitcher_outs=outs,
    )
    pr = r["physics_raw"]
    mr = r["market_raw"]
    vuln = r["vulnerability"]
    pen_b = r["bullpen_boost"]
    pillar = min(100.0, r["physics_component"] * 2.0)
    return {
        "omega": r["final"],
        "1_original_phy": round(pr * 0.40, 1),
        "1_original_mkt": round(mr * 0.20, 1),
        "2_raw_phy": pr,
        "2_raw_mkt": mr,
        "3_pillar_phy": pillar,
        "3_pillar_mkt": r["market_pillar"],
        "4_rec_phy": pr,
        "4_rec_mkt": mr,
        "xwoba": r["team_xwoba"],
        "vuln": vuln,
        "pen": pen_b,
    }


def hitter_eras(sw, label, xwoba, ahr, platoon_mult=1.0):
    xw_in = min(0.480, xwoba * platoon_mult)
    r = sw.calculate_individual_hitter_score(
        label,
        team_score=100,
        matchup_xwoba=xw_in,
        ahr_price=ahr,
        pitch_hand=None,
        hitter_splits=None,
    )
    platoon_bonus = max(0.0, min(12.0, (platoon_mult - 1.0) * 40.0)) if platoon_mult != 1.0 else 0.0
    p_comp = r["physics_component"]
    m_comp = r["market"]
    pillar = min(100.0, r["physics_component"] * 2.0)
    # Pre-pillar era (05ad1ba): physics = p_comp, market = m_comp (0-50 each)
    return {
        "omega": r["final"],
        "xwoba": r["matchup_xwoba"],
        "1_original_phy": p_comp,
        "1_original_mkt": m_comp,
        "2_raw_phy": round(min(100, p_comp * 2), 1),  # what doubling did without platoon
        "2_raw_mkt": m_comp,
        "3_pillar_phy": pillar,
        "3_pillar_mkt": r["market_pillar"],
        "4_rec_phy": round(min(100, ((r["matchup_xwoba"] - 0.280) / 0.140) * 100), 1),
        "platoon_bonus": platoon_bonus,
        "4_rec_mkt": m_comp,
    }


def print_team_table():
    sw = SharpsWeighting()
    print("\n=== TEAM STACKS — PHY/MKT by display era ===\n")
    hdr = (
        f"{'Team':<22} | {'OMEGA':>5} | "
        f"{'OldPHY':>6} {'OldMKT':>6} | "
        f"{'RawPHY':>6} {'RawMKT':>6} | "
        f"{'PilPHY':>6} {'PilMKT':>6} | "
        f"{'RecPHY':>6} {'RecMKT':>6} | xwOBA"
    )
    print(hdr)
    print("-" * len(hdr))
    for row in TEAM_SLATE:
        e = team_eras(sw, *row)
        short = row[0].replace(" Diamondbacks", "").replace(" New York", " NY").replace(" Los Angeles ", " LA ")
        print(
            f"{short:<22} | {e['omega']:5.1f} | "
            f"{e['1_original_phy']:6.1f} {e['1_original_mkt']:6.1f} | "
            f"{e['2_raw_phy']:6.1f} {e['2_raw_mkt']:6.1f} | "
            f"{e['3_pillar_phy']:6.1f} {e['3_pillar_mkt']:6.1f} | "
            f"{e['4_rec_phy']:6.1f} {e['4_rec_mkt']:6.1f} | {e['xwoba']:.3f}"
        )
    print("\nLegend:")
    print("  Old = weighted slices (physics_raw×0.40, market_raw×0.20) — why everyone looked ~40")
    print("  Raw = full 0–100 pillars (97ca9a6 fix)")
    print("  Pil = composite PHY capped at 99 + full MKT — what you see now (all 99 PHY)")
    print("  Rec = lineup power PHY + Vegas MKT (recommended)")


def print_hitter_table():
    sw = SharpsWeighting()
    print("\n=== HITTERS — PHY/MKT by display era (samples) ===\n")
    hdr = (
        f"{'Profile':<22} | {'OMEGA':>5} | "
        f"{'OldPHY':>6} {'OldMKT':>6} | "
        f"{'×2 PHY':>6} {'OldMkt':>6} | "
        f"{'PilPHY':>6} {'PilMKT':>6} | "
        f"{'RecPHY':>6} {'RecMKT':>6} | xwOBA"
    )
    print(hdr)
    print("-" * len(hdr))
    for label, xw, ahr, plat in HITTER_SAMPLES:
        e = hitter_eras(sw, label, xw, ahr, plat)
        print(
            f"{label:<22} | {e['omega']:5.1f} | "
            f"{e['1_original_phy']:6.1f} {e['1_original_mkt']:6.1f} | "
            f"{e['2_raw_phy']:6.1f} {e['2_raw_mkt']:6.1f} | "
            f"{e['3_pillar_phy']:6.1f} {e['3_pillar_mkt']:6.1f} | "
            f"{e['4_rec_phy']:6.1f} {e['4_rec_mkt']:6.1f} | {e['xwoba']:.3f}"
        )

    print("\n=== HITTERS — from archived slate (May 20) ===\n")
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "reports/archive/results_2026-05-20.json",
    )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    hitters = data.get("hitters", data.get("hitter_reports", []))
    # Re-score top 12 by player_score with stored xwOBA/AHR
    scored = []
    for h in hitters:
        xw = float(h.get("matchup_xwoba", 0.33) or 0.33)
        ahr = float(h.get("ahr_price", 500) or 500)
        e = hitter_eras(sw, h["name"], xw, ahr, 1.0)
        scored.append((h["name"], h["team"], e))
    scored.sort(key=lambda x: -x[2]["omega"])
    hdr2 = (
        f"{'Hitter':<18} {'Tm':<4} | "
        f"{'OldPHY':>6} {'OldMKT':>6} | {'PilPHY':>6} {'PilMKT':>6} | "
        f"{'RecPHY':>6} | xwOBA | storedPHY"
    )
    print(hdr2)
    print("-" * len(hdr2))
    for name, team, e in scored[:15]:
        stored = next(
            (h["physics_score"] for h in hitters if h["name"] == name),
            "?",
        )
        tm = (team or "")[:4]
        print(
            f"{name[:18]:<18} {tm:<4} | "
            f"{e['1_original_phy']:6.1f} {e['1_original_mkt']:6.1f} | "
            f"{e['3_pillar_phy']:6.1f} {e['3_pillar_mkt']:6.1f} | "
            f"{e['4_rec_phy']:6.1f} | {e['xwoba']:.3f} | {stored}"
        )

    # Distribution: how many hitters hit pillar 100 on archive xwOBA
    counts = {"p_comp_50": 0, "pillar_100": 0, "xwoba_ge_42": 0, "n": 0}
    for h in hitters:
        xw = float(h.get("matchup_xwoba", 0.33) or 0.33)
        e = hitter_eras(sw, h["name"], xw, float(h.get("ahr_price", 500) or 500), 1.0)
        counts["n"] += 1
        if e["1_original_phy"] >= 49.9:
            counts["p_comp_50"] += 1
        if e["3_pillar_phy"] >= 99.9:
            counts["pillar_100"] += 1
        if xw >= 0.420:
            counts["xwoba_ge_42"] += 1
    print(f"\nArchive slate ({counts['n']} hitters):")
    print(f"  p_comp maxed (50/50 scale): {counts['p_comp_50']}")
    print(f"  physics_pillar = 100:       {counts['pillar_100']}")
    print(f"  matchup_xwoba >= 0.420:     {counts['xwoba_ge_42']}")

    print("\nLegend:")
    print("  OldPHY = p_comp 0–50 (original hitter column)")
    print("  PilPHY = min(100, p_comp×2 + platoon bonus) — caps at 100 when xwOBA high")
    print("  RecPHY = xwOBA mapped 0–100 (same scale as team physics_raw)")


if __name__ == "__main__":
    print_team_table()
    print_hitter_table()
