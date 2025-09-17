#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook Notification Module
Handles sending profile completion notifications to Make/Zapier with formatted conversation data
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape
from typing import Dict, List, Optional, Tuple
import requests

from openai import OpenAI
from database import db

logger = logging.getLogger(__name__)

# Configuration from environment
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_PROMPT_ID_SUMMARIZER = os.environ.get('OPENAI_PROMPT_ID_SUMMARIZER')

# Request configuration (matching webhook_openai.py)
REQUEST_TIMEOUT = (3, 10)  # 3s connect, 10s read
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # seconds between retries

class WebhookNotifier:
    def __init__(self):
        """Initialize the webhook notifier with OpenAI client"""
        if not all([WEBHOOK_URL, OPENAI_API_KEY, OPENAI_PROMPT_ID_SUMMARIZER]):
            missing = []
            if not WEBHOOK_URL:
                missing.append("WEBHOOK_URL")
            if not OPENAI_API_KEY:
                missing.append("OPENAI_API_KEY")
            if not OPENAI_PROMPT_ID_SUMMARIZER:
                missing.append("OPENAI_PROMPT_ID_SUMMARIZER")
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            self.enabled = False
            return
        
        self.enabled = True
        self.webhook_url = WEBHOOK_URL
        self.prompt_id = OPENAI_PROMPT_ID_SUMMARIZER
        
        logger.info(f"Webhook URL configured: {self.webhook_url[:30]}...")
        logger.info(f"Summarizer prompt ID: {self.prompt_id}")
        
        # Initialize OpenAI client
        try:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("Webhook notifier initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.enabled = False
    
    def _parse_retry_after(self, header_value: Optional[str], fallback: float) -> float:
        """Convert Retry-After header value into seconds, falling back when needed."""
        if not header_value:
            return fallback

        candidate = header_value.strip()
        if not candidate:
            return fallback

        try:
            seconds = float(candidate)
            if seconds >= 0:
                return seconds
        except ValueError:
            pass

        try:
            retry_dt = parsedate_to_datetime(candidate)
            if retry_dt is None:
                return fallback
            if retry_dt.tzinfo is None:
                retry_dt = retry_dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta_seconds = (retry_dt - now).total_seconds()
            if delta_seconds > 0:
                return delta_seconds
        except Exception:
            logger.warning(f"Unable to parse Retry-After header '{candidate}', using fallback {fallback}s")

        return fallback

    def make_request_with_retry(self, url: str, data: Dict, headers: Dict) -> Tuple[bool, Optional[requests.Response]]:
        """Make HTTP request with retry logic (from webhook_openai.py)"""
        for attempt in range(MAX_RETRIES):
            backoff = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            try:
                response = requests.post(
                    url,
                    json=data,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )

                if 200 <= response.status_code < 300:
                    return True, response

                if response.status_code == 429:  # Rate limited
                    header_value = response.headers.get('Retry-After')
                    retry_after = self._parse_retry_after(header_value, backoff)
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue

                logger.error(f"Request failed with status {response.status_code}: {response.text}")

            except requests.exceptions.Timeout:
                logger.error(f"Request timeout on attempt {attempt + 1}/{MAX_RETRIES}")
            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error on attempt {attempt + 1}/{MAX_RETRIES}")
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")

            if attempt < MAX_RETRIES - 1:
                time.sleep(backoff)

        return False, None
    
    def format_timestamp(self, timestamp: str) -> str:
        """Format timestamp for Italian locale"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime("%d/%m/%Y %H:%M")
        except:
            return timestamp
    
    def format_conversation_as_html(self, messages: List[Dict], profile: Dict) -> str:
        """Format conversation messages as a WhatsApp-style HTML transcript."""
        html_parts = [
            '<div style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px 0;">',
            '<h3 style="margin: 0 0 12px 0;">Conversazione WhatsApp</h3>',
            '<div style="border: 1px solid #ddd; border-radius: 5px; padding: 16px; background: #fff;">'
        ]
        
        # Get user display name
        user_name = profile.get('name') or 'Utente'
        if profile.get('last_name'):
            user_name += f" {profile['last_name']}"
        user_name_html = escape(user_name)
        
        for msg in messages:
            timestamp = self.format_timestamp(msg.get('timestamp', ''))
            message_text = escape(msg.get('message', ''))
            message_text = message_text.replace('\n', '<br>')
            timestamp_html = escape(timestamp)
            
            if msg.get('sender') == 'user':
                # User message (green bubble on right)
                html_parts.append(
                    '<div style="margin: 10px 0; display: flex; justify-content: flex-end;">'
                    '<div style="background: #dcf8c6; padding: 10px 15px; border-radius: 10px; '
                    'max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">'
                    f'<div style="font-size: 12px; color: #666; margin-bottom: 5px;">{user_name_html} - {timestamp_html}</div>'
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
                    f'<div style="font-size: 12px; color: #666; margin-bottom: 5px;">Assistente - {timestamp_html}</div>'
                    f'<div>{message_text}</div>'
                    '</div>'
                    '</div>'
                )
        
        html_parts.extend([
            '</div>',
            '</div>'
        ])
        
        return ''.join(html_parts)
    
    def format_conversation_as_plain(self, messages: List[Dict], profile: Dict) -> str:
        """Format conversation as plain text for OpenAI summarizer"""
        lines = []
        
        # Get user display name
        user_name = profile.get('name', 'Utente')
        if profile.get('last_name'):
            user_name += f" {profile['last_name']}"
        
        for msg in messages:
            timestamp = self.format_timestamp(msg.get('timestamp', ''))
            sender = user_name if msg.get('sender') == 'user' else 'Assistente'
            message = msg.get('message', '')
            
            lines.append(f"[{timestamp}] {sender}: {message}")
        
        return '\n'.join(lines)
    
    def generate_summary(self, conversation_text: str) -> Optional[str]:
        """Generate conversation summary using OpenAI"""
        if not self.enabled:
            logger.warning("Summary generation skipped - webhook notifier is disabled")
            return None
        
        try:
            logger.info(f"Generating summary for conversation with {len(conversation_text)} characters")
            logger.debug(f"Using prompt ID: {self.prompt_id}")
            
            response = self.client.responses.create(
                prompt={
                    "id": self.prompt_id,
                    "variables": {
                        "conv_history": conversation_text
                    }
                },
                input=[{"role": "user", "content": "Genera un riassunto di questa conversazione"}],
                model="gpt-4.1"
            )
            
            logger.info("Summary generated successfully")
            return response.output_text
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}", exc_info=True)
            return None
    
    def send_profile_completion_webhook(self, phone_number: str, profile: Dict) -> bool:
        """Send webhook notification when profile is completed"""
        if not self.enabled:
            logger.warning("Webhook notifier is disabled due to missing configuration")
            return False
        
        try:
            # Get conversation messages from database
            messages = db.get_messages(phone_number)
            if not messages:
                logger.warning(f"No messages found for {phone_number}")
                return False
            
            # Format conversation
            html_conversation = self.format_conversation_as_html(messages, profile)
            plain_conversation = self.format_conversation_as_plain(messages, profile)
            
            # Generate summary
            summary = self.generate_summary(plain_conversation)
            if not summary:
                summary = "Riassunto non disponibile al momento. Riferirsi alla conversazione. Grazie"
                logger.warning(f"Summary generation failed for {phone_number}, using fallback message")
            
            # Build webhook payload
            payload = {
                "event": "profile.completed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "profile": {
                    "phone_number": phone_number,
                    "name": profile.get('name', ''),
                    "last_name": profile.get('last_name', ''),
                    "ragione_sociale": profile.get('ragione_sociale', ''),
                    "email": profile.get('email', '')
                },
                "summary": summary,
                "conversation_html": html_conversation,
                "conversation_plain": plain_conversation
            }
            
            # Send webhook
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WhatsApp-Bot/1.0'
            }
            
            success, response = self.make_request_with_retry(self.webhook_url, payload, headers)
            
            if success:
                logger.info(f"Successfully sent profile completion webhook for {phone_number}")
                return True
            else:
                logger.error(f"Failed to send webhook for {phone_number} after {MAX_RETRIES} attempts")
                return False
                
        except Exception as e:
            logger.error(f"Error in send_profile_completion_webhook: {e}", exc_info=True)
            return False

# Global instance
webhook_notifier = WebhookNotifier()

def notify_profile_completion(phone_number: str, profile: Dict) -> bool:
    """
    Public function to notify profile completion
    
    Args:
        phone_number: WhatsApp phone number
        profile: Profile data dictionary
        
    Returns:
        bool: Success status
    """
    return webhook_notifier.send_profile_completion_webhook(phone_number, profile)
