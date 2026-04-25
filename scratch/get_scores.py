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
    t = row['team']
    if t not in scores or res['final'] > scores[t]['score']:
        scores[t] = {'score': res['final'], 'ml': ml, 'div': div, 'is_steam': is_steam, 'is_storm': is_storm, 'is_shark': is_shark, 'is_whale': is_whale}

for t, data in sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True):
    print(f"{t:20} | Score: {data['score']:.1f} | Signals: Steam:{data['is_steam']} Storm:{data['is_storm']} Shark:{data['is_shark']} Whale:{data['is_whale']}")
