import os

def main():
    root = r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS"
    out_lines = []
    for dirpath, _, filenames in os.walk(root):
        if ".git" in dirpath or "node_modules" in dirpath or "__pycache__" in dirpath or ".gemini" in dirpath:
            continue
        for f in filenames:
            if not f.endswith((".py", ".html", ".js", ".css")):
                continue
            path = os.path.join(dirpath, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                if "blind" in content.lower():
                    out_lines.append(f"Found 'blind' in {os.path.relpath(path, root)}")
                    # print matching lines
                    lines = content.splitlines()
                    for idx, line in enumerate(lines, 1):
                        if "blind" in line.lower():
                            out_lines.append(f"  Line {idx}: {line.strip()}")
            except Exception as e:
                out_lines.append(f"Error reading {f}: {e}")

    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\scratch\search_output.txt", "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(out_lines))
    print("Done! Wrote output to scratch/search_output.txt")

if __name__ == "__main__":
    main()
