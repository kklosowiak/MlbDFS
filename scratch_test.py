import pandas as pd
from engine.sharps_weighting import SharpsWeighting
df = pd.read_csv('logs/trend_tag_log.csv')
df = df[df['date'] == '2026-04-24']
sw = SharpsWeighting()
scores = {}
for _, row in df.iterrows():
    if pd.isnull(row['team']): continue
    ml = -float(row['ml_move']) if pd.notnull(row['ml_move']) else 0.0
    tt = float(row['tt_move']) if pd.notnull(row['tt_move']) else 0.0
    div = float(row['divergence']) if pd.notnull(row['divergence']) else 0.0
    itt = float(row['implied_total']) if pd.notnull(row['implied_total']) else 4.0
    is_storm = (div >= 10 and tt >= 0.3)
    is_shark = (div >= 10 and ml <= -10)
    is_whale = (div >= 15)
    is_steam = (ml <= -10 and div < 10)
    res = sw.calculate_stack_score(
        team=row['team'], ml_move=ml, tt_move=tt, curr_itt=itt,
        divergence=div, is_storm=is_storm, is_shark=is_shark, is_whale=is_whale, is_steam=is_steam
    )
    # keep best score for each team
    t = row['team']
    if t not in scores or res['final'] > scores[t][0]:
        scores[t] = (res['final'], ml, div, row['slate_timestamp'])

for s in sorted(scores.items(), key=lambda x: x[1][0], reverse=True)[:6]:
    print(f'{s[0]:20} | Peak Score: {s[1][0]:.1f} | ML: {s[1][1]:.0f} | Div: {s[1][2]:.0f} | Time: {s[1][3]}')

