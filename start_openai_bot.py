#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup script for WhatsApp OpenAI Bot
Loads environment variables and starts the webhook server
"""

import os
import sys
from pathlib import Path

# Set UTF-8 as default encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Get the directory of this script
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)

# Load environment variables from .env file
env_file = script_dir / '.env'
if env_file.exists():
    print("[ENV] Loading environment variables from .env file...")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                if 'TOKEN' in key or 'KEY' in key:
                    print(f"   [OK] {key}: {'*' * 10}...")
                else:
                    print(f"   [OK] {key}: {value[:30]}..." if len(value) > 30 else f"   [OK] {key}: {value}")
else:
    print("[WARN] No .env file found. Using environment variables.")

# Verify required environment variables
required_vars = {
    'WHATSAPP_ACCESS_TOKEN': 'WhatsApp access token',
    'WHATSAPP_PHONE_ID': 'WhatsApp phone number ID',
    'OPENAI_API_KEY': 'OpenAI API key',
    'OPENAI_PROMPT_ID': 'OpenAI prompt ID'
}

missing_vars = []
for var, description in required_vars.items():
    if not os.environ.get(var):
        missing_vars.append(f"   [ERROR] {var} ({description})")

if missing_vars:
    print("\n[WARN] Missing required environment variables:")
    for var in missing_vars:
        print(var)
    print("\nPlease set these in your .env file or environment.")
    response = input("\nDo you want to continue anyway? (y/n): ")
    if response.lower() != 'y':
        sys.exit(1)

# Set default values
os.environ.setdefault('PORT', '3000')
os.environ.setdefault('VERIFY_TOKEN', 'my-verify-token-123')
os.environ.setdefault('OPENAI_MODEL', 'gpt-4.1')

print("\n[START] Starting WhatsApp OpenAI Bot")
print("=" * 50)
print(f"[LOCAL] Local URL: http://localhost:{os.environ.get('PORT')}")
print(f"[TOKEN] Verify Token: {os.environ.get('VERIFY_TOKEN')}")
print(f"[MODEL] OpenAI Model: {os.environ.get('OPENAI_MODEL')}")
print("=" * 50)
print("\n[SETUP] To connect to WhatsApp:")
print("1. Run ngrok: ngrok http " + os.environ.get('PORT', '3000'))
print("2. Use the ngrok URL in WhatsApp webhook settings")
print("3. Send a message to your WhatsApp Business number")
print("=" * 50)
print("\n[COMMANDS] Available commands in WhatsApp:")
print("   /reset - Start a new conversation")
print("   /history - View conversation history")
print("   /info - Get bot information")
print("=" * 50)
print("\nStarting server...\n")

# Import and run the webhook server
try:
    from webhook_openai import app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)), debug=True)
except ImportError as e:
    print(f"\n[ERROR] Error importing webhook_openai: {e}")
    print("\nPlease install required packages:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"\n[ERROR] Error starting server: {e}")
    sys.exit(1)