import os

filepath = "templates/index.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = '    <!-- 📖 SYSTEM HANDBOOK MODAL OVERLAY -->'
end_marker = '</body>'

start_idx = content.find(start_marker)
if start_idx == -1:
    # Try finding it without the leading indentation
    start_marker = '<!-- 📖 SYSTEM HANDBOOK MODAL OVERLAY -->'
    start_idx = content.find(start_marker)

if start_idx == -1:
    print("Start marker not found")
    exit(1)
    
end_idx = content.find(end_marker, start_idx)
if end_idx == -1:
    print("End body marker not found")
    exit(1)

# The new handbook HTML content
new_handbook_html = """    <!-- 📖 SYSTEM HANDBOOK MODAL OVERLAY -->
    <div class="handbook-modal" id="handbook-modal">
        <button class="handbook-close-btn" onclick="closeHandbook()">CLOSE HANDBOOK ×</button>
        
        <div class="handbook-sidebar">
            <h2>🔱 OMEGA Handbook</h2>
            <p style="font-size: 0.72rem; color: var(--text-secondary); margin: -10px 0 10px 0; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">QUANT WHITEPAPER & GUIDE</p>
            <hr style="border: 0; border-top: 1px solid var(--border); width: 100%; margin: 0 0 10px 0;">
            
            <ul class="handbook-toc">
                <li class="handbook-toc-item active" onclick="scrollToHandbookSection('sec-philosophy')">1. Konrad's Story & Philosophy</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-pitchers')">2. Pitcher Alpha Math</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-hitters')">3. Hitter Prop Mechanics</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-stacks')">4. Team Stacks & Bullpens</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-environment')">5. Environmental Filters</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-definitions')">6. Cockpit Signals Glossary</li>
                <li class="handbook-toc-item" onclick="scrollToHandbookSection('sec-playbook')">7. Our GPP Drafting Playbook</li>
            </ul>
        </div>
        
        <div class="handbook-content-area">
            <!-- SECTION 1 -->
            <div id="sec-philosophy" style="margin-bottom: 60px; padding-top: 20px;">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>1.</span> Hi, I'm Konrad — Let's Talk DFS Math
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    I've been playing Daily Fantasy Sports (DFS) and betting on baseball for **over 10 years**. In that time, I've seen it all: line-up traps, bookmaker tricks, massive public chalk bubbles, and standard projection sheets that fail because they treat sports like dry, static spreadsheets.
                </p>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    That's why I built the **OMEGA Engine**. I wanted a system that doesn't just parse raw historical averages, but instead **triangulates three distinct layers of real-time reality** to discover mathematically massive leverage:
                </p>
                <div class="quant-card">
                    <h4 style="color:#fff; font-weight: 800; margin-bottom: 6px;">Vector A: Pure Physics (Statcast Calibration)</h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin:0; line-height: 1.6;">
                        Direct field measurements: barrel rates, expected weighted on-base average (xwOBA), Pitch CSW (Called Strikes + Whiffs), and SIERA. This represents actual physical capability, stripping away luck and ballpark noise.
                    </p>
                </div>
                <div class="quant-card">
                    <h4 style="color:#fff; font-weight: 800; margin-bottom: 6px;">Vector B: Market Intelligence (Sharps & Whales)</h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin:0; line-height: 1.6;">
                        We track sportsbook splits and money flows. Tracking massive cash discrepancies (e.g., a team receiving only 20% of tickets but 80% of total money) exposes where syndicate groups and institutional "Whales" are placing their high-conviction positions.
                    </p>
                </div>
                <div class="quant-card">
                    <h4 style="color:#fff; font-weight: 800; margin-bottom: 6px;">Vector C: Environmental Modifier Overlay</h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin:0; line-height: 1.6;">
                        External variables that act as physics accelerators or suppressors: home plate umpire strike zones, stadium-specific humidity and launch velocities, wind shear, and multi-day trailing bullpen fatigue logs.
                    </p>
                </div>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    When these three vectors converge on a single matchup, the engine registers an active **Target or Shark Signal**, indicating an highly exploitable outlier edge in the market. Let me show you how my brother and I use this cockpit every single day to systematically lock in high-leverage plays and aggressively fade market traps!
                </p>
            </div>
            
            <!-- SECTION 2 -->
            <div id="sec-pitchers" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>2.</span> Pitcher Alpha Mathematical Architecture
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    In GPP tournaments, a failed starting pitcher will sink your entire lineup instantly. To lock down our pitching core, OMEGA grades starting pitchers on a mix of raw physical talent and sharp market backing. 
                </p>
                
                <h4 style="color: #fff; margin-bottom: 8px; font-weight: 700;">Formula 1: The Pure Talent Floor</h4>
                <p style="font-size: 0.95rem; color: var(--text-secondary); margin-top: 0; line-height: 1.6;">
                    First, we calculate a pitcher's talent ceiling using Skill-Interactive ERA (SIERA) and Called Strikes + Whiffs (CSW) rate:
                </p>
                <div class="quant-equation">
                    Talent_Score = 25 * (4.50 - SIERA) + 100 * (CSW - 0.25)
                </div>
                <p style="font-size: 0.95rem; color: var(--text-secondary); line-height: 1.6;">
                    <strong>Konrad's Rule:</strong> My brother and I never select a pitcher with a baseline Talent Score below 55. If they don't have the arm talent, they don't make our roster.
                </p>
                
                <h4 style="color: #fff; margin-bottom: 8px; font-weight: 700;">Formula 2: Market Divergence Adjustment</h4>
                <p style="font-size: 0.95rem; color: var(--text-secondary); margin-top: 0; line-height: 1.6;">
                    Next, we scan sportsbook shifts to detect syndicate actions and steam:
                </p>
                <div class="quant-equation">
                    Market_Divergence = (Sharp_ML_Move * 1.5) + (Whale_Money_Gap * 2.0)
                </div>
                
                <h4 style="color: #fff; margin-bottom: 8px; font-weight: 700;">The "Sharp Money" Signal & +7.5% Premium Multiplier</h4>
                <p style="font-size: 0.95rem; color: var(--text-secondary); margin-top: 0; line-height: 1.6;">
                    OMEGA filters raw betting volume through strict institutional gates. A game is flagged as **SHARP** when pro money splits diverge aggressively from ticket volume (e.g., ticket count is 22% but money percentage is 58%), or when multi-book syndicate steam triggers concurrent line movement on both the moneyline and the under. When a team or pitcher receives confirmed pro money backing, the engine automatically applies a <strong>+7.5% Sharp Premium Multiplier</strong> to prioritize professional consensus over public bias.
                </p>
                <div class="quant-equation">
                    Sharp_Premium_Factor = 1.075 [IF Sharp_Signal == True, ELSE 1.0]
                </div>
                
                <h4 style="color: #fff; margin-bottom: 8px; font-weight: 700;">Formula 3: The Aggregated Pitcher Alpha</h4>
                <p style="font-size: 0.95rem; color: var(--text-secondary); margin-top: 0; line-height: 1.6;">
                    The final score incorporates environmental overlays (umpire strike zones, wind/stadium adjustments) and applies defensive gates:
                </p>
                <div class="quant-equation">
                    Pitcher_Alpha = ((Talent_Score * Sharp_Premium_Factor) * Defensive_Gates) + Market_Divergence + Env_Overlay
                </div>
                
                <div class="quant-card" style="border-left: 4px solid var(--accent-red); background: rgba(255, 69, 58, 0.02);">
                    <h4 style="color:#fff; font-weight: 800; display:flex; align-items:center; gap:8px;">
                        <span class="badge pill-trap">🛡️ DEFENSIVE GATE: THE WHALE TRAP</span>
                    </h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin:0; line-height: 1.6;">
                        If public ticket volume is highly heavy (&gt;70% on a pitcher) but the moneyline moves in the <em>opposite</em> direction (Reverse Line Movement), the engine flags a <strong>Whale Trap</strong>. The gate applies a <strong>-20% penalty</strong> to that pitcher, suppressing them in lineup generation to aggressively fade public consensus.
                    </p>
                </div>
            </div>
            
            <!-- SECTION 3 -->
            <div id="sec-hitters" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>3.</span> Hitter Prop Mechanics & The Abrams Price Shield
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    Hitters are all about home run upside and high DraftKings ceilings. To identify high-leverage prop plays, we look at physical contact metrics and bookmaker price discrepancies:
                </p>
                
                <div class="quant-card" style="border-left: 4px solid var(--accent-green); background: rgba(52, 199, 89, 0.02);">
                    <h4 style="color:#fff; font-weight: 800; display:flex; align-items:center; gap:8px;">
                        <span>🔬 Hitter PHYS (Physics Score) Calculation</span>
                    </h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin-bottom: 8px; line-height: 1.6;">
                        Represents a hitter's pure Statcast contact profile, scaling expected Weighted On-Base Average (xwOBA) over their rolling 14-day and matchup baseline from 0.280 to 0.420. Yields up to <strong>50.0 points</strong> of the player's core rating.
                    </p>
                    <div class="quant-equation" style="font-size: 0.8rem; padding: 10px;">
                        PHYS = Limit[0, 50, ((Matchup_xwOBA - 0.280) / (0.420 - 0.280)) * 50]
                    </div>
                </div>
                <div class="quant-card" style="border-left: 4px solid var(--accent-blue); background: rgba(10, 132, 255, 0.02);">
                    <h4 style="color:#fff; font-weight: 800; display:flex; align-items:center; gap:8px;">
                        <span>📊 Hitter MKT (Market Score) Calculation</span>
                    </h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin-bottom: 8px; line-height: 1.6;">
                        Scales the player's AnyTime Home Run (AHR) prop market odds from +200 to +700, exposing bookmaker mispricings. Yields up to <strong>50.0 points</strong> of the player's core rating.
                    </p>
                    <div class="quant-equation" style="font-size: 0.8rem; padding: 10px;">
                        MKT = Limit[0, 50, ((700 - Min[700, AHR_Odds]) / 500) * 50]
                    </div>
                </div>
                
                <h4 style="color: #fff; margin-bottom: 8px; font-weight: 700;">Formula 4: Expected wOBA Momentum</h4>
                <p style="font-size: 0.95rem; color: var(--text-secondary); margin-top: 0; line-height: 1.6;">
                    OMEGA tracks a rolling 14-day Statcast window (Exit Velocity, Hard Hit %, and Launch Angle optimization) to calculate raw xwOBA momentum:
                </p>
                <div class="quant-equation">
                    Hitter_xwOBA_Momentum = (Rolling_Avg_EV * 0.4) + (Hard_Hit_Pct * 0.3) + (Launch_Angle_Opt * 0.3)
                </div>
                
                <div class="quant-card" style="border-left: 4px solid var(--accent-orange); background: rgba(255, 159, 10, 0.02);">
                    <h4 style="color:#fff; font-weight: 800; display:flex; align-items:center; gap:8px;">
                        <span class="badge pill-steam">🛡️ THE ABRAMS PRICE SHIELD</span>
                    </h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin:0; line-height: 1.6;">
                        Bookmakers often try to suppress public interest in elite hitters by pricing their Home Run props extremely high (e.g., pricing CJ Abrams or an elite bat at +900). OMEGA has a built-in protective floor: if a hitter's pure Statcast physics xwOBA is &gt; .380, the engine automatically overrides artificially inflated odds, forcing the player up our target lists based on raw capability rather than bookmaker pricing bias.
                    </p>
                </div>
            </div>
            
            <!-- SECTION 4 -->
            <div id="sec-stacks" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>4.</span> Team Stacks & The Bullpen Death-Spiral
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    DFS tournaments are won through stacking. OMEGA ranks team stacks using an aggregated formula that measures how hard an offense hits, combined with the structural vulnerability of the opposing pitching staff.
                </p>
                
                <h4 style="color: #fff; margin-bottom: 8px; font-weight: 700;">Formula 5: Unified Team Stack Score</h4>
                <p style="font-size: 0.95rem; color: var(--text-secondary); margin-top: 0; line-height: 1.6;">
                    We sum the top xwOBA scores in the projected starting lineup, weigh it for power concentration (the 1-5 batting order spots), and multiply it by atmospheric and fatigue elements:
                </p>
                <div class="quant-equation">
                    Stack_Score = (Lineup_xwOBA_Sum * Power_Concentration) * Bullpen_Fatigue_Factor * Stadium_PF * Umpire_Bias
                </div>
                
                <h4 style="color: #fff; margin-bottom: 8px; font-weight: 700;">Formula 6: Bullpen Fatigue Acceleration Index</h4>
                <p style="font-size: 0.95rem; color: var(--text-secondary); margin-top: 0; line-height: 1.6;">
                    Relief pitching staffs are highly volatile when overworked. OMEGA logs every relief appearance over a rolling 3-day window. If the opposing bullpen's fatigue score is &gt; 80, the stack conviction scales exponentially:
                </p>
                <div class="quant-equation">
                    Bullpen_Fatigue_Factor = 1.0 + ((Fatigue - 80) / 100) * 0.20 [IF Fatigue &gt; 80, ELSE 1.0]
                </div>
                <p style="font-size: 0.95rem; color: var(--text-secondary); line-height: 1.6;">
                    <em>Konrad's Note:</em> If the opposing bullpen's fatigue index is 95, the stack gets a **+23% multiplier boost**, signaling an inevitable late-inning relief collapse!
                </p>
                
                <div class="quant-card" style="border-left: 4px solid var(--accent-purple); background: rgba(191, 90, 242, 0.02);">
                    <h4 style="color:#fff; font-weight: 800; display:flex; align-items:center; gap:8px;">
                        <span class="badge pill-paradox">⚡ THE PARADOX RESOLVER GATE</span>
                    </h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin:0; line-height: 1.6;">
                        Playing a starting pitcher while simultaneously playing a 5-man batting stack against them is a mathematically contradictory stance. If a Top 5 pitcher is matched against a Top 3 stack, the Paradox Resolver applies a **-30% penalty** to the pitcher, forcing us to take a clear tactical stance: stack the hitters, or play the pitcher, but never compromise in the middle.
                    </p>
                </div>
            </div>
            
            <!-- SECTION 5 -->
            <div id="sec-environment" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>5.</span> Environmental Filters (The Invisible 10%)
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    Ballgames aren't played in climatized domes. Standard projection systems treat weather and umpires like background noise, but my brother and I treat them as critical edge accelerators:
                </p>
                <div class="quant-card">
                    <h4 style="color:#fff; font-weight: 800; margin-bottom: 6px;">A. Stadium Thermal Density</h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin:0; line-height: 1.6;">
                        When temperatures rise above 70°F, air density plummets. Hit carry distance increases by ~3.5 feet for every 10-degree rise, directly boosting Hitter Burst and stack rankings in hot, outdoor stadiums.
                    </p>
                </div>
                <div class="quant-card">
                    <h4 style="color:#fff; font-weight: 800; margin-bottom: 6px;">B. Asymmetrical Park Factors</h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin:0; line-height: 1.6;">
                         Balls fly differently based on batter handedness. OMEGA uses left- and right-handed park multipliers individually. A short right-field porch (like Yankee Stadium) applies a specific <strong>1.12x boost to lefties</strong>, while keeping righties completely neutral.
                    </p>
                </div>
                <div class="quant-card">
                    <h4 style="color:#fff; font-weight: 800; margin-bottom: 6px;">C. Umpire Strike Zone Bias</h4>
                    <p style="font-size:0.92rem; color:var(--text-secondary); margin:0; line-height: 1.6;">
                        OMEGA maps historic umpire strike zones daily. A tight strike zone umpire ('Launch Zone') forces pitchers to throw meatier pitches in the zone, scaling the opposing team stack Implied Team Total by up to **+12%**. Conversely, wide strike zone umpires increase pitcher strikeout ceilings.
                    </p>
                </div>
            </div>
            
            <!-- SECTION 6 -->
            <div id="sec-definitions" style="margin-bottom: 60px; padding-top: 40px; border-top: 1px solid var(--border);">
                <h3 style="font-size: 1.8rem; font-weight: 800; margin-top: 0; letter-spacing: -0.03em; color: var(--accent-blue); display: flex; align-items: center; gap: 10px;">
                    <span>6.</span> The OMEGA Cheat Sheet (Signals Glossary)
                </h3>
                <p style="font-size: 1.05rem; line-height: 1.7; color: rgba(255,255,255,0.85);">
                    Here is your direct cockpit cheat sheet to identify high-conviction plays on any slate:
                </p>
                <table style="margin-top: 20px; font-size: 0.9rem;">
                    <thead>
                        <tr>
                            <th style="width: 250px;">Signal Badge</th>
                            <th>Mathematical Meaning</th>
                            <th>Strategic Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><span class="badge" style="background: rgba(52, 199, 89, 0.12); border-color: #34c759; color: #34c759; text-shadow: 0 0 6px rgba(52, 199, 89, 0.3); font-weight: 800; font-size: 0.72rem; padding: 4px 8px; border-radius: 4px; border: 1px solid; display: inline-block; white-space: nowrap;">🔬 PHYS (PHYSICS)</span></td>
                            <td>Expected physical performance based entirely on Statcast launch velocities, expected wOBA (xwOBA), Pitch CSW%, SIERA, umpire zones, and weather physics. Represents true underlying baseline talent.</td>
                            <td>Compare with market score. When PHYS is high but MKT is low, target for high-leverage GPP tournament plays (exploiting public blind spots).</td>
                        </tr>
                        <tr>
                            <td><span class="badge" style="background: rgba(10, 132, 255, 0.12); border-color: #0a84ff; color: #0a84ff; text-shadow: 0 0 6px rgba(10, 132, 255, 0.3); font-weight: 800; font-size: 0.72rem; padding: 4px 8px; border-radius: 4px; border: 1px solid; display: inline-block; white-space: nowrap;">📊 MKT (MARKET)</span></td>
                            <td>Consensus Vegas and sportsbook sentiment. Reflects opening moneyline lines, live money movements, betting split discrepancies (ticket-to-money gap), and Anytime Home Run (AHR) prop pricing.</td>
                            <td>Use to detect institutional support and syndicate steam. High MKT scores highlight where the smart money is moving before the public reacts.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-target">🎯 TARGET</span></td>
                            <td>Highest overall OMEGA-ranked math value on the slate.</td>
                            <td>Lock in as core roster anchors in both cash and GPP slates.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-shark">🦈 SHARK</span></td>
                            <td>Syndicate sharp-backed money on both the Moneyline and Under.</td>
                            <td>High-priority plays. Betting limits are expanding; sharps confirm the value.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-sharp">🟢 SHARP</span></td>
                            <td>Confirmed institutional money backing split. Triggers a <strong>+7.5% premium boost</strong>.</td>
                            <td>Core anchor target. Shows heavy professional consensus before public locks.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-neutral" style="background: linear-gradient(135deg, rgba(0, 242, 254, 0.12) 0%, rgba(79, 172, 254, 0.12) 100%); border-color: #00f2fe; color: #00f2fe; text-shadow: 0 0 8px rgba(0, 242, 254, 0.4); text-transform: uppercase; font-weight: 800; font-size: 0.72rem; padding: 4px 8px; border-radius: 4px; border: 1px solid; display: inline-block; white-space: nowrap;">👁️ BLIND SPOT</span></td>
                            <td>Divergence Arbitrage: Physics score exceeds Market score by 25+ points.</td>
                            <td>Maximum tournament leverage stack target. Highly unowned by the general public.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-whale">🐳 WHALE</span></td>
                            <td>Highly massive institutional volume flows (high money %, low ticket %).</td>
                            <td>Indicates "Super-Sharp" backing. Target in GPP rosters to match smart pools.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-steam">🔥 STEAM</span></td>
                            <td>Lines are moving rapidly in a narrow window across multiple books.</td>
                            <td>Indicates syndicate activity. Roster immediately before prices rise.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-storm">⚡ STORM</span></td>
                            <td>Offense playing in ideal hot/humid/wind-out launch environment.</td>
                            <td>Ideal stack target. High carry multiplier; heavy odds of home run clusters.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-storm">✨ DEBUT</span></td>
                            <td>Rookie or starting pitcher making their seasonal or career debut.</td>
                            <td>Highly volatile. Statcast metrics are estimated; utilize small leverage stakes.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-storm" style="white-space: nowrap;">✨ DEBUT TARGET</span></td>
                            <td>Batting stack facing a rookie starting pitcher making their career or seasonal debut.</td>
                            <td>Exploitable target. Volatile opposing arm; triggers a <strong>+10% stack multiplier boost</strong>.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-trap">❌ TRAP</span></td>
                            <td>Reverse Line Movement detected. Public is on one side, whales on the other.</td>
                            <td>Aggressively fade. Avoid starting pitchers or stacks flagged as a trap.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-gassed">🚒 GASSED</span></td>
                            <td>Opposing bullpen's 3-day trailing fatigue index is greater than 80%.</td>
                            <td>Prioritize this batting stack. High odds of late-game run explosions.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-steam">🔥 GASSING</span></td>
                            <td>Opponent strikeout rate is high; boosts pitcher strikeout ceiling.</td>
                            <td>Target pitcher's over-strikeout prop on prop boards. High GPP ceiling.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-lowconf">🧊 COLD</span></td>
                            <td>Hitter has experienced a severe cold streak over their last 15 plate appearances.</td>
                            <td>Gate activated. Lowers hitter priority and suppresses them in lineup generator.</td>
                        </tr>
                        <tr>
                            <td><span class="badge pill-paradox">🚫 PARADOX</span></td>
                            <td>Conflict: Top Pitcher faces a Top Stack. Suppress rating by 30%.</td>
                            <td>Forces a clean stand: stack the offense, or lock the pitcher, never mix them.</td>
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
                    The OMEGA Cockpit is not a static scoreboard; it is a **dynamic tournament-winning weapon**. By utilizing expected physical baselines and market betting flows, you can systematically build highly leveraged rosters that out-maximize the field. Here is the step-by-step drafting playbook my brother and I use:
                </p>
                
                <div class="quant-card" style="border-left: 4px solid var(--accent-blue);">
                    <h4 style="color:#fff; font-weight:800; margin-bottom: 10px;">Step 1: Anchor Your Pitching Core (The Talent-Shield)</h4>
                    <p style="font-size: 0.95rem; color: rgba(255,255,255,0.85); line-height: 1.6; margin: 0 0 12px 0;">
                        In multi-entry tournaments, pitching failure kills rosters instantly. Build your pitching pool by looking at the **Pitchers Matrix**:
                    </p>
                    <ul style="font-size: 0.9rem; color: var(--text-secondary); margin: 0; padding-left: 20px;">
                        <li style="margin-bottom: 6px;"><strong style="color:#fff;">Filter by Floor:</strong> Only select pitchers with a raw Talent Score > 55. If a pitcher's arm talent (SIERA/CSW) is weak, do not roster them.</li>
                        <li style="margin-bottom: 6px;"><strong style="color:#fff;">Identify Pro backing:</strong> Look for pitchers carrying a <span class="badge pill-sharp">🟢 SHARP</span> or <span class="badge pill-whale">🐳 WHALE</span> badge. Pro-backing confirms that professional money expects an elite game.</li>
                        <li style="margin-bottom: 0;"><strong style="color:#fff;">AGGRESSIVE FADE:</strong> Never roster a pitcher flagged with a <span class="badge pill-trap">❌ TRAP</span> badge, regardless of how cheap their salary is. The market is screaming that a public trap is active.</li>
                    </ul>
                </div>
                
                <div class="quant-card" style="border-left: 4px solid var(--accent-green);">
                    <h4 style="color:#fff; font-weight:800; margin-bottom: 10px;">Step 2: Build Your 5-3 and 4-4 Correlation Offenses</h4>
                    <p style="font-size: 0.95rem; color: rgba(255,255,255,0.85); line-height: 1.6; margin: 0 0 12px 0;">
                        Correlated scoring is the only way to climb the GPP leaderboards. When a team scores 10 runs, all players in that batting lineup benefit:
                    </p>
                    <ul style="font-size: 0.9rem; color: var(--text-secondary); margin: 0; padding-left: 20px;">
                        <li style="margin-bottom: 6px;"><strong style="color:#fff;">Identify "Storm" Stacks:</strong> Look for team stacks carrying the <span class="badge pill-storm">⚡ STORM</span> badge. This confirms hot/humid stadium carry velocities, wind launch assistance, and tight umpire strike zones.</li>
                        <li style="margin-bottom: 6px;"><strong style="color:#fff;">Target Gassed Bullpens:</strong> Prioritize stack matchups carrying the <span class="badge pill-gassed">🚒 GASSED</span> badge. If the opposing relief pitching staff has a 3-day fatigue index > 80%, the offense will explode in the late innings against exhausted relief arms.</li>
                        <li style="margin-bottom: 0;"><strong style="color:#fff;">Avoid Paradoxes:</strong> Ensure you do not play a pitcher who is starting against your main batting stack. Lock in your stance and let the **Paradox Resolver** suppress conflicting selections.</li>
                    </ul>
                </div>
                
                <div class="quant-card" style="border-left: 4px solid var(--accent-purple);">
                    <h4 style="color:#fff; font-weight:800; margin-bottom: 10px;">Step 3: Capture Divergence Arbitrage (Leverage Over the Field)</h4>
                    <p style="font-size: 0.95rem; color: rgba(255,255,255,0.85); line-height: 1.6; margin: 0 0 12px 0;">
                        In DFS, high ownership is your enemy. The field drafts based on media hype and basic projection sheets. You win by finding the "Blind Spots":
                    </p>
                    <ul style="font-size: 0.9rem; color: var(--text-secondary); margin: 0; padding-left: 20px;">
                        <li style="margin-bottom: 6px;"><strong style="color:#fff;">The Divergence Indicator:</strong> Look for matchups in the **Teams Matrix** where the **Physics Score** is highly higher than the **Market Score** (e.g., Physics is 88, but Market is 52).</li>
                        <li style="margin-bottom: 6px;"><strong style="color:#fff;">Strategic Opportunity:</strong> This means that while public consensus and betting money are cold on the team, their underlying Statcast physical metrics are elite. Stacking this team gives you massive tournament leverage: they will score high but be owned by less than 5% of the tournament field!</li>
                        <li style="margin-bottom: 0;"><strong style="color:#fff;">Verify on Hitter Prop Boards:</strong> Verify these plays by checking the Hitter prop board for batters whose home run odds are artificially high, leveraging the **Abrams Price Shield** floor.</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>"""

# Find the end of the handbook modal container by splitting at </body>
end_idx = content.find(end_marker)
if end_idx == -1:
    print("End body marker </body> not found")
    exit(1)

updated_content = content[:start_idx] + new_handbook_html + "\\n" + content[end_idx:]

with open(filepath, "w", encoding="utf-8") as f:
    f.write(updated_content)
    
print("Handbook updated successfully via Python split!")
