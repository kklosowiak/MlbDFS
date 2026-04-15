import requests
import sys

token = "8768870830:AAEl31aKg2hAPewlJbYullkbYb1QuMJ2fHY"
chat_id = "8678924440"

print(f"Testing Telegram Bot...")
url = f"https://api.telegram.org/bot{token}/getMe"

try:
    resp = requests.get(url)
    print(f"getMe Response: {resp.status_code}")
    print(f"getMe Data: {resp.json()}")
    
    msg_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": "🛸 OMEGA Connectivity Test: SUCCESS."}
    resp = requests.post(msg_url, data=payload)
    print(f"sendMessage Response: {resp.status_code}")
    print(f"sendMessage Data: {resp.json()}")
except Exception as e:
    print(f"Error: {e}")
