import os

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(base_dir, "templates", "index.html")
    
    if not os.path.exists(target_path):
        print(f"[ERROR]: Target file does not exist: {target_path}")
        return
        
    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    start_tag = "<!-- 📖 SYSTEM HANDBOOK MODAL OVERLAY -->"
    end_tag = "</div>\\n</body>"
    
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)
    
    if start_idx == -1 or end_idx == -1:
        print("[ERROR]: Could not find handbook overlay tags inside index.html")
        return
        
    # We want to keep the closing body and html tags, so end of replacement is right before \n</body>
    end_idx += 6 # Include </div>\n (which is length of </div>\n in the code: '</div>\\n')
    
    replacement_html = """<!-- 📖 SYSTEM HANDBOOK MODAL OVERLAY -->
    <div class="handbook-modal" id="handbook-modal">
        <button class="handbook-close-btn" onclick="closeHandbook()">CLOSE HANDBOOK ×</button>
        
        <div class="handbook-sidebar">
            <h2>🔱 OMEGA Handbook</h2>
            <p style="font-size: 0.72rem; color: var(--text-secondary); margin: -10px 0 10px 0; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">GPP OPERATIONAL GUIDE</p>
            <hr style="border: 0; border-top: 1px solid var(--border); width: 100%; margin: 0 0 10px 0;">
            
            <ul class="handbook-toc">
                <li class="handbook-toc-item active" onclick="scrollToHandbookSection('sec-philosophy')">1. The Battle of Liquidity & Physics</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-pitchers')">2. Starting Pitchers Matrix</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-hitters')">3. Hitters & Power Rankings</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-stacks')">4. Team Stacks & Bullpens</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-environment')">5. Ballpark Weather Matrix</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-definitions')">6. Cockpit Signals Glossary</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-playbook')">7. Our GPP Drafting Playbook</li>
            </ul>
        </div>
        
        <div class="handbook-content-area">
            <!-- SECTION 1 -->
            <div id="sec-philosophy" style="margin-bottom: 60px; padding-top: 20px;">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>1.</span> The Battle of Liquidity & Physics
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    Every single day in Major League Baseball, two massive forces collide. On one side are millions of casual, retail sports bettors and DFS players, submitting rosters based on last night’s highlights, name recognition, and stagnant, outdated seasonal box scores. On the other side is a network of secretive, multi-million-dollar sharp betting syndicates, using advanced proprietary algorithms to move lines and dump massive amounts of liquidity into the market.
                </p>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    <strong>OMEGA v9.0 is your personal intelligence terminal in this battle.</strong> It does not trust simple seasonal averages, and it does not follow the crowd. Instead, OMEGA acts as a high-frequency probability filter. By constantly monitoring the global sports betting markets and cross-referencing them against the cold, hard physics of the playing field—such as real-time exit velocities, barometric ballpark pressure, and umpire strike zones—OMEGA isolates the exact mathematical gaps where the public is walking into a trap and the smart money is preparing to cash in.
                </p>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    This handbook is your plain-English roadmap to reading the terminal, understanding the signals, and constructing tournament-winning GPP lineups that have a systematic, mathematical edge over the field.
                </p>
            </div>
            
            <!-- SECTION 2 -->
            <div id="sec-pitchers" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>2.</span> The Starting Pitchers Matrix
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    This is your pitching anchor terminal. It helps you identify high-floor "Core" pitchers to build around and high-leverage "Pivots" to separate your lineups from the crowd.
                </p>
                <ul style="font-size: 1.0rem; line-height: 1.8; color: rgba(255,255,255,0.85); padding-left: 20px;">
                    <li><strong style="color:var(--accent-blue);">OMEGA (Final Score):</strong> The definitive quantitative score of the pitcher (on a scale of 0 to 110+). A score of <strong>100+ is elite (blue)</strong>, and <strong>85+ is high-quality (green)</strong>.</li>
                    <li><strong style="color:var(--accent-blue);">PHY (Physics Score):</strong> Represents the pitcher's raw physical talent and stuff, combining their pitching command, strikeout rates, and velocity trends into a simple 0-25 score. **Higher is better.**</li>
                    <li><strong style="color:var(--accent-blue);">MKT (Market Score):</strong> The betting market's confidence in this pitcher. It tracks line movement, odds shifts, and sharp betting volume. A **high Market score (purple)** means the smartest money in the world is heavily backing this pitcher.</li>
                    <li><strong style="color:var(--accent-blue);">K-PROP & OUTS:</strong> The live betting lines for their Strikeouts and total Outs. The parenthesis show the odds (e.g., `+114` means a $100 bet wins $114). Use these columns to quickly find which pitchers are projected for deep, high-strikeout outings.</li>
                </ul>
            </div>
            
            <!-- SECTION 3 -->
            <div id="sec-hitters" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>3.</span> Hitters & Power Rankings
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    This matrix ranks individual batters, exposing elite players who are in premier matchups to hit home runs or accumulate extra-base hits.
                </p>
                <ul style="font-size: 1.0rem; line-height: 1.8; color: rgba(255,255,255,0.85); padding-left: 20px;">
                    <li><strong style="color:var(--accent-blue);">OMEGA (Hitter Score):</strong> The raw projected power potential of the batter on today's slate. Ranks individual hitters from highest power upside to lowest.</li>
                    <li><strong style="color:var(--accent-blue);">PLAYER & vs PITCHER:</strong> The batter's name, team, and the opposing starting pitcher they are facing.</li>
                    <li><strong style="color:var(--accent-blue);">HR-PROP & BASES:</strong> The live Vegas prop pricing for their Home Run odds (e.g., `+450` means a $100 bet pays $450 if they hit a home run) and total bases line. Sorting by this column lets you instantly identify the highest-upside power hitters on the slate.</li>
                </ul>
            </div>
            
            <!-- SECTION 4 -->
            <div id="sec-stacks" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>4.</span> Team Stacks & Bullpens
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    In large-field DFS tournaments, "stacking" (pairing 3 to 5 hitters from the same team) is the most successful strategy to win first place. This dashboard ranks the best offensive team stacks on the slate.
                </p>
                <ul style="font-size: 1.0rem; line-height: 1.8; color: rgba(255,255,255,0.85); padding-left: 20px;">
                    <li><strong style="color:var(--accent-blue);">OMEGA (Stack Score):</strong> The overall rating of the team's offense today. A score above **95 is an elite GPP stack**.</li>
                    <li><strong style="color:var(--accent-blue);">ITT (Implied Team Total):</strong> The most important basic stat in DFS. This is the **Vegas Implied Run Total** (e.g., `5.28` means Vegas expects this team to score 5.28 runs). Stacking teams with an ITT above **4.8** is a premier strategy.</li>
                    <li><strong style="color:var(--accent-blue);">ML MOVE & TT MOVE (Moneyline & Team Total Movement):</strong> Shows how the betting lines have shifted since opening. A positive number (e.g., `+15` or `+0.5`) means money is flooding in, indicating the team is gaining strong market steam.</li>
                    <li><strong style="color:var(--accent-blue);">DIVERGENCE:</strong> Shows the "Money Gap." If this is **highly positive (e.g., +26%)**, it means smart, high-roller bettors are putting far more money on this team than the general public. This is a massive buy signal.</li>
                </ul>
            </div>
            
            <!-- SECTION 5 -->
            <div id="sec-environment" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>5.</span> Ballpark Weather Matrix
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    Weather alters the physics of a baseball. Hot air makes the ball fly farther; cold air dense-packs the atmosphere; wind blowing out can turn routine flyouts into home runs. This panel monitors these environmental anomalies.
                </p>
                <ul style="font-size: 1.0rem; line-height: 1.8; color: rgba(255,255,255,0.85); padding-left: 20px;">
                    <li><strong style="color:var(--accent-blue);">STATUS:</strong> Color-coded safety status. `☀️ CLEAR` (Safe), `🏟️ DOME` (Indoor, zero weather impact), `⛅ DELAY RISK` (High danger for starting pitchers who might get warm and then get pulled), or `🌧️ POSTPONE HAZARD` (Severe weather risk; avoid!).</li>
                    <li><strong style="color:var(--accent-blue);">TEMP & HUMIDITY:</strong> Displays the temperature and moisture. **High heat (85°F+) and high humidity** are massive boosts for hitters, causing the ball to carry significantly farther.</li>
                    <li><strong style="color:var(--accent-blue);">WIND SPEED & DIRECTION:</strong> The velocity and direction of the wind (e.g., `12mph Out to Left`). Wind blowing **OUT** at 8mph+ is a major hitter accelerator. Wind blowing **IN** at 8mph+ is a major pitcher boost.</li>
                    <li><strong style="color:var(--accent-blue);">PARK & UMPIRE:</strong> Evaluates stadium altitude and the strike-zone tightness of the assigned home-plate umpire. A "Tight" strike-zone umpire walks more batters, heavily boosting offenses.</li>
                </ul>
            </div>
            
            <!-- SECTION 6 -->
            <div id="sec-definitions" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>6.</span> Cockpit Signals Glossary
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    Here is your direct cockpit cheat sheet to identify high-conviction plays on any slate:
                </p>
                <table style="margin-top: 20px; font-size: 0.9rem;">
                    <thead>
                        <tr>
                            <th style="width: 250px;">Signal Badge</th>
                            <th>Operational Meaning</th>
                            <th>Strategic Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><span class="badge pill-shark">🦈 SHARK</span></td>
                            <td>Sharp, professional bettors are aggressively moving the lines on this play.</td>
                            <td>Highly reliable core plays. Lock these into your lineups.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-whale">🐳 WHALE</span></td>
                            <td>The biggest high-rollers in the world (the "Whales") are dumping massive financial volume on this play.</td>
                            <td>Elite GPP tournament plays. These indicate massive smart-money backing.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-storm">⚡ STORM</span></td>
                            <td>Offense playing in ideal hot/humid/wind-out launch environments.</td>
                            <td>Prioritize these hitters and stacks. The ball will be flying out of the park.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-steam">💨 STEAM</span></td>
                            <td>Extreme, late-breaking money is flooding in on this line just hours before lock.</td>
                            <td>Pay close attention to these late shifts. They indicate late-breaking sharp news.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-sharp">⚡ BURST</span></td>
                            <td>A player who has massive statistical upside but is projected for extremely low ownership in GPP tournaments.</td>
                            <td>The ultimate tournament secret. Pair a BURST player with a popular stack to make your lineup unique.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-trap" style="background:rgba(255,69,58,0.15); border-color:#ff453a; color:#ff453a;">🚨 TRAP</span></td>
                            <td>A highly popular public play that has severe underlying warning signs.</td>
                            <td>FADE. Let the rest of the field roster this player. When they fail, you leapfrog them.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-paradox">⚠️ PARADOX</span></td>
                            <td>A contradiction in the data (e.g., an elite starting pitcher facing an elite, highly rated offense).</td>
                            <td>Avoid rostering both sides. Choose one side of the matchup to commit to.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-lowconf" style="background:rgba(255,159,10,0.15); border-color:#ff9f0a; color:#ff9f0a;">🌋 HAZARD</span></td>
                            <td>High probability of negative outcomes, such as severe weather or delay risks.</td>
                            <td>Highly risky. Avoid starting pitchers in these games.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-gassed">🔥 EXHAUSTED</span></td>
                            <td>The opposing team's bullpen relief pitchers are completely fatigued.</td>
                            <td>Massive BUY signal for the opposing stack. Feasting on tired relief arms leads to late-inning run surges.</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <!-- SECTION 7 -->
            <div id="sec-playbook" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>7.</span> Our GPP Drafting Playbook
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    To win first place in a high-stakes GPP tournament, you cannot just play the "best" players. You must play the **smartest** players:
                </p>
                
                <div class="quant-card" style="border-left: 4px solid var(--accent-blue);">
                    <h4 style="color:#fff; font-weight:800; margin-bottom: 10px;">Strategy 1: The "Trap-Pivot" Sweep</h4>
                    <p style="font-size: 0.95rem; color: rgba(255,255,255,0.85); line-height: 1.6; margin: 0;">
                        Scan the Starting Pitchers matrix and locate a highly owned pitcher flagged as a `🚨 TRAP`. Do not roster that pitcher. Instead, pivot to a pitcher in the same price range who has high Physics (`PHY`) and zero warning signals, and directly stack the opposing hitters. If the trap pitcher fails, your lineup vaults straight to the top.
                    </p>
                </div>
                
                <div class="quant-card" style="border-left: 4px solid var(--accent-green);">
                    <h4 style="color:#fff; font-weight:800; margin-bottom: 10px;">Strategy 2: The Bullpen Exhaustion Exploit</h4>
                    <p style="font-size: 0.95rem; color: rgba(255,255,255,0.85); line-height: 1.6; margin: 0;">
                        Look for a team stack whose opponent is flagged with `🔥 EXHAUSTED` bullpen fatigue. Even if the starting pitcher is decent, roster a 4-man or 5-man stack against them. The moment the starter exits the game, the opposing offense will face fatigued relief arms, netting you massive, late-inning run surges.
                    </p>
                </div>
                
                <div class="quant-card" style="border-left: 4px solid var(--accent-purple);">
                    <h4 style="color:#fff; font-weight:800; margin-bottom: 10px;">Strategy 3: The Whale Moneyline Sync</h4>
                    <p style="font-size: 0.95rem; color: rgba(255,255,255,0.85); line-height: 1.6; margin: 0;">
                        Cross-reference the Team Stack Matrix with the Pitchers Matrix. Locate a team that has a highly positive Divergence (e.g., +26% money gap) and a `🐳 WHALE` signal, but their starting pitcher is flagged as a `🚨 TRAP`. Do not play the starting pitcher, but roster the team's offense (stack them) to exploit a high-scoring game while avoiding the low-upside chalk pitcher!
                    </p>
                </div>
            </div>
        </div>"""
        
    new_content = content[:start_idx] + replacement_html + content[end_idx:]
    
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print("[SUCCESS]: Overwrote hardcoded handbook modal inside templates/index.html!")

if __name__ == "__main__":
    main()
