import os
import datetime
from config import config
from utils.normalization import normalize_player_name

SHARP_FADE_DIVERGENCE = -15


class SlateReportGenerator:
    """
    OMEGA v10.5: Daily Attack Plan Generator
    Replaces generic analysis with a strict, confidence-based reasoning engine.
    """

    def __init__(self):
        self.output_path = os.path.join(config.REPORTS_DIR, "slate_analysis.md")
        self.park_factors = config.PARK_FACTORS

    def generate(self, p_reports, t_reports, h_reports):
        print("[REPORT]: Generating OMEGA Daily Attack Plan...")

        pitcher_map = {normalize_player_name(p['pitcher']): p for p in p_reports}
        team_pitcher_map = {p['team']: p for p in p_reports}
        
        scored_pitchers = []
        from utils.attack_confidence import score_pitcher_confidence, score_stack_confidence

        for p in p_reports:
            conf, reasons = score_pitcher_confidence(p, t_reports)
            p['attack_conf'] = conf
            p['attack_reasons'] = reasons
            p['blended_rating'] = round((p.get('alpha_score', 0) + conf) / 2, 1)
            scored_pitchers.append(p)
            
        scored_pitchers.sort(key=lambda x: x['attack_conf'], reverse=True)

        scored_stacks = []
        for t in t_reports:
            conf, reasons = score_stack_confidence(t, p_reports)
            t['attack_conf'] = conf
            t['attack_reasons'] = reasons
            t['blended_rating'] = round((t.get('stack_score', 0) + conf) / 2, 1)
            scored_stacks.append(t)
            
        scored_stacks.sort(key=lambda x: x['attack_conf'], reverse=True)

        for h in h_reports:
            team_data = next((t for t in t_reports if t['team'] == h.get('team')), None)
            opp_p = pitcher_map.get(normalize_player_name(h.get('opp_pitcher', '')))
            if not opp_p and team_data:
                opp_p = team_pitcher_map.get(team_data.get('opponent'))
            conf, reasons = self._score_hitter_confidence(h, team_data, opp_p)
            h['attack_conf'] = conf
            h['attack_reasons'] = reasons
            h['blended_rating'] = round((h.get('player_score', 0) + conf) / 2, 1)

        lines = []
        lines.append(f"# 🔥 OMEGA Daily Attack Plan")
        lines.append(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p ET')}")
        lines.append("")
        lines.append("> [!TIP]")
        lines.append("> This Attack Plan evaluates all stacks and pitchers on a strict Confidence scale (0-100%). It ignores raw Omega scores and builds comprehensive arguments based on Physics, Platoon Edges, Traps, Recent Form, and Market Divergence.")
        lines.append("")
        lines.append("---")
        lines.append("")

        lines.append("## 👑 The Ultimate Suggestion")
        best_p1 = scored_pitchers[0] if len(scored_pitchers) > 0 else None
        best_p2 = self._pick_sp2(scored_pitchers)
        lock_stacks = [
            t for t in scored_stacks
            if not t.get('is_trap')
            and t.get('dqi_status') != 'FADE'
            and not t.get('is_volatile')
        ]
        best_t = lock_stacks[0] if lock_stacks else (scored_stacks[0] if scored_stacks else None)
        
        if best_t:
            lines.append(f"### 🏟️ Lock Stack: {best_t['team']} (Blended: {best_t['blended_rating']} | CONF: {best_t['attack_conf']}% | Ω: {best_t.get('stack_score', 0)})")
            for r in best_t['attack_reasons']:
                lines.append(f"- {r}")
            lines.append("")

        if best_p1:
            lines.append(f"### ⚾ SP1 Lock: {best_p1['pitcher']} ({best_p1['attack_conf']}% Confidence)")
            for r in best_p1['attack_reasons']:
                lines.append(f"- {r}")
            lines.append("")

        if best_p2:
            lines.append(f"### ⚾ SP2 Lock: {best_p2['pitcher']} ({best_p2['attack_conf']}% Confidence)")
            for r in best_p2['attack_reasons']:
                lines.append(f"- {r}")
            lines.append("")
            
        lines.append("---")
        lines.append("")

        lines.append("## 🏟️ Core Stacks (Top 5)")
        lines.append("")
        for i, t in enumerate(scored_stacks[:5], 1):
            lines.append(f"### {i}. {t['team']} (Blended: {t['blended_rating']} | CONF: {t['attack_conf']}% | Ω: {t.get('stack_score', 0)})")
            for r in t['attack_reasons']:
                lines.append(f"- {r}")
            lines.append("")

        core_pitchers = [p for p in scored_pitchers if not p.get('sharp_fade') and not p.get('is_trap')][:5]
        if not core_pitchers:
            core_pitchers = scored_pitchers[:5]
        lines.append("## ⚾ Core Pitchers (Top 5)")
        lines.append("")
        for i, p in enumerate(core_pitchers, 1):
            tag = " ⚠️ split signal" if p.get('sharp_fade') else ""
            lines.append(f"### {i}. {p['pitcher']} ({p['attack_conf']}% Confidence){tag}")
            for r in p['attack_reasons']:
                lines.append(f"- {r}")
            lines.append("")

        lines.append("---")
        prop_traps = [p for p in p_reports if p.get('is_trap')]
        lines.append("## 🚨 TRAP SP (Stack Against)")
        if prop_traps:
            for p in prop_traps[:5]:
                trap_reason = p.get('trap_type') or 'Vulnerable'
                lines.append(
                    f"- **{p['pitcher']}**: Prop TRAP ({trap_reason}). Attack opposing hitters."
                )
        else:
            lines.append("- *No prop TRAP pitchers flagged today.*")
        lines.append("")

        sharp_fades = [
            p for p in p_reports
            if p.get('sharp_fade') and not p.get('is_trap')
        ]
        lines.append("## 📉 Sharp Fade (SP Caution)")
        if sharp_fades:
            for p in sharp_fades[:5]:
                div = p.get('divergence', 0)
                lines.append(
                    f"- **{p['pitcher']}**: Sharp money fading this side ({div:+d}% divergence). "
                    f"Playable with caution — not a prop TRAP."
                )
        else:
            lines.append("- *No sharp-fade SP caution flags today.*")
        lines.append("")

        lines.append("## 🎯 Leverage Pivots (GPP Tournaments)")
        pivots = [t for t in t_reports if t.get('is_physics_override')]
        if pivots:
            for t in pivots[:3]:
                xwoba_str = "{:.3f}".format(t.get('team_xwoba', 0))[1:]
                lines.append(f"- **{t['team']}**: `⚡ PHY OVERRIDE`. Elite underlying hit physics (.{xwoba_str} xwOBA) that the market is currently undervaluing.")
        else:
            lines.append("- *No extreme physics overrides detected today.*")

        report = "\n".join(lines)
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(report)
            
        print(f"[REPORT]: Attack Plan written to {self.output_path}")
        return self.output_path

    def _pick_sp2(self, scored_pitchers):
        if len(scored_pitchers) < 2:
            return None
        for p in scored_pitchers[1:6]:
            if not p.get('sharp_fade') and not p.get('is_trap'):
                return p
        return scored_pitchers[1]

    def _score_pitcher_confidence(self, p, t_reports):
        conf = 50
        reasons = []
        
        if p.get('form_status') == 'SURGING':
            conf += 15
            reasons.append(f"🔥 SURGING: Elite recent form with {p.get('recent_k9')} K/9 and {p.get('recent_era')} ERA over last 3 starts.")
        elif p.get('form_status') == 'COLD':
            conf -= 20
            reasons.append(f"🧊 COLD: Pitcher is in a major slump ({p.get('recent_era')} ERA last 3 starts).")
            
        siera = p.get('physics_score', 0)
        if siera >= 20:
            conf += 15
            reasons.append(f"Elite underlying Physics profile (Score: {siera:.1f}).")
        elif siera < 10:
            conf -= 15
            reasons.append(f"Weak underlying Physics profile (Score: {siera:.1f}).")
            
        if p.get('is_trap'):
            conf -= 30
            reasons.append(f"🚨 TRAP: Flagged as a Vegas trap ({p.get('trap_type')}). Sharp money is fading.")
        elif p.get('sharp_fade'):
            div = int(p.get('divergence', 0) or 0)
            conf -= 12
            reasons.append(
                f"📉 Sharp market fade ({div:+d}% divergence) — playable with caution, not a prop TRAP."
            )
            opp = p.get('opponent')
            opp_t = next((t for t in t_reports if t['team'] == opp), None)
            if p.get('form_status') == 'SURGING' and opp_t and opp_t.get('stack_score', 100) < 50:
                conf += 5
                reasons.append("Form + soft opponent offset part of the fade signal.")
        if p.get('is_paradox'):
            conf -= 25
            reasons.append(f"⚠️ PARADOX: Good pitcher, but facing an absolutely lethal lineup. Fade.")
            
        opp = p.get('opponent')
        opp_t = next((t for t in t_reports if t['team'] == opp), None)
        if opp_t:
            if opp_t['stack_score'] > 80:
                conf -= 15
                reasons.append(f"Dangerous Matchup: Facing a Top-Tier Stack in the {opp}.")
            elif opp_t['stack_score'] < 50:
                conf += 15
                reasons.append(f"Elite Matchup: Facing a bottom-tier opposing lineup ({opp}).")
                
        if p.get('is_sharp') or p.get('is_shark') or p.get('is_whale'):
            conf += 10
            reasons.append("Institutional/Sharp money is backing this pitcher today.")
            
        if not reasons:
            reasons.append("Neutral metrics across the board.")
            
        return max(0, min(100, conf)), reasons

    def _score_stack_confidence(self, t, p_reports):
        conf = 50
        reasons = []
        
        xwoba = t.get('team_xwoba', 0)
        if xwoba >= 0.320:
            conf += 20
            reasons.append(f"Elite Team Physics: Massive .{str(xwoba)[2:5]} xwOBA projection.")
        elif xwoba < 0.290:
            conf -= 15
            reasons.append(f"Weak Team Physics: Poor .{str(xwoba)[2:5]} xwOBA projection.")
            
        if t.get('is_physics_override'):
            conf += 15
            reasons.append("⚡ PHY OVERRIDE: Market is undervaluing this team's true hitting ceiling.")
            
        if t.get('is_shark') or t.get('is_whale') or t.get('is_sharp'):
            conf += 15
            reasons.append("Institutional/Sharp money is heavily backing this stack.")
            
        if t.get('divergence', 0) >= 15:
            conf += 10
            reasons.append(f"🟢 OVER-DIVERGENCE: Market line is moving heavily in their favor.")
            
        opp_p_name = t.get('opp_pitcher')
        opp_p = next((p for p in p_reports if p['pitcher'] == opp_p_name), None)
        if opp_p:
            if opp_p.get('is_trap'):
                conf += 15
                reasons.append(f"Attacking a Vegas Trap: Opposing pitcher {opp_p_name} is a known Trap.")
                trap_note = opp_p.get("trap_prop_note")
                if trap_note:
                    reasons.append(trap_note)
            if opp_p.get('form_status') == 'COLD':
                conf += 15
                reasons.append(f"Attacking Cold Pitching: {opp_p_name} has a {opp_p.get('recent_era')} ERA over last 3 starts.")
            if opp_p.get('physics_score', 0) > 20 and not opp_p.get('is_trap'):
                conf -= 20
                reasons.append(f"Tough Matchup: Facing an elite underlying pitcher in {opp_p_name}.")
                
        bp = t.get('bullpen_fatigue', 0)
        if bp >= 85 or t.get('is_gassed'):
            conf += 10
            reasons.append(f"🔥 GASSED BP: Opposing bullpen is exhausted. Great late-inning ceiling.")
            
        if not reasons:
            reasons.append("Neutral metrics across the board.")
            
        return max(0, min(100, conf)), reasons

    def _score_hitter_confidence(self, h, team_data, opp_pitcher):
        from utils.hitter_confidence import score_hitter_confidence
        return score_hitter_confidence(h, team_data, opp_pitcher)
