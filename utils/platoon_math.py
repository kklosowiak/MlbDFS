"""Shared platoon multiplier (team stacks + hitter scoring)."""


def compute_platoon_multiplier(hitter_profile, pitch_hand):
    """
    Bayesian blend of 2026 vs 2025 OPS split ratios vs opposing pitcher hand.
    Returns 1.0 when data is insufficient.
    """
    if not pitch_hand or not hitter_profile:
        return 1.0

    opp_hand = str(pitch_hand).upper()
    overall_ops = float(hitter_profile.get("ops", 0.720) or 0.720)
    if overall_ops <= 0.200:
        overall_ops = 0.720

    if opp_hand == "L":
        split_ops = float(hitter_profile.get("vs_left_ops", 0.0) or 0.0)
        split_pa = int(hitter_profile.get("vs_left_pa", 0) or 0)
        split_ops_2025 = float(hitter_profile.get("vs_left_ops_2025", 0.0) or 0.0)
        split_pa_2025 = int(hitter_profile.get("vs_left_pa_2025", 0) or 0)
        split_ops_other_2025 = float(hitter_profile.get("vs_right_ops_2025", 0.0) or 0.0)
        split_pa_other_2025 = int(hitter_profile.get("vs_right_pa_2025", 0) or 0)
    else:
        split_ops = float(hitter_profile.get("vs_right_ops", 0.0) or 0.0)
        split_pa = int(hitter_profile.get("vs_right_pa", 0) or 0)
        split_ops_2025 = float(hitter_profile.get("vs_right_ops_2025", 0.0) or 0.0)
        split_pa_2025 = int(hitter_profile.get("vs_right_pa_2025", 0) or 0)
        split_ops_other_2025 = float(hitter_profile.get("vs_left_ops_2025", 0.0) or 0.0)
        split_pa_other_2025 = int(hitter_profile.get("vs_left_pa_2025", 0) or 0)

    ratio_2026 = split_ops / overall_ops if overall_ops > 0 and split_ops > 0 else 1.0

    ratio_2025 = 1.0
    has_2025 = False
    if (split_pa_2025 + split_pa_other_2025) >= 40 and split_ops_2025 > 0:
        total_pa_2025 = split_pa_2025 + split_pa_other_2025
        overall_ops_2025 = (
            (split_ops_2025 * split_pa_2025) + (split_ops_other_2025 * split_pa_other_2025)
        ) / total_pa_2025
        if overall_ops_2025 > 0.200:
            ratio_2025 = split_ops_2025 / overall_ops_2025
            has_2025 = True

    weight_2026 = min(1.0, split_pa / 100.0)

    if has_2025:
        platoon_multiplier = (weight_2026 * ratio_2026) + ((1.0 - weight_2026) * ratio_2025)
    elif split_pa >= 20:
        platoon_multiplier = (weight_2026 * ratio_2026) + ((1.0 - weight_2026) * 1.0)
    else:
        platoon_multiplier = 1.0

    return max(0.70, min(1.30, platoon_multiplier))
