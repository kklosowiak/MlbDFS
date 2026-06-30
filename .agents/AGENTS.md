# ⚾ Project-Scoped MLB DFS Rules

## 1. 🔍 Rookie & Prospect Call-Up Platoon Validation
*   **The Rule:** When a player is flagged as making their MLB debut or has fewer than 20 career plate appearances, the agent MUST manually verify their batting side (`bat_side`) and throwing hand (`pitch_hand`) against public scouting reports or MLB rosters.
*   **Actionable Fix:** If a discrepancy is found (e.g., Kyle Teel misclassified as `bat_side: 'R'` when he is an `L`), the agent must correct it in the local cache before running the optimizer to ensure platoon calculations are correct.

## 2. 🏆 DraftKings Stacking Rules
*   **The Rule:** Pitcher and hitter stacking from the same team is 100% legal on DraftKings. You can roster up to 5 hitters and the starting pitcher from the same team.
*   **Actionable Fix:** Never report warning flags or reject lineups on the basis of a pitcher being stacked with hitters from the same team.

## 3. 🖥️ Windows Terminal Script Compatibility
*   **The Rule:** Avoid using raw Unicode characters (such as emojis: ✅, ❌, ⚠️, ⭐) in Python script console prints or file writes.
*   **Actionable Fix:** Use plain ASCII for terminal output in scripts. If Unicode output is absolutely required, wrap standard output with UTF-8 encoding:
    ```python
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    ```

## 4. Verification Claims: "Confirmed" vs "Logic-Level Check"
*   **The Rule:** Before stating any claim as "confirmed" or "validated" about production behavior, ask first: am I reading this from the actual shipped code path, or from something I wrote that I believe matches it (a standalone reimplementation, an inline formula, a hand-traced calculation)?
*   **If it is the second one:** Label it explicitly as a "logic-level check, not yet run against production" rather than stating it as confirmed. Note what would be needed to promote it to confirmed (e.g. "would need to call the real function with real cached data to verify").
*   **Reserve "confirmed" only for:** Claims backed by executing the actual production code path with real data and printed output.
*   **Actionable Fix:** When a verification step is needed to promote a logic-level check to confirmed, run the real function against real cached data and print the output before making the claim — do not assume the reimplementation matches the shipped code.
