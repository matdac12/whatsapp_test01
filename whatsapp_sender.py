#!/usr/bin/env python3
import os
import requests
import json
import argparse
from typing import Optional

class WhatsAppSender:
    def __init__(self, access_token: str, phone_id: str):
        """
        Initialize WhatsApp sender with credentials
        
        Args:
            access_token: WhatsApp Business API access token
            phone_id: WhatsApp Business phone number ID
        """
        self.access_token = access_token
        self.phone_id = phone_id
        self.api_version = "v22.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
    
    def send_text_message(self, recipient: str, message: str) -> dict:
        """
        Send a text message via WhatsApp
        
        Args:
            recipient: Phone number with country code (no + sign)
            message: Text message to send
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/{self.phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        return response.json(), response.status_code
    
    def send_template_message(self, recipient: str, template_name: str, 
                            language_code: str = "en", 
                            components: Optional[list] = None) -> dict:
        """
        Send a template message via WhatsApp
        
        Args:
            recipient: Phone number with country code (no + sign)
            template_name: Name of the approved template
            language_code: Language code for the template
            components: Template components with parameters
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/{self.phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if components:
            payload["template"]["components"] = components
        
        response = requests.post(url, headers=headers, json=payload)
        return response.json(), response.status_code

def main():
    parser = argparse.ArgumentParser(description="Send WhatsApp messages via Business API")
    parser.add_argument("--token", help="WhatsApp Business API access token (or set WHATSAPP_ACCESS_TOKEN env var)")
    parser.add_argument("--phone-id", help="WhatsApp Business phone number ID (or set WHATSAPP_PHONE_ID env var)")
    parser.add_argument("--to", required=True, help="Recipient phone number (with country code, no + sign)")
    parser.add_argument("--message", required=True, help="Message text to send")
    parser.add_argument("--template", help="Send as template message with this template name")
    parser.add_argument("--lang", default="en", help="Template language code (default: en)")
    
    args = parser.parse_args()
    
    # Get credentials from arguments or environment variables
    access_token = args.token or os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_id = args.phone_id or os.getenv("WHATSAPP_PHONE_ID")
    
    if not access_token or not phone_id:
        print("❌ Error: Missing credentials!")
        print("Please provide --token and --phone-id arguments or set environment variables:")
        print("  WHATSAPP_ACCESS_TOKEN")
        print("  WHATSAPP_PHONE_ID")
        return 1
    
    # Initialize sender
    sender = WhatsAppSender(access_token, phone_id)
    
    # Send message
    print(f"📱 Sending WhatsApp message to +{args.to}...")
    
    try:
        if args.template:
            # Send template message
            response, status = sender.send_template_message(
                args.to, 
                args.template,
                args.lang
            )
        else:
            # Send text message
            response, status = sender.send_text_message(args.to, args.message)
        
        if status == 200:
            message_id = response.get("messages", [{}])[0].get("id", "N/A")
            print(f"✅ Message sent successfully!")
            print(f"📨 Message ID: {message_id}")
            return 0
        else:
            print(f"❌ Failed to send message")
            print(f"Status: {status}")
            print(f"Response: {json.dumps(response, indent=2)}")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())