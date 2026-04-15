import unicodedata
import re

def normalize_player_name(name):
    """
    Expert-level Name Normalization for OMEGA v3.2.1.
    Strips accents, punctuation, common suffixes, and normalizes casing to 
    ensure high-fidelity matching across Odds API, DraftKings, and MLBAM datasets.
    """
    if not name:
        return ""
        
    # 1. Unicode NFKD normalization to decompose combined characters (e.g., ñ -> n + ~)
    nfkd_form = unicodedata.normalize('NFKD', name)
    # 2. Filter out non-spacing marks (the accents)
    name = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    # 3. Lowercase and strip punctuation
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    
    # 4. Strip common player name suffixes that introduce drift
    # Pattern: capture space followed by jr, sr, ii, iii, iv at the end of string
    suffixes = [r"\sjr\b", r"\ssr\b", r"\sii\b", r"\siii\b", r"\siv\b"]
    for suffix in suffixes:
        name = re.sub(suffix, "", name)
        
    # 5. Final whitespace normalization
    return " ".join(name.split()).strip()

if __name__ == "__main__":
    # Internal Unit Tests
    test_cases = [
        ("Ronald Acuña Jr.", "ronald acuna"),
        ("Vladimir Guerrero Sr.", "vladimir guerrero"),
        ("Robert Stephenson II", "robert stephenson"),
        ("Pete Alonso", "pete alonso"),
        ("Adolis García", "adolis garcia")
    ]
    
    print("Running Normalization Alpha Tests...")
    for original, expected in test_cases:
        result = normalize_player_name(original)
        status = "PASS" if result == expected else "FAIL"
        print(f"[{status}] {original} -> {result} (Expected: {expected})")
