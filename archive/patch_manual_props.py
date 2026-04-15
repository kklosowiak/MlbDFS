import csv

file_path = r"c:\Users\konra\.gemini\antigravity\scratch\mlb_dfs_sharps_engine\data\manual_props.csv"

# read all lines
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# write back only up to line 51 (remove the badly appended lines)
with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines[:51])

# Append correctly with tabs
rows = [
    "cba7f4f927e5e141eef8113b0ae66a4b\t4/10/2026\tFALSE\tDraftKings\t4/10/2026\tMilwaukee Brewers\tWashington Nationals\tpitcher_strikeouts\tOver\tChad Patrick\t-140\t4.5\n",
    "cba7f4f927e5e141eef8113b0ae66a4b\t4/10/2026\tFALSE\tDraftKings\t4/10/2026\tMilwaukee Brewers\tWashington Nationals\tpitcher_outs\tOver\tChad Patrick\t-101\t15.5\n"
]

with open(file_path, "a", encoding="utf-8") as f:
    f.writelines(rows)
