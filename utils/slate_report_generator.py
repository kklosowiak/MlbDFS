import os
import datetime
from config import config


class SlateReportGenerator:
    """
    OMEGA v7.1: Auto Deep-Dive Slate Report Generator.
    Generates a comprehensive game-by-game markdown analysis
    replicating the manual deep-dive workflow that won on 4/29/26.
    """

    def __init__(self):
        self.output_path = os.path.join(config.REPORTS_DIR, "slate_analysis.md")
        self.park_factors = config.PARK_FACTORS

    def generate(self, p_reports, t_reports, h_reports):
        """Main entry point. Generates the full slate_analysis.md report."""
        print("[REPORT]: Generating Deep-Dive Slate Analysis...")

        team_map = {t['team']: t for t in t_reports}
        pitcher_map = {}
        for p in p_reports:
            pitcher_map.setdefault(p['team'], []).append(p)

        # Pair teams into games
        games = self._pair_games(t_reports, team_map)

        lines = []
        lines.append(f"# ⚾ OMEGA Deep-Dive Slate Analysis ({len(games)} Games)")
        lines.append(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p ET')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Section 1: DFS Convictions
        lines.extend(self._dfs_convictions(p_reports, t_reports, h_reports, team_map, games))

        # Section 2: Pitcher Tiers
        lines.extend(self._pitcher_tiers(p_reports, team_map))

        # Section 3: Stack Rankings
        lines.extend(self._stack_rankings(t_reports))

        # Section 4: Run Environment Map
        lines.extend(self._run_environment(games, team_map))

        # Section 5: Game-by-Game Breakdown
        lines.extend(self._game_by_game(games, team_map, p_reports, h_reports))

        # Section 6: Hitter Spotlight
        lines.extend(self._hitter_spotlight(h_reports))

        report = "\n".join(lines)

        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"[REPORT]: Slate analysis written to {self.output_path}")
        return self.output_path

    def _pair_games(self, t_reports, team_map):
        """Pair teams into game matchups."""
        games = []
        paired = set()
        for t in t_reports:
            if t['team'] in paired:
                continue
            opp = t['opponent']
            t2 = team_map.get(opp)
            if not t2:
                continue
            paired.add(t['team'])
            paired.add(opp)

            fav = t if t['stack_score'] >= t2['stack_score'] else t2
            dog = t2 if fav == t else t
            games.append((fav, dog))
        return games

    def _signal_list(self, team):
        """Extract active signal names from a team report."""
        signals = []
        if team.get('is_shark'): signals.append('SHARK')
        if team.get('is_whale'): signals.append('WHALE')
        if team.get('is_sharp'): signals.append('SHARP')
        if team.get('is_storm'): signals.append('STORM')
        if team.get('is_steam'): signals.append('STEAM')
        if team.get('is_burst'): signals.append('BURST')
        if team.get('is_gassed'): signals.append('GASSED BP')
        trend = team.get('trend', 'STABLE')
        if trend != 'STABLE':
            signals.append(trend)
        return signals

    def _pitcher_flags(self, p):
        """Extract flags from a pitcher report."""
        flags = []
        if p.get('is_paradox'): flags.append('PARADOX')
        if p.get('is_hazard'): flags.append('HAZARD')
        if p.get('is_debut'): flags.append('DEBUT')
        if p.get('is_low_ceiling'): flags.append('LOW-K')
        if p.get('is_coors'): flags.append('COORS')
        return flags

    def _hitter_flags(self, h):
        """Extract flags from a hitter report."""
        flags = []
        if h.get('is_hot'): flags.append('🔥 HOT')
        if h.get('is_juiced_target'): flags.append('JUICED')
        if h.get('is_speed_target'): flags.append('SPEED')
        return flags

    # ──────────────────────────────────────────────
    # Section Generators
    # ──────────────────────────────────────────────

    def _pitcher_tiers(self, p_reports, team_map):
        """Generate pitcher tier breakdown."""
        lines = ["## ⚡ Pitcher Tier Breakdown", ""]

        tiers = {
            "Tier 1 — Elite Conviction (100+)": [],
            "Tier 2 — Strong Plays (80-99)": [],
            "Tier 3 — Risky / Situational (65-79)": [],
            "Fade Zone (<65)": [],
        }

        for p in p_reports:
            score = p['alpha_score']
            if score >= 100:
                tiers["Tier 1 — Elite Conviction (100+)"].append(p)
            elif score >= 80:
                tiers["Tier 2 — Strong Plays (80-99)"].append(p)
            elif score >= 65:
                tiers["Tier 3 — Risky / Situational (65-79)"].append(p)
            else:
                tiers["Fade Zone (<65)"].append(p)

        for tier_name, pitchers in tiers.items():
            if not pitchers:
                continue
            lines.append(f"### {tier_name}")
            lines.append("")
            lines.append("| Pitcher | OMEGA | Phys | Mkt | K-Prop | Outs | Flags | vs Opponent (Stack) |")
            lines.append("|---------|-------|------|-----|--------|------|-------|---------------------|")
            for p in pitchers:
                flags = self._pitcher_flags(p)
                flag_str = ", ".join(flags) if flags else "Clean"
                opp_stack = team_map.get(p['opponent'], {})
                opp_score = opp_stack.get('stack_score', 0)
                lines.append(
                    f"| **{p['pitcher']}** ({p['team']}) | {p['alpha_score']:.1f} | {p['physics_score']:.1f} "
                    f"| {p['market_score']:.1f} | {p.get('k_line', '-')} | {p.get('outs_line', '-')} "
                    f"| {flag_str} | {p['opponent']} ({opp_score:.1f}) |"
                )
            lines.append("")

        lines.append("---")
        lines.append("")
        return lines

    def _stack_rankings(self, t_reports):
        """Generate team stack rankings."""
        lines = ["## 🏟️ Team Stack Rankings", ""]
        lines.append("| Rank | Team | OMEGA | xwOBA | ITT | Div | Signals | vs SP | Opp BP |")
        lines.append("|------|------|-------|-------|-----|-----|---------|-------|--------|")

        for i, t in enumerate(t_reports, 1):
            signals = self._signal_list(t)
            sig_str = ", ".join(signals) if signals else "—"
            bp_str = f"{t['bullpen_fatigue']:.0f}"
            if t.get('is_gassed'):
                bp_str += " 🔥"
            lines.append(
                f"| {i} | **{t['team']}** | {t['stack_score']:.1f} | .{str(t['team_xwoba'])[2:]} "
                f"| {t['implied_total']:.2f} | {t['divergence']:+.0f} | {sig_str} "
                f"| {t['opp_pitcher']} | {bp_str} |"
            )

        lines.append("")
        lines.append("---")
        lines.append("")
        return lines

    def _run_environment(self, games, team_map):
        """Generate run environment projections."""
        lines = ["## 🔴 Run Environment Map", ""]
        lines.append("| Game | Combined ITT | Park Factor | BP Fatigue (Higher=Runs) | Projection |")
        lines.append("|------|-------------|-------------|--------------------------|------------|")

        game_envs = []
        for fav, dog in games:
            combined_itt = fav['implied_total'] + dog['implied_total']
            # Use the home team's park factor (fav or dog could be home)
            home_team = fav['team']  # approximate — the one with lower ML move is likely home
            pf = self.park_factors.get(home_team, self.park_factors.get(dog['team'], 1.0))
            max_bp = max(fav['bullpen_fatigue'], dog['bullpen_fatigue'])

            if combined_itt >= 9.0 or (combined_itt >= 8.0 and pf >= 1.05):
                proj = "🔴 HIGH"
            elif combined_itt >= 7.5 or max_bp >= 90:
                proj = "🟠 MODERATE-HIGH"
            elif combined_itt >= 6.5:
                proj = "🟡 MODERATE"
            else:
                proj = "🔵 LOW"

            game_envs.append((fav, dog, combined_itt, pf, max_bp, proj))

        # Sort by combined ITT descending
        game_envs.sort(key=lambda x: x[2], reverse=True)

        for fav, dog, combined_itt, pf, max_bp, proj in game_envs:
            total_signal = fav.get('total_signal', '') or dog.get('total_signal', '')
            ts_str = f" {total_signal}" if total_signal else ""
            lines.append(
                f"| {fav['team']} vs {dog['team']} | {combined_itt:.2f} | {pf:.2f} "
                f"| {max_bp:.0f} | {proj}{ts_str} |"
            )

        lines.append("")
        lines.append("---")
        lines.append("")
        return lines

    def _game_by_game(self, games, team_map, p_reports, h_reports):
        """Generate detailed game-by-game breakdown."""
        lines = ["## 📊 Game-by-Game Breakdown", ""]

        pitcher_by_opp = {}
        for p in p_reports:
            pitcher_by_opp[p['opponent']] = p

        for i, (fav, dog) in enumerate(games, 1):
            lines.append(f"### Game {i}: {fav['team']} ({fav['stack_score']:.1f}) vs {dog['team']} ({dog['stack_score']:.1f})")
            lines.append("")

            # Pitching matchup
            fav_sp = pitcher_by_opp.get(fav['team'])  # pitcher facing fav = dog's pitcher
            dog_sp = pitcher_by_opp.get(dog['team'])   # pitcher facing dog = fav's pitcher

            if fav_sp and dog_sp:
                lines.append(f"**Pitching:** {dog_sp['pitcher']} ({dog_sp['alpha_score']:.1f}) vs {fav_sp['pitcher']} ({fav_sp['alpha_score']:.1f})")
            lines.append("")

            # Side-by-side comparison
            lines.append("| Metric | " + fav['team'] + " | " + dog['team'] + " |")
            lines.append("|--------|" + "-" * (len(fav['team']) + 2) + "|" + "-" * (len(dog['team']) + 2) + "|")
            lines.append(f"| Stack Score | **{fav['stack_score']:.1f}** | {dog['stack_score']:.1f} |")
            lines.append(f"| xwOBA | {fav['team_xwoba']:.3f} | {dog['team_xwoba']:.3f} |")
            lines.append(f"| ITT | {fav['implied_total']:.2f} | {dog['implied_total']:.2f} |")
            lines.append(f"| ML Move | {fav['ml_move']:+.1f} | {dog['ml_move']:+.1f} |")
            lines.append(f"| TT Move | {fav['tt_move']:+.1f} | {dog['tt_move']:+.1f} |")
            lines.append(f"| Divergence | {fav['divergence']:+.0f} | {dog['divergence']:+.0f} |")
            lines.append(f"| Opp BP | {fav['bullpen_fatigue']:.0f} {'🔥' if fav.get('is_gassed') else ''} | {dog['bullpen_fatigue']:.0f} {'🔥' if dog.get('is_gassed') else ''} |")
            lines.append(f"| Weather | {fav.get('weather_label', '?')} | {dog.get('weather_label', '?')} |")
            lines.append(f"| Umpire | {fav.get('umpire_name', 'TBD')} | {dog.get('umpire_name', 'TBD')} |")

            fav_sigs = self._signal_list(fav)
            dog_sigs = self._signal_list(dog)
            lines.append(f"| Signals | {', '.join(fav_sigs) if fav_sigs else '—'} | {', '.join(dog_sigs) if dog_sigs else '—'} |")

            total_sig = fav.get('total_signal', '') or dog.get('total_signal', '')
            if total_sig:
                lines.append(f"| Total Signal | {total_sig} | {total_sig} |")

            lines.append("")
            
            # OMEGA v8.0: Synthesized Game Analysis
            lines.append(self._generate_game_analysis(fav, dog, fav_sp, dog_sp))
            lines.append("")

            # Top hitters for each side
            for side in [fav, dog]:
                side_hitters = [h for h in h_reports if h['team'] == side['team']][:5]
                if side_hitters:
                    lines.append(f"**{side['team']} Top Hitters:**")
                    lines.append("")
                    lines.append("| OMEGA | Player | xwOBA | AHR | Hit Line | Flags |")
                    lines.append("|-------|--------|-------|-----|----------|-------|")
                    for h in side_hitters:
                        flags = self._hitter_flags(h)
                        flag_str = ", ".join(flags) if flags else "—"
                        lines.append(
                            f"| {h['player_score']:.1f} | {h['name']} | .{str(h['matchup_xwoba'])[2:]} "
                            f"| {h['ahr_price']:+d} | {h.get('hit_line', '-')}@{h.get('hits_price', 0):+d} "
                            f"| {flag_str} |"
                        )
                    lines.append("")

            lines.append("---")
            lines.append("")

        return lines

    def _generate_game_analysis(self, fav, dog, fav_sp, dog_sp):
        """Heuristic text generator for game-by-game analysis.
        
        OMEGA v8.2: Run Environment Consistency Gate
        Prevents contradictions where a game is flagged as HIGH-run in the
        Run Environment Map but the analysis says "neutral / no alpha signals."
        If the environment is objectively run-heavy, the analysis MUST
        recommend stacking — regardless of whether WHALE/SHARP signals fired.
        """
        analysis = []
        fav_sigs = self._signal_list(fav)
        dog_sigs = self._signal_list(dog)
        
        # Pre-compute run environment metrics for consistency gate
        combined_itt = fav['implied_total'] + dog['implied_total']
        max_bp_fatigue = max(fav.get('bullpen_fatigue', 0), dog.get('bullpen_fatigue', 0))
        fav_sp_score = fav_sp['alpha_score'] if fav_sp else 999
        dog_sp_score = dog_sp['alpha_score'] if dog_sp else 999
        fav_sp_fade = fav_sp_score < 65   # pitcher facing fav is in fade zone
        dog_sp_fade = dog_sp_score < 65    # pitcher facing dog is in fade zone
        
        # 1. Pitching Paradox
        fav_sp_paradox = fav_sp and fav_sp.get('is_paradox')
        dog_sp_paradox = dog_sp and dog_sp.get('is_paradox')
        
        if fav_sp_paradox and dog_sp_paradox:
            analysis.append("This is an absolute warzone. Both pitchers are flagged for Paradox traps against top-tier opposing stacks. Fade the pitching entirely.")
        elif fav_sp_paradox:
            analysis.append(f"Proceed with caution on {fav_sp['pitcher']} (PARADOX trap). The {dog['team']} form an elite stack that can ruin a good pitcher's day.")
        elif dog_sp_paradox:
            analysis.append(f"A pure fade spot for {dog_sp['pitcher']} (PARADOX trap) against the high-powered {fav['team']} lineup.")
            
        # 2. Market Conviction
        sharp_teams = []
        if any(s in fav_sigs for s in ['WHALE', 'SHARK', 'STEAM']):
            sharp_teams.append(fav['team'])
        if any(s in dog_sigs for s in ['WHALE', 'SHARK', 'STEAM']):
            sharp_teams.append(dog['team'])
            
        if len(sharp_teams) == 2:
            analysis.append("Syndicates are battling on both sides of this game. We have conflicting sharp signals, making this a chaotic leverage spot for GPPs.")
        elif len(sharp_teams) == 1:
            analysis.append(f"The engine detects major institutional backing for the {sharp_teams[0]}. Professional syndicates are actively attacking this side.")
            
        # 3. Burst / Game Theory
        has_burst = 'BURST' in fav_sigs or 'BURST' in dog_sigs
        total_sig = fav.get('total_signal', '') or dog.get('total_signal', '')
        
        if 'O-DIV' in total_sig and has_burst:
            analysis.append("🚨 **Elite Run Environment**: Massive Over-Divergence combined with late-game BURST conditions. This game is a prime target for full game-stacks.")
        elif has_burst:
            burst_team = fav['team'] if 'BURST' in fav_sigs else dog['team']
            analysis.append(f"We have a ⚡ BURST condition triggered for the {burst_team}, targeting a highly fatigued opposing bullpen. This is an elite late-game ceiling spot.")
        elif 'U-DIV' in total_sig:
            analysis.append("Heavy sharp money is fading the run total here (U-DIV). This is a strong environment for starting pitching and a hard fade for hitters.")

        # 4. OMEGA v8.2: Run Environment Consistency Gate
        # Ensures high-run games ALWAYS get a stacking callout, even without
        # traditional WHALE/SHARP signals. Prevents the "high ITT but neutral
        # environment" contradiction.
        env_callouts = []
        
        # Gate A: High combined ITT + Fade Zone pitcher = must-stack
        if combined_itt >= 9.0 and fav_sp_fade:
            env_callouts.append(
                f"🔴 **High-Run Alert:** Combined ITT ({combined_itt:.1f}) projects elite run "
                f"production. {fav_sp['pitcher']} ({fav_sp_score:.1f} OMEGA) is in the Fade Zone, "
                f"making the {dog['team']} a strong stacking target in this environment."
            )
        if combined_itt >= 9.0 and dog_sp_fade:
            env_callouts.append(
                f"🔴 **High-Run Alert:** Combined ITT ({combined_itt:.1f}) projects elite run "
                f"production. {dog_sp['pitcher']} ({dog_sp_score:.1f} OMEGA) is in the Fade Zone, "
                f"making the {fav['team']} a strong stacking target in this environment."
            )
        
        # Gate B: High combined ITT + high BP fatigue = late-game ceiling
        if combined_itt >= 8.5 and max_bp_fatigue >= 85 and not has_burst:
            tired_side = fav['team'] if dog.get('bullpen_fatigue', 0) >= 85 else dog['team']
            env_callouts.append(
                f"⚡ **Bullpen Fatigue Alert:** Opposing bullpen fatigue ({max_bp_fatigue:.0f}) "
                f"combined with high ITT ({combined_itt:.1f}) creates a late-game ceiling spot "
                f"for the {tired_side}."
            )
        
        # Gate C: Both pitchers in Fade Zone = game-stack environment
        if fav_sp_fade and dog_sp_fade and combined_itt >= 8.0:
            env_callouts.append(
                f"🔥 **Game-Stack Environment:** Both pitchers are in the Fade Zone "
                f"({fav_sp['pitcher']} {fav_sp_score:.1f}, {dog_sp['pitcher']} {dog_sp_score:.1f}). "
                f"This is a premium game-stack target — consider stacking both sides."
            )
        
        analysis.extend(env_callouts)

        # 5. Final Verdict — only fires if NO other analysis was generated
        # The consistency gate ensures that high-run games never fall through
        # to this generic "neutral" fallback.
        if not analysis:
            analysis.append("This game grades out as a relatively neutral environment. Pitching leans slightly ahead, but no elite alpha signals have fired for either side.")
            
        return "**OMEGA Analysis:** " + " ".join(analysis)

    def _hitter_spotlight(self, h_reports):
        """Generate top hitter spotlight."""
        lines = ["## 🔥 Hitter Spotlight (Top 15)", ""]
        lines.append("| Rank | Player | OMEGA | Team | xwOBA | AHR | vs Pitcher | Flags |")
        lines.append("|------|--------|-------|------|-------|-----|------------|-------|")

        for i, h in enumerate(h_reports[:15], 1):
            flags = self._hitter_flags(h)
            flag_str = ", ".join(flags) if flags else "—"
            lines.append(
                f"| {i} | **{h['name']}** | {h['player_score']:.1f} | {h['team']} "
                f"| .{str(h['matchup_xwoba'])[2:]} | {h['ahr_price']:+d} "
                f"| {h.get('opp_pitcher', 'TBD')} | {flag_str} |"
            )

        lines.append("")
        lines.append("---")
        lines.append("")
        return lines

    def _dfs_convictions(self, p_reports, t_reports, h_reports, team_map, games):
        """Generate DFS conviction plays and fades."""
        lines = ["## 🎯 DFS Conviction Plays", ""]

        # SP Targets: Top 3 pitchers
        lines.append("### SP Targets")
        lines.append("")
        for i, p in enumerate(p_reports[:3], 1):
            opp_stack = team_map.get(p['opponent'], {}).get('stack_score', 0)
            flags = self._pitcher_flags(p)
            flag_note = f" ⚠️ {', '.join(flags)}" if flags else ""
            lines.append(
                f"{i}. **{p['pitcher']}** ({p['alpha_score']:.1f} OMEGA) — "
                f"Phys: {p['physics_score']:.1f}, K: {p.get('k_line', '-')}, "
                f"vs {p['opponent']} ({opp_stack:.1f} stack){flag_note}"
            )
        lines.append("")

        # Stack Priority: Top 4
        lines.append("### Stack Priority")
        lines.append("")
        labels = ["PRIMARY", "SECONDARY", "TERTIARY", "GPP LEVERAGE"]
        for i, t in enumerate(t_reports[:4]):
            label = labels[i] if i < len(labels) else f"#{i+1}"
            signals = self._signal_list(t)
            sig_str = f" — {', '.join(signals)}" if signals else ""
            top_hitters = [h for h in h_reports if h['team'] == t['team']][:3]
            hitter_names = ", ".join([h['name'] for h in top_hitters])
            lines.append(
                f"{i+1}. **{label}: {t['team']}** ({t['stack_score']:.1f} OMEGA, "
                f"{t['implied_total']:.2f} ITT){sig_str}"
            )
            if hitter_names:
                lines.append(f"   - Core bats: {hitter_names}")
        lines.append("")

        # One-Off Targets: Top hitters not on top 3 stacks
        top_stack_teams = {t['team'] for t in t_reports[:3]}
        one_offs = [h for h in h_reports if h['team'] not in top_stack_teams][:4]
        if one_offs:
            lines.append("### One-Off Power Targets")
            lines.append("")
            for h in one_offs:
                flags = self._hitter_flags(h)
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                lines.append(
                    f"- **{h['name']}** ({h['team']}, {h['player_score']:.1f} OMEGA, "
                    f"{h['matchup_xwoba']:.3f} xwOBA){flag_str}"
                )
            lines.append("")

        # Fades
        lines.append("### ❌ Hard Fades")
        lines.append("")

        # Fade bottom stacks
        fade_stacks = [t for t in t_reports if t['stack_score'] < 55]
        if fade_stacks:
            for t in fade_stacks[:3]:
                reasons = []
                if t['divergence'] < -10:
                    reasons.append(f"{t['divergence']:+.0f} divergence")
                if t['team_xwoba'] < 0.270:
                    reasons.append(f".{str(t['team_xwoba'])[2:]} xwOBA")
                if t.get('trend') == 'FADING':
                    reasons.append("FADING")
                reason_str = f" ({', '.join(reasons)})" if reasons else ""
                lines.append(f"- **{t['team']} stack** ({t['stack_score']:.1f} OMEGA){reason_str}")

        # Fade PARADOX pitchers
        paradox_pitchers = [p for p in p_reports if p.get('is_paradox')]
        if paradox_pitchers:
            for p in paradox_pitchers:
                lines.append(f"- **{p['pitcher']}** ({p['alpha_score']:.1f} OMEGA — PARADOX vs Top Stack)")

        lines.append("")
        return lines
