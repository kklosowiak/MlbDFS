import os
import datetime
from config import config
from utils.normalization import normalize_player_name

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

        # 1. Map Opponents
        pitcher_map = {normalize_player_name(p['pitcher']): p for p in p_reports}
        team_pitcher_map = {p['team']: p for p in p_reports}
        
        # 2. Score Pitchers
        scored_pitchers = []
        for p in p_reports:
            conf, reasons = self._score_pitcher_confidence(p, t_reports)
            p['attack_conf'] = conf
            p['attack_reasons'] = reasons
            scored_pitchers.append(p)
            
        scored_pitchers.sort(key=lambda x: x['attack_conf'], reverse=True)

        # 3. Score Stacks
        scored_stacks = []
        for t in t_reports:
            conf, reasons = self._score_stack_confidence(t, p_reports)
            t['attack_conf'] = conf
            t['attack_reasons'] = reasons
            scored_stacks.append(t)
            
        scored_stacks.sort(key=lambda x: x['attack_conf'], reverse=True)

        # 3b. Score Hitters (attack_conf for CONF column + one-off decisions)
        for h in h_reports:
            team_data = next((t for t in t_reports if t['team'] == h.get('team')), None)
            opp_p = pitcher_map.get(normalize_player_name(h.get('opp_pitcher', '')))
            if not opp_p and team_data:
                opp_p = team_pitcher_map.get(team_data.get('opponent'))
            conf, reasons = self._score_hitter_confidence(h, team_data, opp_p)
            h['attack_conf'] = conf
            h['attack_reasons'] = reasons

        # 4. Generate Report
        lines = []
        lines.append(f"# 🔥 OMEGA Daily Attack Plan")
        lines.append(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p ET')}")
        lines.append("")
        lines.append("> [!TIP]")
        lines.append("> This Attack Plan evaluates all stacks and pitchers on a strict Confidence scale (0-100%). It ignores raw Omega scores and builds comprehensive arguments based on Physics, Platoon Edges, Traps, Recent Form, and Market Divergence.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 4a. The Ultimate Suggestion
        lines.append("## 👑 The Ultimate Suggestion")
        best_p1 = scored_pitchers[0] if len(scored_pitchers) > 0 else None
        best_p2 = scored_pitchers[1] if len(scored_pitchers) > 1 else None
        best_t = scored_stacks[0] if scored_stacks else None
        
        if best_t:
            lines.append(f"### 🏟️ Lock Stack: {best_t['team']} ({best_t['attack_conf']}% Confidence)")
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

        # 4b. Top 5 Stacks
        lines.append("## 🏟️ Core Stacks (Top 5)")
        lines.append("")
        for i, t in enumerate(scored_stacks[:5], 1):
            lines.append(f"### {i}. {t['team']} ({t['attack_conf']}% Confidence)")
            for r in t['attack_reasons']:
                lines.append(f"- {r}")
            lines.append("")

        # 4c. Top 5 Pitchers
        lines.append("## ⚾ Core Pitchers (Top 5)")
        lines.append("")
        for i, p in enumerate(scored_pitchers[:5], 1):
            lines.append(f"### {i}. {p['pitcher']} ({p['attack_conf']}% Confidence)")
            for r in p['attack_reasons']:
                lines.append(f"- {r}")
            lines.append("")

        # 4d. Vegas Trap & Leverage Pivot
        lines.append("---")
        lines.append("## 🚨 Vegas Traps (Hard Fades)")
        traps = [p for p in p_reports if p.get('is_trap') or p.get('divergence', 0) < -15]
        if traps:
            for p in traps[:3]:
                trap_reason = p.get('trap_type') or 'Sharp Market Fade'
                lines.append(f"- **{p['pitcher']}**: Vegas is trapping the public here. They have a `{trap_reason}` designation.")
        else:
            lines.append("- *No obvious Vegas traps detected today.*")
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

    def _score_pitcher_confidence(self, p, t_reports):
        conf = 50
        reasons = []
        
        # Form
        if p.get('form_status') == 'SURGING':
            conf += 15
            reasons.append(f"🔥 SURGING: Elite recent form with {p.get('recent_k9')} K/9 and {p.get('recent_era')} ERA over last 3 starts.")
        elif p.get('form_status') == 'COLD':
            conf -= 20
            reasons.append(f"🧊 COLD: Pitcher is in a major slump ({p.get('recent_era')} ERA last 3 starts).")
            
        # Physics
        siera = p.get('physics_score', 0)
        if siera >= 20:
            conf += 15
            reasons.append(f"Elite underlying Physics profile (Score: {siera:.1f}).")
        elif siera < 10:
            conf -= 15
            reasons.append(f"Weak underlying Physics profile (Score: {siera:.1f}).")
            
        # Trap / Paradox
        if p.get('is_trap'):
            conf -= 30
            reasons.append(f"🚨 TRAP: Flagged as a Vegas trap ({p.get('trap_type')}). Sharp money is fading.")
        if p.get('is_paradox'):
            conf -= 25
            reasons.append(f"⚠️ PARADOX: Good pitcher, but facing an absolutely lethal lineup. Fade.")
            
        # Matchup
        opp = p.get('opponent')
        opp_t = next((t for t in t_reports if t['team'] == opp), None)
        if opp_t:
            if opp_t['stack_score'] > 80:
                conf -= 15
                reasons.append(f"Dangerous Matchup: Facing a Top-Tier Stack in the {opp}.")
            elif opp_t['stack_score'] < 50:
                conf += 15
                reasons.append(f"Elite Matchup: Facing a bottom-tier opposing lineup ({opp}).")
                
        # Market
        if p.get('is_sharp') or p.get('is_shark') or p.get('is_whale'):
            conf += 10
            reasons.append("Institutional/Sharp money is backing this pitcher today.")
            
        # Output bounds checking
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
            
        # PHY Override
        if t.get('is_physics_override'):
            conf += 15
            reasons.append("⚡ PHY OVERRIDE: Market is undervaluing this team's true hitting ceiling.")
            
        # Market
        if t.get('is_shark') or t.get('is_whale') or t.get('is_sharp'):
            conf += 15
            reasons.append("Institutional/Sharp money is heavily backing this stack.")
            
        if t.get('divergence', 0) >= 15:
            conf += 10
            reasons.append(f"🟢 OVER-DIVERGENCE: Market line is moving heavily in their favor.")
            
        # Matchup / Opposing Pitcher
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
                
        # Bullpen Fatigue
        bp = t.get('bullpen_fatigue', 0)
        if bp >= 85 or t.get('is_gassed'):
            conf += 10
            reasons.append(f"🔥 GASSED BP: Opposing bullpen is exhausted. Great late-inning ceiling.")
            
        # Output bounds checking
        if not reasons:
            reasons.append("Neutral metrics across the board.")
            
        return max(0, min(100, conf)), reasons

    def _score_hitter_confidence(self, h, team_data, opp_pitcher):
        from utils.hitter_confidence import score_hitter_confidence
        return score_hitter_confidence(h, team_data, opp_pitcher)
