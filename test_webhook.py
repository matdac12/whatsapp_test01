#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for webhook notification functionality
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webhook_notifier import webhook_notifier

def test_webhook():
    """Test the webhook with sample data"""
    
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
    
    # Test HTML generation
    print("Testing HTML generation...")
    html = webhook_notifier.format_conversation_as_html(test_messages, test_profile)
    print("HTML generated successfully!")
    print(f"HTML length: {len(html)} characters")
    
    # Save HTML to file for manual inspection
    with open('test_conversation.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML saved to test_conversation.html for inspection")
    
    # Test plain text generation
    print("\nTesting plain text generation...")
    plain = webhook_notifier.format_conversation_as_plain(test_messages, test_profile)
    print("Plain text generated successfully!")
    print(f"Plain text preview:\n{plain[:200]}...")
    
    # Test summary generation (requires valid OpenAI configuration)
    if webhook_notifier.enabled:
        print("\nTesting summary generation...")
        summary = webhook_notifier.generate_summary(plain)
        if summary:
            print("Summary generated successfully!")
            print(f"Summary: {summary}")
        else:
            print("Summary generation failed (check OpenAI configuration)")
    else:
        print("\nWebhook notifier is disabled (missing environment variables)")
        print("Required: WEBHOOK_URL, OPENAI_API_KEY, OPENAI_PROMPT_ID_SUMMARIZER")
        return
    
    # Test webhook payload generation (without sending)
    print("\nGenerating webhook payload...")
    payload = {
        "event": "profile.completed",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "profile": test_profile,
        "summary": summary if summary else "Test summary",
        "conversation_html": html,
        "conversation_plain": plain
    }
    
    print("Webhook payload generated successfully!")
    print(f"Payload keys: {list(payload.keys())}")
    
    # Option to send actual webhook (commented out by default)
    # print("\nTo send actual webhook, uncomment the following lines:")
    # success = webhook_notifier.send_profile_completion_webhook(
    #     test_profile['phone_number'], 
    #     test_profile
    # )
    # print(f"Webhook sent: {success}")

if __name__ == "__main__":
    test_webhook()