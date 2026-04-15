from pybaseball import batting_stats_range
from datetime import datetime, timedelta
import pandas as pd

end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')

print(f"Fetching from {start_date} to {end_date}...")
try:
    df = batting_stats_range(start_date, end_date)
    print(f"Columns: {df.columns.tolist()}")
    print(df.head())
except Exception as e:
    import traceback
    traceback.print_exc()
