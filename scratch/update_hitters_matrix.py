import os

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(base_dir, "templates", "index.html")
    
    if not os.path.exists(target_path):
        print(f"[ERROR]: Target file does not exist: {target_path}")
        return
        
    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 1. Replace the table headers
    old_headers = """                             <th class="sortable-th" onclick="sortTable('hitters-table', 5, true)">HR-PROP ↕</th>
                             <th class="sortable-th" onclick="sortTable('hitters-table', 6, true)">BASES ↕</th>"""
                             
    new_headers = """                             <th class="sortable-th" onclick="sortTable('hitters-table', 5, true)">HR-PROP ↕</th>
                             <th class="sortable-th" onclick="sortTable('hitters-table', 6, true)">HITS ↕</th>
                             <th class="sortable-th" onclick="sortTable('hitters-table', 7, true)">BASES ↕</th>"""
                             
    # Robust replace (handles both CRLF and LF)
    if old_headers in content:
        content = content.replace(old_headers, new_headers)
        print("[SUCCESS]: Replaced table headers using LF format.")
    elif old_headers.replace("\n", "\r\n") in content:
        content = content.replace(old_headers.replace("\n", "\r\n"), new_headers.replace("\n", "\r\n"))
        print("[SUCCESS]: Replaced table headers using CRLF format.")
    else:
        # Fallback single-line matches if the block had different indentation or spacing
        print("[WARNING]: Block headers match failed. Trying single line fallback...")
        content = content.replace(
            "th class=\"sortable-th\" onclick=\"sortTable('hitters-table', 6, true)\">BASES ↕</th",
            "th class=\"sortable-th\" onclick=\"sortTable('hitters-table', 6, true)\">HITS ↕</th>\n                             <th class=\"sortable-th\" onclick=\"sortTable('hitters-table', 7, true)\">BASES ↕</th"
        )
        
    # 2. Replace the row metrics
    old_row = """                    <td class="metric">${h.ahr_price > 0 ? '+' : ''}${h.ahr_price || '-'}</td>
                    <td class="metric"><b>${h.hit_line || '-'}</b><br><span style="font-size:0.8em; color:var(--text-secondary);">(${h.hits_price > 0 ? '+' : ''}${h.hits_price || '-'})</span></td>"""
                    
    new_row = """                    <td class="metric">${h.ahr_price > 0 ? '+' : ''}${h.ahr_price || '-'}</td>
                    <td class="metric"><b>${h.hits_line || '-'}</b><br><span style="font-size:0.8em; color:var(--text-secondary);">(${h.hits_price > 0 ? '+' : ''}${h.hits_price || '-'})</span></td>
                    <td class="metric"><b>${h.tb_line || '-'}</b><br><span style="font-size:0.8em; color:var(--text-secondary);">(${h.tb_price > 0 ? '+' : ''}${h.tb_price || '-'})</span></td>"""
                    
    if old_row in content:
        content = content.replace(old_row, new_row)
        print("[SUCCESS]: Replaced row metrics using LF format.")
    elif old_row.replace("\n", "\r\n") in content:
        content = content.replace(old_row.replace("\n", "\r\n"), new_row.replace("\n", "\r\n"))
        print("[SUCCESS]: Replaced row metrics using CRLF format.")
    else:
        print("[ERROR]: Could not find row metrics inside index.html")
        return
        
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("[SUCCESS]: Successfully updated templates/index.html hitters matrix structure!")

if __name__ == "__main__":
    main()
