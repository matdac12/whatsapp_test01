#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Conversation Manager
Manages conversations using OpenAI's new Conversations and Responses API
Based on the guide in openAI_integration.md
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from openai import OpenAI
from database import db

# Ensure UTF-8 encoding for stdout
if sys.stdout.encoding != 'utf-8':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logger = logging.getLogger(__name__)

class OpenAIConversationManager:
    def __init__(self, api_key: str, prompt_id: str, model: str = "gpt-4.1"):
        """
        Initialize the OpenAI conversation manager
        
        Args:
            api_key: OpenAI API key
            prompt_id: The prompt ID to use for all responses
            model: The model to use (default: gpt-4.1)
        """
        try:
            # Ensure API key is properly encoded
            api_key = api_key.strip()
            self.client = OpenAI(api_key=api_key)
            self.prompt_id = prompt_id.strip()
            self.model = model
            self.conversations: Dict[str, str] = {}  # whatsapp_user_id -> openai_conversation_id
            
            # Load existing conversations from database
            self.load_conversations()
            
            logger.info(f"OpenAI Conversation Manager initialized")
            logger.info(f"Model: {self.model}")
            logger.info(f"Prompt ID: {self.prompt_id[:20]}...")
            logger.info(f"API Key: {api_key[:20]}...")
            logger.info(f"Loaded {len(self.conversations)} existing conversations")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def load_conversations(self):
        """Load existing conversations from database"""
        try:
            self.conversations = db.get_all_conversations()
            logger.info(f"Loaded {len(self.conversations)} conversations from database")
        except Exception as e:
            logger.error(f"Error loading conversations from database: {e}")
            self.conversations = {}
    
    def save_all_conversations(self):
        """Save ALL conversations to database (bulk operation - use sparingly)"""
        try:
            # Save all conversations to database
            for user_id, conversation_id in self.conversations.items():
                db.save_conversation(user_id, conversation_id)
            logger.debug(f"Saved all {len(self.conversations)} conversations to database")
        except Exception as e:
            logger.error(f"Error saving conversations to database: {e}")
    
    def get_or_create_conversation(self, user_id: str, initial_message: Optional[str] = None) -> str:
        """
        Get existing conversation or create a new one for a user
        
        Args:
            user_id: WhatsApp user ID
            initial_message: Optional initial message to start the conversation
            
        Returns:
            OpenAI conversation ID
        """
        if user_id in self.conversations:
            logger.info(f"Found existing conversation for user {user_id}: {self.conversations[user_id]}")
            return self.conversations[user_id]
        
        try:
            # Create new conversation as per the guide
            if initial_message:
                # Initialize with the first message - ensure proper encoding
                initial_message_safe = initial_message.encode('utf-8', errors='ignore').decode('utf-8')
                logger.info(f"Creating conversation with initial message")
                conversation = self.client.conversations.create(
                    items=[{"type": "message", "role": "user", "content": initial_message_safe}]
                )
            else:
                # Create empty conversation
                logger.info(f"Creating empty conversation")
                conversation = self.client.conversations.create()
            
            conversation_id = conversation.id
            self.conversations[user_id] = conversation_id
            # Save only this single conversation, not all
            db.save_conversation(user_id, conversation_id)
            
            logger.info(f"Created new conversation for user {user_id}: {conversation_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"User ID: {user_id}")
            if initial_message:
                logger.error(f"Initial message length: {len(initial_message)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def generate_response(self, user_id: str, message: str, prompt_variables: Optional[Dict[str, str]] = None) -> str:
        """
        Generate an AI response for a user message
        
        Args:
            user_id: WhatsApp user ID
            message: User's message text
            prompt_variables: Optional dictionary of variables to pass to the prompt
            
        Returns:
            AI-generated response text
        """
        try:
            # Get or create conversation
            conversation_id = self.get_or_create_conversation(user_id, message)
            
            logger.info(f"Generating response for user {user_id}")
            # Safely log the message
            try:
                logger.info(f"User message: {message}")
            except:
                logger.info(f"User message: [Contains special characters]")
            
            # Log variables if provided
            if prompt_variables:
                logger.debug(f"Prompt variables: {prompt_variables}")
            
            # Ensure message is properly encoded
            message_utf8 = message.encode('utf-8').decode('utf-8')
            
            # Build prompt configuration
            prompt_config = {"id": self.prompt_id}
            
            # Add variables if provided
            if prompt_variables:
                prompt_config["variables"] = prompt_variables
            
            # Generate response using the Responses API
            response = self.client.responses.create(
                prompt=prompt_config,
                input=[{"role": "user", "content": message_utf8}],
                model=self.model,
                conversation=conversation_id
                # No stream parameter as we don't want streaming
            )
            
            # Get the output text
            output_text = response.output_text
            
            # Log safely with proper encoding
            log_preview = output_text[:100] if len(output_text) > 100 else output_text
            logger.info(f"Generated response: {log_preview}...")
            return output_text
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Return a fallback message
            return "I apologize, but I'm having trouble processing your message right now. Please try again."
    
    def reset_conversation(self, user_id: str) -> bool:
        """
        Reset a user's conversation by creating a new one
        
        Args:
            user_id: WhatsApp user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if user_id in self.conversations:
                old_conversation_id = self.conversations[user_id]
                
                # Optionally delete the old conversation
                # As mentioned in the guide, we can delete conversations
                try:
                    self.client.conversations.delete(old_conversation_id)
                    logger.info(f"Deleted old conversation: {old_conversation_id}")
                except Exception as e:
                    logger.warning(f"Could not delete old conversation: {e}")
                
                # Remove from our tracking
                del self.conversations[user_id]
                db.delete_conversation(user_id)
                # No need to save all conversations - we already deleted the one we needed
                
                logger.info(f"Reset conversation for user {user_id}")
                return True
            else:
                logger.info(f"No conversation to reset for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error resetting conversation: {e}")
            return False
    
    def get_conversation_history(self, user_id: str, limit: int = 10) -> Optional[list]:
        """
        Get conversation history for a user
        
        Args:
            user_id: WhatsApp user ID
            limit: Maximum number of items to retrieve
            
        Returns:
            List of conversation items or None if error
        """
        try:
            if user_id not in self.conversations:
                logger.warning(f"No conversation found for user {user_id}")
                return None
            
            conversation_id = self.conversations[user_id]
            
            # Get items as shown in the guide
            items = self.client.conversations.items.list(conversation_id, limit=limit)
            
            return items.data
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return None
    
    def update_conversation_with_data(self, user_id: str, client_info_json: str) -> bool:
        """
        Update the conversation with extracted client data
        
        Args:
            user_id: WhatsApp user ID
            client_info_json: JSON string of extracted client information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if user_id not in self.conversations:
                logger.warning(f"No conversation found for user {user_id}")
                return False
            
            conversation_id = self.conversations[user_id]
            
            # Add the extracted data to the conversation as per the guide
            items = self.client.conversations.items.create(
                conversation_id,
                items=[
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{
                            "type": "output_text", 
                            "text": f"[DATI CLIENTE ESTRATTI]: {client_info_json}"
                        }],
                    }
                ],
            )
            
            logger.info(f"Updated conversation {conversation_id} with extracted client data")
            return True
            
        except Exception as e:
            logger.error(f"Error updating conversation with data: {e}")
            return False
    
    def handle_command(self, user_id: str, command: str) -> Optional[str]:
        """
        Handle special commands
        
        Args:
            user_id: WhatsApp user ID
            command: Command text (without /)
            
        Returns:
            Response text or None if not a special command
        """
        command = command.lower().strip()
        
        if command == "reset":
            if self.reset_conversation(user_id):
                return "✨ Conversation reset! Let's start fresh. How can I help you?"
            else:
                return "Sorry, I couldn't reset the conversation. Please try again."
        
        elif command == "history":
            history = self.get_conversation_history(user_id, limit=5)
            if history:
                return f"📜 Last {len(history)} messages in our conversation:\n" + \
                       "\n".join([f"- {item.get('content', '')[:50]}..." for item in history])
            else:
                return "No conversation history found."
        
        elif command == "info":
            conv_id = self.conversations.get(user_id, "None")
            return f"ℹ️ Conversation Info:\n" \
                   f"• Model: {self.model}\n" \
                   f"• Conversation ID: {conv_id[:8]}...\n" \
                   f"• Active conversations: {len(self.conversations)}"
        
        return None