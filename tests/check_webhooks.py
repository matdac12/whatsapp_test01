import os
import requests

# Get credentials from environment or use placeholders
ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN', 'YOUR_TOKEN_HERE')
PHONE_ID = os.getenv('WHATSAPP_PHONE_ID', 'YOUR_PHONE_ID_HERE')

# API endpoint
url = f"https://graph.facebook.com/v22.0/{PHONE_ID}/subscribed_apps"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

response = requests.get(url, headers=headers)

print("Status Code:", response.status_code)
print("\nResponse:")
print(response.json())

if response.status_code == 200:
    data = response.json()
    if 'data' in data and len(data['data']) > 0:
        print("\n" + "="*50)
        print("SUBSCRIBED APPS:")
        print("="*50)
        for app in data['data']:
            print(f"App: {app.get('id')} - {app.get('name', 'Unknown')}")
            print(f"Subscribed fields: {app.get('subscribed_fields', [])}")
            print("-"*50)
    else:
        print("\nNo apps are subscribed to this phone number.")
