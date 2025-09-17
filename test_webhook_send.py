#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for webhook sending functionality with actual HTTP request
"""

import os
import json
import time
from datetime import datetime

# Try to import requests, handle if not available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  Warning: requests module not available. Install with: pip install requests")

def format_conversation_as_html(messages, profile):
    """Simple HTML generation for testing"""
    html_parts = [
        '<div style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto;">',
        '<h3>Conversazione WhatsApp</h3>',
        '<details style="margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">',
        '<summary style="cursor: pointer; font-weight: bold; color: #0066cc;">',
        '🔽 Clicca per espandere la conversazione completa',
        '</summary>',
        '<div style="margin-top: 15px;">'
    ]

    user_name = profile.get('name', 'Utente')
    if profile.get('last_name'):
        user_name += f" {profile['last_name']}"

    for msg in messages:
        timestamp = msg.get('timestamp', '')
        message_text = msg.get('message', '').replace('\n', '<br>')

        if msg.get('sender') == 'user':
            # User message (green bubble on right)
            html_parts.append(
                '<div style="margin: 10px 0; display: flex; justify-content: flex-end;">'
                '<div style="background: #dcf8c6; padding: 10px 15px; border-radius: 10px; '
                'max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">'
                f'<div style="font-size: 12px; color: #666; margin-bottom: 5px;">{user_name} - {timestamp}</div>'
                f'<div>{message_text}</div>'
                '</div>'
                '</div>'
            )
        else:
            # Assistant message (gray bubble on left)
            html_parts.append(
                '<div style="margin: 10px 0; display: flex; justify-content: flex-start;">'
                '<div style="background: #f0f0f0; padding: 10px 15px; border-radius: 10px; '
                'max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">'
                f'<div style="font-size: 12px; color: #666; margin-bottom: 5px;">Assistente - {timestamp}</div>'
                f'<div>{message_text}</div>'
                '</div>'
                '</div>'
            )

    html_parts.extend([
        '</div>',
        '</details>',
        '</div>'
    ])

    return ''.join(html_parts)

def format_conversation_as_plain(messages, profile):
    """Format conversation as plain text"""
    lines = []

    user_name = profile.get('name', 'Utente')
    if profile.get('last_name'):
        user_name += f" {profile['last_name']}"

    for msg in messages:
        timestamp = msg.get('timestamp', '')
        sender = user_name if msg.get('sender') == 'user' else 'Assistente'
        message = msg.get('message', '')
        lines.append(f"[{timestamp}] {sender}: {message}")

    return '\n'.join(lines)

def send_test_webhook(webhook_url, payload):
    """Send test webhook with retry logic"""
    if not REQUESTS_AVAILABLE:
        print("❌ Cannot send webhook: requests module not available")
        return False

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'WhatsApp-Bot-Test/1.0'
    }

    max_retries = 3
    timeout = (3, 10)  # 3s connect, 10s read

    for attempt in range(max_retries):
        try:
            print(f"🔄 Sending webhook (attempt {attempt + 1}/{max_retries})...")
            print(f"   URL: {webhook_url}")
            print(f"   Payload size: {len(json.dumps(payload))} bytes")

            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )

            print(f"   Response status: {response.status_code}")

            if response.status_code == 200:
                print("✅ Webhook sent successfully!")
                print(f"   Response: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
                return True
            elif response.status_code == 429:  # Rate limited
                retry_after = int(response.headers.get('Retry-After', 2))
                print(f"⏳ Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            else:
                print(f"❌ Request failed with status {response.status_code}")
                print(f"   Response: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")

        except requests.exceptions.Timeout:
            print(f"⏰ Request timeout on attempt {attempt + 1}")
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 Connection error on attempt {attempt + 1}: {str(e)[:100]}")
        except Exception as e:
            print(f"💥 Unexpected error: {str(e)[:100]}")

        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            print(f"   Waiting {wait_time}s before retry...")
            time.sleep(wait_time)

    print("❌ Failed to send webhook after all retries")
    return False

def test_webhook_send():
    """Test the complete webhook sending functionality"""

    print("🧪 Testing Webhook Send Functionality")
    print("=" * 50)

    # Load from .env file manually
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    except:
        pass

    # Check for WEBHOOK_URL environment variable
    webhook_url = os.environ.get('WEBHOOK_URL')
    if not webhook_url:
        print("⚠️  WEBHOOK_URL environment variable not set")
        # Use a test URL (httpbin.org for testing)
        webhook_url = "https://httpbin.org/post"
        print(f"   Using test URL: {webhook_url}")
    else:
        print(f"✅ Found WEBHOOK_URL: {webhook_url[:50]}{'...' if len(webhook_url) > 50 else ''}")

    # Sample profile data
    test_profile = {
        'name': 'Mario',
        'last_name': 'Rossi',
        'ragione_sociale': 'Acme Corp',
        'email': 'mario.rossi@acme.com',
        'phone_number': '+391234567890'
    }

    # Sample messages for testing
    test_messages = [
        {
            'sender': 'user',
            'message': 'Ciao, sono Mario della Acme Corp',
            'timestamp': '2025-01-16T11:45:00Z'
        },
        {
            'sender': 'assistant',
            'message': 'Ciao Mario! Benvenuto. Per poterti assistere al meglio, potresti fornirmi il tuo cognome?',
            'timestamp': '2025-01-16T11:45:05Z'
        },
        {
            'sender': 'user',
            'message': 'Il mio cognome è Rossi',
            'timestamp': '2025-01-16T11:46:00Z'
        },
        {
            'sender': 'assistant',
            'message': 'Perfetto Mario Rossi! Potresti indicarmi anche il tuo indirizzo email?',
            'timestamp': '2025-01-16T11:46:05Z'
        },
        {
            'sender': 'user',
            'message': 'La mia email è mario.rossi@acme.com',
            'timestamp': '2025-01-16T11:47:00Z'
        },
        {
            'sender': 'assistant',
            'message': 'Grazie Mario! Ho registrato tutti i tuoi dati. Come posso aiutarti oggi?',
            'timestamp': '2025-01-16T11:47:05Z'
        }
    ]

    print("\n📝 Generating conversation formats...")

    # Generate HTML and plain text
    html_conversation = format_conversation_as_html(test_messages, test_profile)
    plain_conversation = format_conversation_as_plain(test_messages, test_profile)

    print(f"✅ HTML generated ({len(html_conversation)} chars)")
    print(f"✅ Plain text generated ({len(plain_conversation)} chars)")

    # Build webhook payload (matching the original structure)
    payload = {
        "event": "profile.completed",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "profile": {
            "phone_number": test_profile['phone_number'],
            "name": test_profile.get('name', ''),
            "last_name": test_profile.get('last_name', ''),
            "ragione_sociale": test_profile.get('ragione_sociale', ''),
            "email": test_profile.get('email', '')
        },
        "summary": "Test conversation: Mario Rossi from Acme Corp provided his contact details",
        "conversation_html": html_conversation,
        "conversation_plain": plain_conversation
    }

    print(f"\n📦 Webhook payload created")
    print(f"   Event: {payload['event']}")
    print(f"   Profile: {payload['profile']['name']} {payload['profile']['last_name']}")
    print(f"   Company: {payload['profile']['ragione_sociale']}")
    print(f"   Email: {payload['profile']['email']}")
    print(f"   Total payload size: {len(json.dumps(payload))} bytes")

    # Send the webhook
    print(f"\n🚀 Sending webhook to: {webhook_url}")
    success = send_test_webhook(webhook_url, payload)

    print("\n" + "=" * 50)
    if success:
        print("🎉 WEBHOOK TEST COMPLETED SUCCESSFULLY!")
    else:
        print("❌ WEBHOOK TEST FAILED")

    return success

if __name__ == "__main__":
    test_webhook_send()