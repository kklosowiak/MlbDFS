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

    @staticmethod
    def _compute_blended(entity, score_field='stack_score'):
        """Compute blended_rating inline without relying on the key being pre-set.

        Used inside generate() which runs BEFORE main.py's canonical blended_rating
        write block. The canonical formula is (score + attack_conf) / 2 -- identical
        to what main.py writes, so display values in the report are always consistent.

        Args:
            entity: team, pitcher, or hitter dict
            score_field: 'stack_score' for teams, 'alpha_score' for pitchers,
                         'player_score' for hitters
        """
        raw_score = entity.get(score_field, 0)
        if isinstance(raw_score, dict):
            raw_score = raw_score.get('final', 0)
        score = float(raw_score or 0)
        conf = float(entity.get('attack_conf', 0) or 0)
        return round((score + conf) / 2, 1)

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
            # NOTE: blended_rating is set by main.py CANONICAL block after this function returns.
            scored_pitchers.append(p)
            
        scored_pitchers.sort(key=lambda x: x['attack_conf'], reverse=True)

        scored_stacks = []
        for t in t_reports:
            conf, reasons = score_stack_confidence(t, p_reports)
            t['attack_conf'] = conf
            t['attack_reasons'] = reasons
            # NOTE: blended_rating is set by main.py CANONICAL block after this function returns.
            scored_stacks.append(t)
            
        # OMEGA v20.1: PARADOX Resolution Rule
        processed_games = set()
        for p in p_reports:
            if p.get('is_paradox'):
                game_key = tuple(sorted([p['team'], p['opponent']]))
                if game_key in processed_games:
                    continue
                processed_games.add(game_key)
                
                # Find the two teams in scored_stacks
                team_opp = next((t for t in scored_stacks if t['team'] == p['opponent']), None)
                team_self = next((t for t in scored_stacks if t['team'] == p['team']), None)
                
                if team_opp and team_self:
                    def get_momentum_signals(t_obj):
                        sig = 0
                        if t_obj.get("is_burst"): sig += 1
                        if t_obj.get("is_hot_run_msmi") or t_obj.get("is_hot_run_msmi_support"): sig += 1
                        return sig
                        
                    itt1 = float(team_opp.get("implied_total", 4.5) or 4.5)
                    itt2 = float(team_self.get("implied_total", 4.5) or 4.5)
                    
                    winner = None
                    if abs(itt1 - itt2) > 0.301:
                        winner = team_opp if itt1 > itt2 else team_self
                    else:
                        m1 = get_momentum_signals(team_opp)
                        m2 = get_momentum_signals(team_self)
                        if m1 != m2:
                            winner = team_opp if m1 > m2 else team_self
                        else:
                            f1 = float(team_opp.get("bullpen_fatigue", 0) or 0)
                            f2 = float(team_self.get("bullpen_fatigue", 0) or 0)
                            if f1 != f2:
                                winner = team_opp if f1 > f2 else team_self
                            else:
                                xw1 = float(team_opp.get("team_xwoba", 0) or 0)
                                xw2 = float(team_self.get("team_xwoba", 0) or 0)
                                winner = team_opp if xw1 > xw2 else team_self
                                
                    loser = team_self if winner == team_opp else team_opp
                    
                    conf_winner = float(winner.get('attack_conf', 0) or 0)
                    conf_loser = float(loser.get('attack_conf', 0) or 0)
                    
                    if conf_loser >= conf_winner:
                        val_winner = conf_winner
                        val_loser = conf_loser
                        if val_winner == val_loser:
                            winner['attack_conf'] = val_winner + 1.0
                        else:
                            winner['attack_conf'] = val_loser
                            loser['attack_conf'] = val_winner
                        
                        winner.setdefault('attack_reasons', []).append(
                            f"PARADOX: Won within-game recommendation vs {loser['team']} (higher ITT/momentum)."
                        )
                        loser.setdefault('attack_reasons', []).append(
                            f"PARADOX: Lost within-game recommendation vs {winner['team']} (lower ITT/momentum)."
                        )

        scored_stacks.sort(key=lambda x: x['attack_conf'], reverse=True)

        # OMEGA v20.3: Slate Compression Detection (Item 3)
        self.is_low_diff = False
        self.differentiation_std = 99.0
        if len(scored_stacks) >= 6:
            import statistics
            top6_confs = [float(t.get('attack_conf', 0) or 0) for t in scored_stacks[:6]]
            self.differentiation_std = round(statistics.stdev(top6_confs), 2)
            if self.differentiation_std < 5.0:
                self.is_low_diff = True

        for h in h_reports:
            team_data = next((t for t in t_reports if t['team'] == h.get('team')), None)
            opp_p = pitcher_map.get(normalize_player_name(h.get('opp_pitcher', '')))
            if not opp_p and team_data:
                opp_p = team_pitcher_map.get(team_data.get('opponent'))
            conf, reasons = self._score_hitter_confidence(h, team_data, opp_p)
            h['attack_conf'] = conf
            h['attack_reasons'] = reasons
            # NOTE: blended_rating is set by main.py CANONICAL block after this function returns.

        # OMEGA ELITE ALERTS (Highest Probability Backtested Combinations)
        alert_lines = []
        if self.is_low_diff:
            alert_lines.append(f"- ⚠️ **LOW DIFFERENTIATION WARNING**: The top stack options have highly compressed confidence scores (Std Dev: {self.differentiation_std:.2f} < 5.0). Stack selection should lean heavily on ownership, game totals, and platoon/radar alignment.")
        
        # 1. Stacks: Elite Physics + Weak Arm (66.3% hit rate)
        for t in t_reports:
            xwoba = float(t.get('team_xwoba') or 0.0)
            opp_phys = float(t.get('opp_pitcher_physics') or 50.0)
            if xwoba >= 0.330 and opp_phys <= 35.0:
                alert_lines.append(f"- 📈 **ELITE OFFENSE ALERT**: **{t['team']}** stack meets the **Elite Physics + Weak Arm** combo (xwOBA: {xwoba:.3f} vs. {t.get('opp_pitcher')}'s PHY: {opp_phys:.1f}). This combination has a **66.3% backtested hit rate** for scoring 4+ runs.")

        # 2. Stacks: Gassed Bullpen Attack (+8.0 pts)
        for t in t_reports:
            bp = float(t.get('bullpen_fatigue') or 0.0)
            outs = float(t.get('opp_pitcher_outs') or 18.0)
            xwoba = float(t.get('team_xwoba') or 0.0)
            if bp >= 75.0 and outs <= 15.5 and xwoba >= 0.315:
                alert_lines.append(f"- 🔥 **GASSED BULLPEN ATTACK**: **{t['team']}** targets short-leash starter {t.get('opp_pitcher')} (Outs Line: {outs}) and an exhausted bullpen (Fatigue: {bp:.1f}%). High expectation of late-inning run scoring (+8.0 pts boost).")

        # 3. Stacks: Anti-Chalk Matchup Mismatch (+10.0 pts)
        for t in t_reports:
            if t.get('is_anti_chalk_smash'):
                alert_lines.append(f"- ⚓ **ANTI-CHALK SMASH**: **{t['team']}** targets a starting pitcher with hidden physical or market vulnerabilities. Backtested as an elite mismatch target (+10.0 pts boost).")

        # 4. Stacks: DQI Trust (80+ DQI / 14% Div / 4.2 ITT)
        for t in t_reports:
            dqi = int(t.get('dqi_score') or 0)
            div = int(t.get('divergence') or 0)
            itt = float(t.get('implied_total') or 0.0)
            if dqi >= 80 and div >= 14 and itt >= 4.2:
                alert_lines.append(f"- 🟢 **DQI TRUST COMBO**: **{t['team']}** stack passes all DQI Trust Gates (DQI: {dqi} | Div: {div:+d}% | ITT: {itt:.2f}). Highly reliable sharp consensus.")

        # 5. Pitchers: Low-Ceiling + Hazard Shelling (100% Shelling Rate)
        for p in p_reports:
            if p.get('is_low_ceiling') and p.get('is_hazard'):
                alert_lines.append(f"- 🚨 **PITCHER SHELLING ALERT**: Opposing starter **{p['pitcher']}** has a **Low-Ceiling + Power Hazard** combo (Low strikeout upside facing high-power xwOBA lineup). This combo is **5-for-5 (100%)** at predicting pitchers getting shelled.")

        # 6. Pitchers: True Talent + High Walks Fade (-25.0 pts)
        for p in p_reports:
            if p.get('walks_penalty') and p.get('true_talent_penalty'):
                alert_lines.append(f"- 📉 **TRUE TALENT & WALKS FADE**: Opposing starter **{p['pitcher']}** suffers from control issues and poor underlying sabermetrics (Walks Penalty + True Talent Penalty = -25.0 pts reduction). Stack against them immediately.")

        # 7. Pitchers: Trap Fade + Institutional Anchor (-10% Multiplier)
        for p in p_reports:
            if p.get('is_trap') and p.get('divergence', 0) < -10:
                alert_lines.append(f"- 📉 **SHARP TRAP FADE**: Starter **{p['pitcher']}** is a public trap experiencing heavy sharp money fade (Divergence: {p['divergence']}%). Institutional Anchor penalty active.")

        # OMEGA v21.1: Pitchers: High Bust Risk Alert (Volatile + Low Ceiling)
        for p in p_reports:
            if p.get('is_high_bust_risk'):
                alert_lines.append(f"- 🔴 **HIGH BUST RISK WARNING**: **{p['pitcher']}** has both **is_volatile** and **is_low_ceiling** pregame signals. Backtesting shows a success rate of only **16.1%** (N=31). Proceed with extreme caution.")

        # OMEGA v21.1: Pitchers: Outlier-Driven Form Warning
        for p in p_reports:
            if p.get('is_outlier_driven'):
                alert_lines.append(f"- ⚠️ **OUTLIER-DRIVEN FORM WARNING**: **{p['pitcher']}** recent ERA ({p.get('recent_era')}) is driven by a single outlier start. Ex-best ERA is **{p.get('recent_era_ex_best')}**, indicating a hidden slump.")

        lines = []
        lines.append(f"# 🔥 OMEGA Daily Attack Plan")
        lines.append(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p ET')}")
        lines.append("")
        lines.append("> [!TIP]")
        lines.append("> This Attack Plan evaluates all stacks and pitchers on a strict Confidence scale (0-100%). It ignores raw Omega scores and builds comprehensive arguments based on Physics, Platoon Edges, Traps, Recent Form, and Market Divergence.")
        lines.append("")
        
        if alert_lines:
            lines.append("---")
            lines.append("")
            lines.append("## ⚡ OMEGA ELITE COMBO ALERTS")
            lines.append("> [!IMPORTANT]")
            lines.append("> The following high-probability backtested combinations have been detected on today's slate:")
            lines.append("")
            for al in alert_lines:
                lines.append(al)
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
            blended_display = best_t.get('blended_rating') or self._compute_blended(best_t, 'stack_score')
            lines.append(f"### 🏟️ Lock Stack: {best_t['team']} (Blended: {blended_display} | CONF: {best_t['attack_conf']}% | Ω: {best_t.get('stack_score', 0)})")
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
            blended_display = t.get('blended_rating') or self._compute_blended(t, 'stack_score')
            lines.append(f"### {i}. {t['team']} (Blended: {blended_display} | CONF: {t['attack_conf']}% | Omega: {t.get('stack_score', 0)})")
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

        lines.append("## 🎯 Physics & Market Pivots")
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
                
        if p.get('is_sharp') or p.get('is_shark'):
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
            
        if t.get('is_shark') or t.get('is_sharp'):
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
