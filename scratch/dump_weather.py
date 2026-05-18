import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://propfinder.app/weather", wait_until="networkidle", timeout=60000)
    page.wait_for_selector(".MuiCard-root", timeout=30000)
    time.sleep(2)
    
    cards = page.query_selector_all(".MuiCard-root")
    print(f"Found {len(cards)} cards:")
    for i, card in enumerate(cards):
        print(f"\n--- CARD {i+1} ---")
        text = card.inner_text()
        print(text)
        print("-------------------\n")
    
    browser.close()
