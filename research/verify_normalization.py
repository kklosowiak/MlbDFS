import sys
import os

# Add the project directory to path
sys.path.append(r'C:\Users\konra\.gemini\antigravity\scratch\sports_agent\sports_agent')

from utils import normalize_name

def test_mapping():
    players = [
        ("Ronald Acuña Jr.", "ronaldacuna"),
        ("Luis Robert Jr.", "luisrobert"),
        ("A.J. Puk", "ajpuk"),
        ("J.D. Martinez", "jdmartinez"),
        ("Vladimir Guerrero III", "vladimirguerrero"),
        ("Aaron Nola ", "aaronnola")
    ]
    
    print("--- OMEGA Naming Normalization Test ---")
    all_passed = True
    for raw, expected in players:
        normalized = normalize_name(raw)
        status = "PASSED" if normalized == expected else "FAILED"
        print(f"[{status}] '{raw}' -> '{normalized}' (Expected: '{expected}')")
        if status == "FAILED":
            all_passed = False
            
    if all_passed:
        print("\n✅ Verification COMPLETE: All 'Identity Handshakes' are synchronized.")
    else:
        print("\n❌ Verification FAILED: Normalization mismatch detected.")

if __name__ == "__main__":
    test_mapping()
